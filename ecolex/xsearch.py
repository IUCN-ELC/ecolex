import logging
from collections import Iterable, defaultdict
from datetime import datetime, timedelta
from functools import partial, reduce
from operator import and_, or_
from scorched import SolrInterface
from scorched.response import SolrResponse
from scorched.strings import DismaxString
from django.conf import settings
from django.utils.functional import LazyObject

from .schema import (
    SCHEMA_MAP, FIELD_MAP,
    FILTER_FIELDS, STATS_FIELDS, FETCH_FIELDS, BOOST_FIELDS,
    SORT_FIELD,
)


logger = logging.getLogger(__name__)


class __DefaultInterface(LazyObject):
    # this exists with the sole purpose to defer reading settings
    def _setup(self):
        self._wrapped = SolrInterface(settings.SOLR_URI)


DEFAULT_INTERFACE = __DefaultInterface()


class Searcher(object):
    SEARCH_OPTIONS = {
        'facet.limit': -1,
        'facet.sort': 'index',
        'facet.method': 'enum',
        'facet.mincount': 1,
    }

    # The secret to understanding what happens here is that the
    # `self.prepare_*()` logic during `__init__` is paired with the
    # `self.get_*()` logic during `execute`, so that:
    #
    # - fields that are faceted upon are tagged during filtering,
    #   so they can be excluded during faceting, unless their values
    #   have been AND-ed together, and that
    #
    # - fields that have their stats retrieved are also used for range
    #   filtering, and they are likewise tagged / excluded.

    def __init__(self, data, language, interface=DEFAULT_INTERFACE):
        self.language = language
        self.interface = interface

        self.qargs = []
        self.qkwargs = {}

        # `q` and `type` will be used for query-ing, the rest are filters
        try:
            self.qargs.append(data.pop('q'))
        except KeyError:
            pass

        types = data.pop('type', [])

        try:
            self.set_types(types)
        except ValueError:
            # all types requested are invalid
            # TODO: return an "empty" response
            return

        self.prepare_filters(data)
        self.prepare_stats()
        self.prepare_range_filters(data)
        self.prepare_facets()

    def set_types(self, types):
        if not types:
            # momentarily set _used_fields even with no given type,
            # to protect agains rogue form fields. TODO: fix.
            #self._used_fields = None
            self._used_fields = reduce(or_,
                                       (set(fs) for fs in FIELD_MAP.values()))
            return

        types = set(SCHEMA_MAP.keys()).intersection(types)
        if not types:
            raise ValueError

        self._used_fields = reduce(or_,
                                   (set(FIELD_MAP[t]) for t in types),
                                   set(FIELD_MAP['_']))

        self.qkwargs['type'] = self.to_query(list(types))

    def is_used_field(self, field):
        return field in self._used_fields
        # we could shortcut calculation when there's no given type, but see
        # `set_types()` above
        #
        # if self._used_fields is None:
        #     return True
        # else:
        #     return field in self._used_fields

    def prepare_filters(self, data):
        filters = {
            field: {
                'data': value,
                'op': and_ if data.get("%s_and_" % field) else or_
            }
            for field, value in data.items()
            if self.is_used_field(field)
        }
        self.filters = filters

    def prepare_stats(self):
        fields = [
            field
            for field in STATS_FIELDS.keys()
            if self.is_used_field(field)
        ]
        self.stats_fields = fields

    def prepare_range_filters(self, data):
        # this one depends on prepare_stats() above
        range_filters = defaultdict(lambda: {'min': None, 'max': None})

        for field in self.stats_fields:
            for typ in ('min', 'max'):
                try:
                    value = data["%s_%s" % (field, typ)]
                except KeyError:
                    continue
                # TODO: all this should be handled in form
                # we'll only deal with integers for now
                try:
                    value = int(value[0])
                except ValueError:
                    continue

                # handling only dates for the moment.
                # form should give us all this stuff of the proper datatype
                if STATS_FIELDS[field].datatype in ('date', 'datetime'):
                    if typ == 'max':
                        value += 1

                    try:
                        value = datetime(value, 1, 1)
                    except TypeError:
                        continue

                    if typ == 'max':
                        value -= timedelta(seconds=1)

                range_filters[field][typ] = value

        self.range_filters = range_filters

    def prepare_facets(self):
        fields = [
            field
            for field in FILTER_FIELDS.keys()
            if self.is_used_field(field)
        ]
        self.facet_fields = fields

    def _get_filter_key(self, field):
        # tag fields used for faceting if OR-ed
        if (field in self.facet_fields
             and self.filters[field]['op'] is or_):
            params = self.mk_local_params(tag=field)
        else:
            params = ''

        source_field = FILTER_FIELDS[field].get_source_field(self.language)

        return '%s%s' % (params, source_field)

    def get_filters(self):
        return {
            self._get_filter_key(field): self.to_query(v['data'], v['op'])
            for field, v in self.filters.items()
        }

    def _get_range_filter_key(self, field):
        # tag fields used for stats
        if field in self.stats_fields:
            params = self.mk_local_params(tag=field)
        else:
            params = ''

        source_field = FILTER_FIELDS[field].get_source_field(self.language)

        return '%s%s' % (params, source_field)

    def get_range_filters(self):
        filters = {}
        for field, v in self.range_filters.items():
            key = self._get_range_filter_key(field)

            if v['min'] is not None and v['max'] is not None:
                lookup = 'range'
                value = (v['min'], v['max'])
            elif v['min'] is not None:
                lookup = 'gte'
                value = v['min']
            else:
                lookup = 'lte'
                value = v['max']

            filters["%s__%s" % (key, lookup)] = value
        return filters

    def _get_stats_key(self, field):
        paramkws = {
            # override default statistics
            'min': 'true',
            'max': 'true',
            # and key returned fields to our field names
            'key': field,
        }
        # and exclude fields used for filtering
        if (field in self.range_filters):
            paramkws['ex'] = field

        params = self.mk_local_params(**paramkws)
        source_field = FILTER_FIELDS[field].get_source_field(self.language)

        return '%s%s' % (params, source_field)

    def get_stats_fields(self):
        return [
            self._get_stats_key(field)
            for field in self.stats_fields
        ]

    def _get_facet_key(self, field):
        # key returned fields to our field names to simplify code
        paramkws = {
            'key': field
        }
        # and exclude fields used for filtering that are OR-ed
        if (field in self.filters
            and self.filters[field]['op'] is or_):
            paramkws['ex'] = field

        params = self.mk_local_params(**paramkws)
        source_field = FILTER_FIELDS[field].get_source_field(self.language)

        return '%s%s' % (params, source_field)

    def get_facet_fields(self):
        return [
            self._get_facet_key(field)
            for field in self.facet_fields
        ]

    def get_fetch_fields(self):
        return tuple(
            f.get_source_field(self.language)
            for k, f in FETCH_FIELDS.items()
            if self.is_used_field(k)
        )

    def get_boost_fields(self):
        return {
            f.get_source_field(self.language): f.solr_boost
            for k, f in BOOST_FIELDS.items()
            if self.is_used_field(k)
        }

    def set_search_options(self, search):
        # hack search.options() to set our custom preferences
        # (because setting faceting options as arguments to .facet_by()
        # won't work, due to the forced tagging above)
        extra_options = self.SEARCH_OPTIONS
        _super_options = search.options
        def wrapped_options(self):
            options = _super_options()
            options.update(extra_options)
            return options

        search.options = type(search.options)(wrapped_options, search)

    def to_query(self, data, op=or_):
        if isinstance(data, str) or not isinstance(data, Iterable) or not data:
            return data

        if len(data) == 1:
            return data[0]

        Q = self.interface.Q
        # this part needed to be able to do "field:(some\\ thing OR an\\ other)"
        return DismaxString(
            "(%s)" % reduce(op, (Q(item) for item in data))
        )

    @staticmethod
    def to_object(language, **data):
        typ = data['type']
        schema = SCHEMA_MAP[typ]
        result, errors = schema.load(data, language=language)
        if errors:
            logger.error("Error parse error: %s", errors)
        return result

    @staticmethod
    def mk_local_params(**params):
        if not params:
            return ''
        return '{!%s}' % (
            " ".join(
                '%s=%s' % kv for kv in params.items()
            )
        )

    def _search(self):
        search = (
            self.interface.query(*self.qargs, **self.qkwargs)
            .filter(**self.get_filters())
            .filter(**self.get_range_filters())
            .alt_parser('edismax', qf=self.get_boost_fields())
        )
        self.set_search_options(search)

        return search

    def search(self, page=1, page_size=None, date_sort=None):
        if page_size is None:
            page_size = settings.SEARCH_PAGE_SIZE
        start = (page - 1) * page_size

        search = (
            self._search()
            .facet_by(self.get_facet_fields())
            .stats_on(self.get_stats_fields())
            .field_limit(self.get_fetch_fields())
            .paginate(start=start, rows=page_size)
        )

        if date_sort is not None:
            sort_dir = "" if date_sort else "-"
            sort_field = SORT_FIELD.get_source_field(self.language)
            search = search.sort_by("%s%s" % (sort_dir, sort_field))

        # from pprint import pprint
        # pprint(search.options(), indent=2, width=100)

        _constructor = partial(self.to_object, language=self.language)
        response = search.execute(constructor=_constructor)

        return response


empty_response = SolrResponse.from_json(repr({
    "responseHeader": {"status": 0},
    "response": {"numFound": 0,
                 "start": 0,
                 "docs": []}
}).replace("'", '"'))
