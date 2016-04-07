import scorched
from collections import Iterable
from functools import reduce
from operator import and_, or_
from django.conf import settings
from django.utils.functional import cached_property

from .xforms import SearchForm
from .schema import FILTER_FIELDS, FETCH_FIELDS, BOOST_FIELDS


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
            qkwargs['type'] = data.pop('type')
        except KeyError:
            pass

        filters = {}
        facets = []
        for name, value in data.items():
            field = FILTER_FIELDS[name].get_source_field(language)
            # also tag the field in local params
            filters['{!tag=%s}%s' % (name, field)] = self.to_query(value)
            # and exclude it during faceting
            facets.append('{!ex=%s}%s' % (name, field))

        fetch_fields = [
            f.get_source_field(language) for f in FETCH_FIELDS.values()
        ]

        boost_fields = {
            f.get_source_field(language): f.solr_boost
            for f in BOOST_FIELDS.values()
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

        return search.execute()

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


# create a default search instance
searcher = Search()
