import logging
import datetime
from collections import defaultdict
from ecolex.lib.utils import is_iterable
from functools import reduce
from operator import and_, or_, itemgetter
from marshmallow.exceptions import ValidationError
from scorched import SolrInterface
from scorched.response import SolrResponse
from scorched.strings import DismaxString
from unidecode import unidecode
from django.conf import settings
from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist
from django.utils.functional import LazyObject
from django.utils.html import strip_tags

from .schema import (
    SCHEMA_MAP, FIELD_MAP,
    FILTER_FIELDS, FACET_FIELDS, STATS_FIELDS,
    FETCH_FIELDS, BOOST_FIELDS, HIGHLIGHT_FIELDS,
    SORT_FIELD,
    to_object,
)


logger = logging.getLogger(__name__)


class __DefaultInterface(LazyObject):
    # this exists with the sole purpose to defer reading settings
    def _setup(self):
        self._wrapped = SolrInterface(settings.SOLR_URI)


DEFAULT_INTERFACE = __DefaultInterface()


class Queryer(object):
    SEARCH_OPTIONS = {
        'hl': True,
        'hl.fragsize': 0,
        'hl.snippets': 100,
        'hl.simple.pre': '<em class="hl">',
    }

    def __init__(self, data, language, interface=DEFAULT_INTERFACE):
        self.language = language
        self.interface = interface
        self.qargs = []

        try:
            q = data.pop('q')
        except KeyError:
            pass
        else:
            if q:
                self.qargs.append(DismaxString(q))

    def _execute(self, search, options=None):
        # set search options last or they'll get overwritten
        self.set_search_options(search, options)
        response = search.execute()
        return response

    def set_search_options(self, search, options=None):
        # hack search.options() to set our custom preferences
        extra_options = self.SEARCH_OPTIONS
        if options:
            extra_options.update(options)

        _super_options = search.options

        def wrapped_options(self):
            options = _super_options()
            options.update(extra_options)
            return options

        search.options = type(search.options)(wrapped_options, search)

    def get_highlight_fields(self):
        return tuple(
            field
            for k, f in HIGHLIGHT_FIELDS.items()
            for field in f.get_source_fields()
        )

    def _handle_highlight(self, response):
        for doc in response.result.docs:
            try:
                hls = response.highlighting[doc['id']]
            except KeyError:
                continue

            for field, hl in hls.items():
                original = doc[field]

                if not isinstance(original, list):
                    doc[field] = hl[0]

                elif len(original) == 1:
                    doc[field] = hl

                else:
                    # we need to iterate through the items and replace
                    # the proper ones
                    for highlighted in hl:
                        # TODO: do we ever return other html with the results?
                        idx = original.index(strip_tags(highlighted))
                        original[idx] = highlighted

    def to_query(self, data, op=or_):
        if not is_iterable(data) or not data:
            return data

        if len(data) == 1:
            return data[0]

        Q = self.interface.Q
        # this part needed to be able to do "field:(some\\ thing OR an\\ other)"
        return DismaxString(
            "(%s)" % reduce(op, (Q(item) for item in data))
        )

    def get(self, **kwargs):
        search = (
            self.interface.query(*self.qargs)
            .filter(**{
                k: self.to_query(v)
                for k, v in kwargs.items()
            })
            .highlight(self.get_highlight_fields())
            .paginate(start=0, rows=1)  # fetch a single row
        )

        response = self._execute(search)

        if response.result.numFound > 1:
            raise MultipleObjectsReturned()
        try:
            result = response.result.docs[0]
        except IndexError:
            raise ObjectDoesNotExist()

        self._handle_highlight(response)
        return to_object(result, self.language)

    def _paginate(self, search, page=1, page_size=None):
        if page_size is None:
            page_size = settings.SEARCH_PAGE_SIZE
        start = (page - 1) * page_size
        return search.paginate(start=start, rows=page_size)

    def _sort(self, search, date_sort=None):
        if date_sort is None:
            return search

        sort_dir = "" if date_sort else "-"
        sort_field = SORT_FIELD.get_source_field(self.language)
        return search.sort_by("%s%s" % (sort_dir, sort_field))

    def get_fetch_fields(self, extra_fields=None):
        # TODO: this is used only in contexts where a single type of document
        # is retrieved. make it aware of the type / unify with below.
        ffs = set(FETCH_FIELDS.values())
        if extra_fields:
            ffs.update(extra_fields)

        return tuple(
            field
            for f in ffs
            for field in f.get_source_fields()
        )

    def findany(self, page=1, page_size=None, date_sort=None,
                fetch_fields=None, options=None, **kwargs):
        Q = self.interface.Q
        _f = reduce(or_,(Q(**{k: self.to_query(v)})
                         for k, v in kwargs.items()))

        search = (
            self.interface.query()
            .filter(_f)
            .field_limit(self.get_fetch_fields(fetch_fields))
        )

        search = self._paginate(search, page=page, page_size=page_size)
        search = self._sort(search, date_sort=date_sort)

        response = self._execute(search, options=options)

        return QueryResponse(response, language=self.language)


