import logging
import scorched
from collections import Iterable
from functools import partial, reduce
from operator import and_, or_
from django.conf import settings
from django.utils.functional import cached_property, LazyObject

from .xforms import SearchForm
from .schema import (
    SCHEMA_MAP, FIELD_MAP,
    FILTER_FIELDS, FETCH_FIELDS, BOOST_FIELDS,
)


logger = logging.getLogger(__name__)


class __DefaultInterface(LazyObject):
    # this exists with the sole purpose to defer reading settings
    def _setup(self):
        self._wrapped = scorched.SolrInterface(settings.SOLR_URI)


DEFAULT_INTERFACE = __DefaultInterface()


class SearchViewMixin(object):
    @cached_property
    def form(self):
        return SearchForm(self.request.GET)


class Search(object):
    SEARCH_OPTIONS = {
        'facet.limit': -1,
        'facet.sort': 'index',
        'facet.method': 'enum',
        'facet.mincount': 1,
    }

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
        self.prepare_facets()

    def set_types(self, types):
        if not types:
            self._used_fields = None
            return

        types = set(SCHEMA_MAP.keys()).intersection(types)
        if not types:
            raise ValueError

        self._used_fields = reduce(or_,
                                   [set(FIELD_MAP[t]) for t in types],
                                   set(FIELD_MAP['_']))

        self.qkwargs['type'] = self.to_query(types)

    def is_used_field(self, field):
        if self._used_fields is None:
            return True
        else:
            return field in self._used_fields

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

    def prepare_facets(self):
        fields = [
            field
            for field in FILTER_FIELDS.keys()
            if self.is_used_field(field)
        ]
        self.facet_fields = fields

    def _get_filter_key(self, field):
        # tag fields used for faceting if OR-ed
        params = ''
        if (field in self.facet_fields
            and self.filters[field]['op'] is or_):
            params = '{!tag=%s}' % field

        source_field = FILTER_FIELDS[field].get_source_field(self.language)

        return '%s%s' % (params, source_field)

    def get_filters(self):
        return {
            self._get_filter_key(field): self.to_query(v['data'], v['op'])
            for field, v in self.filters.items()
        }

    def _get_facet_key(self, field):
        # key return fields to our field names to simplify code
        params = {
            'key': field
        }
        # and exclude fields used for filtering that are OR-ed
        if (field in self.filters
            and self.filters[field]['op'] is or_):
            params['ex'] = field

        params = " ".join(['%s=%s' % kv for kv in params.items()])
        source_field = FILTER_FIELDS[field].get_source_field(self.language)

        return '{!%s}%s' % (params, source_field)

    def get_facets(self):
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
        # hack search.options() to set our faceting preferences
        # (setting them as arguments to .facet_by() won't work
        # because of the forced tagging above)
        _super_options = search.options
        extra_options = self.SEARCH_OPTIONS
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
        return scorched.strings.DismaxString(
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

    def execute(self):
        search = (
            self.interface.query(*self.qargs)
            .query(**self.qkwargs)
            .filter(**self.get_filters())
            .facet_by(self.get_facets())
            .field_limit(self.get_fetch_fields())
            .alt_parser('edismax', qf=self.get_boost_fields())
        )

        self.set_search_options(search)

        _constructor = partial(self.to_object, language=self.language)
        response = search.execute(constructor=_constructor)

        return response
