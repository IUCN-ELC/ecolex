import logging
import scorched
from collections import Iterable
from functools import partial, reduce
from operator import and_, or_
from django.conf import settings
from django.utils.functional import cached_property

from .xforms import SearchForm
from .schema import (
    SCHEMA_MAP, FIELD_MAP,
    FILTER_FIELDS, FETCH_FIELDS, BOOST_FIELDS,
)


logger = logging.getLogger(__name__)


class SearchViewMixin(object):
    @cached_property
    def form(self):
        return SearchForm(self.request.GET)


class Search(object):
    def __init__(self, interface=None):
        if interface is None:
            interface = scorched.SolrInterface(settings.SOLR_URI)

        self.interface = interface

    def search(self, data, language):
        # q and type will be used for query-ing, the rest are filters
        qargs = []
        qkwargs = {}

        try:
            qargs.append(data.pop('q'))
        except KeyError:
            pass

        try:
            types = data.pop('type')
        except KeyError:
            types = []

        is_used_field = lambda x: True

        if types:
            qkwargs['type'] = self.to_query(types)

            _used_fields = ()
            for typ in types:
                try:
                    _used_fields += tuple(FIELD_MAP[typ])
                except KeyError:
                    # hmm. handle this in form maybe?
                    pass
            if _used_fields:
                _used_fields = tuple(FIELD_MAP['_']) + _used_fields
                is_used_field = lambda x: x in _used_fields

        filters = {}
        facets = []
        for name, value in data.items():
            if not is_used_field(name):
                continue

            field = FILTER_FIELDS[name].get_source_field(language)
            # also tag the field in local params
            filters['{!tag=%s}%s' % (name, field)] = self.to_query(value)
            # and exclude it during faceting
            facets.append('{!ex=%s}%s' % (name, field))

        fetch_fields = [
            f.get_source_field(language)
            for k, f in FETCH_FIELDS.items()
            if is_used_field(k)
        ]

        boost_fields = {
            f.get_source_field(language): f.solr_boost
            for k, f in BOOST_FIELDS.items()
            if is_used_field(k)
        }

        search = (
            self.interface.query(*qargs, **qkwargs)
            .filter(**filters)
            .facet_by(facets)
            .field_limit(fetch_fields)
            .alt_parser('edismax', qf=boost_fields)
        )

        # hack search.options() to set our faceting preferences
        # (setting them as arguments to .facet_by() won't work
        # because of the forced tagging above)
        _super_options = search.options
        def wrapped_options(self):
            options = _super_options()
            options.update({
                'facet.limit': -1,
                'facet.sort': 'index',
                'facet.method': 'enum',
                'facet.mincount': 1,
            })
            return options

        search.options = type(search.options)(wrapped_options, search)

        _constructor = partial(self.to_object, language=language)
        return search.execute(constructor=_constructor)

    def to_query(self, data):
        # silly hack to be able to do "field:(some\\ thing OR an\\ other)"
        if isinstance(data, str) or not isinstance(data, Iterable) or not data:
            return data

        if len(data) == 1:
            return data[0]

        Q = self.interface.Q
        return scorched.strings.DismaxString(
            "(%s)" % reduce(or_, (Q(item) for item in data))
        )

    @staticmethod
    def to_object(language, **data):
        typ = data['type']
        schema = SCHEMA_MAP[typ]
        result, errors = schema.load(data, language=language)
        if errors:
            logger.error("Error parse error: %s", errors)
        return result


# create a default search instance
searcher = Search()