class Searcher(Queryer):
    SEARCH_OPTIONS = dict(Queryer.SEARCH_OPTIONS, **{
        'q.op': 'AND',
        'facet.limit': -1,
        'facet.sort': 'index',
        'facet.method': 'enum',
        'facet.mincount': 1,
        'spellcheck.collate': True,
    })

    STATS_KEYS = ('min', 'max')

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
        super().__init__(data, language, interface=interface)

        self.valid = True

        types = data.get('type', [])

        try:
            self.set_types(types)
        except ValueError:
            # all types requested are invalid
            self.valid = False
            return

        self.prepare_filters(data)
        self.prepare_stats()
        self.prepare_range_filters(data)
        self.prepare_facets()

    def set_types(self, types):
        if not types:
            # momentarily set _used_fields even with no given type,
            # to protect agains rogue form fields. TODO: fix.
            # self._used_fields = None
            self._used_fields = reduce(or_,
                                       (set(fs) for fs in FIELD_MAP.values()))
            return

        types = set(SCHEMA_MAP.keys()).intersection(types)
        if not types:
            raise ValueError

        self._used_fields = reduce(or_,
                                   (set(FIELD_MAP[t]) for t in types),
                                   set(FIELD_MAP['_']))

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
        stats_keys = self.STATS_KEYS
        range_filters = defaultdict(lambda: dict.fromkeys(stats_keys))

        for field in self.stats_fields:
            for typ in stats_keys:
                try:
                    value = data["%s_%s" % (field, typ)]
                except KeyError:
                    continue
                if not value:
                    continue

                # we're only dealing with dates (i.e. int years) for the moment
                # form should give us all this stuff of the proper datatype
                if STATS_FIELDS[field].datatype in ('date', 'datetime'):
                    if typ == 'max':
                        value += 1

                    try:
                        value = datetime.datetime(value, 1, 1)
                    except TypeError:
                        continue

                    if typ == 'max':
                        value -= datetime.timedelta(seconds=1)

                range_filters[field][typ] = value

        self.range_filters = range_filters

    def prepare_facets(self):
        fields = [
            field
            for field in FACET_FIELDS.keys()
            if self.is_used_field(field)
        ]
        self.facet_fields = fields

    def _get_filter_key(self, field):
        # tag fields used for faceting if OR-ed
        if (field in self.facet_fields and self.filters[field]['op'] is or_):
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
        # override default statistics,
        paramkws = dict.fromkeys(self.STATS_KEYS, 'true')
        # key returned fields to our field names,
        paramkws['key'] = field
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
        if (field in self.filters and self.filters[field]['op'] is or_):
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
        # we need to get fields in all languages
        return tuple(
            field
            for k, f in FETCH_FIELDS.items()
            for field in f.get_source_fields()
            if self.is_used_field(k)
        )

    def get_boost_fields(self):
        return {
            field: f.solr_boost
            for k, f in BOOST_FIELDS.items()
            for field in f.get_source_fields()
            # if self.is_used_field(k)
        }

    def get_highlight_fields(self):
        return tuple(
            field
            for k, f in HIGHLIGHT_FIELDS.items()
            for field in f.get_source_fields()
            if self.is_used_field(k)
        )

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
            self.interface.query(*self.qargs)
            .filter(**self.get_filters())
            .filter(**self.get_range_filters())
            # Boosting is done by solrconfig.xml as of now. Leaving this line
            # for reference.
            # .alt_parser('edismax', qf=self.get_boost_fields())
        )

        return search

    def _execute(self, search):
        # TODO: this is the place to cache some facets
        do_facets = True

        if do_facets:
            search = search.facet_by(self.get_facet_fields())

        response = super()._execute(search)

        if do_facets:
            self._handle_facets(response)

        return response

    @staticmethod
    def _normalize_facet(text):
        return unidecode(text).lower()

    @classmethod
    def _convert_facet(cls, data):
        item, count = data

        return {
            'id': cls._normalize_facet(item),
            'text': item,
            'count': count,
        }

    def _handle_facets(self, response):
        facets = response.facet_counts.facet_fields
        for k, data in facets.items():
            facets[k] = sorted(map(self._convert_facet, data),
                               key=itemgetter('id', 'text'))

    def _handle_stats(self, response):
        stats = response.stats.stats_fields
        for k, data in stats.items():
            field = STATS_FIELDS[k]._field
            parsed = {}
            if data is None:
                continue
            for item, value in data.items():
                try:
                    value = field.deserialize(value)
                except ValidationError as e:
                    logger.error("Stats parse error: %s", e)
                    continue

                # we will convert dates to their year component alone,
                # because that's what we deal with for now
                if isinstance(value, datetime.date):
                    value = value.year

                parsed[item] = value

            stats[k] = parsed

    def _handle_suggestions(self, response):
        rsp = response.spellcheck
        rsp['collations'] = rsp.get('collations', [])[1:]

    def search(self, page=1, page_size=None, date_sort=None):
        if not self.valid:
            return SearchResponse()

        search = (
            self._search()
            .stats_on(self.get_stats_fields())
            .field_limit(self.get_fetch_fields())
            .highlight(self.get_highlight_fields())
            .spellcheck()
        )

        search = self._paginate(search, page=page, page_size=page_size)
        search = self._sort(search, date_sort=date_sort)

        response = self._execute(search)
        self._handle_stats(response)
        self._handle_highlight(response)
        self._handle_suggestions(response)

        return SearchResponse(response, language=self.language)

    def get_facets(self, facets):
        if facets:
            facets = [f for f in facets
                      if f in self.facet_fields]

            if not facets:
                raise ValueError("Illegal facets requested.")
            else:
                # TODO: overwriting these is not pretty
                self.facet_fields = facets

        search = (
            self._search()
            .paginate(rows=0)
        )

        response = self._execute(search)
        return SearchResponse(response, language=self.language).facets


_empty_response = SolrResponse.from_json(repr({
    "responseHeader": {"status": 0},
    "response": {"numFound": 0,
                 "start": 0,
                 "docs": []}
}).replace("'", '"'))


class QueryResponse(object):
    def __init__(self, response=None, language=None):
        if response is None:
            response = _empty_response
        else:
            assert language is not None

        self.count = response.result.numFound
        self.start = response.result.start
        self.results = [
            to_object(item, language)
            for item in response.result.docs
        ]

    @staticmethod
    def to_object(data, language):
        typ = data['type']
        schema = SCHEMA_MAP[typ]
        result, errors = schema.load(data, language=language)
        if errors:
            logger.error("Parse error: %s", errors)
        return result

    def __len__(self):
        return self.count

    def __iter__(self):
        return iter(self.results)


class SearchResponse(QueryResponse):
    def __init__(self, response=None, language=None):
        super().__init__(response=response, language=language)

        self.facets = response.facet_counts.facet_fields
        self.stats = response.stats.stats_fields
        self.suggestions = response.spellcheck.get('collations')

    def __len__(self):
        return self.count

    def __iter__(self):
        return iter(self.results)
