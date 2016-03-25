import re
from django.core.cache import cache
from rest_framework.viewsets import GenericViewSet
from rest_framework.mixins import ListModelMixin#, RetrieveModelMixin
from ecolex import definitions
from ecolex.search import SearchMixin
from ecolex.lib import unaccent
from . import serializers
from . import pagination


class ApiViewMixin(object):
    def perform_authentication(self, request):
        # skip authentication, we haven't any
        pass


# TODO: get_queryset is being called twice. wut?

class SearchResultViewSet(ApiViewMixin,
                          ListModelMixin,
                          GenericViewSet,
                          SearchMixin):
    serializer_class = serializers.SearchResultSerializer
    pagination_class = pagination.SolrQuerysetPagination

    def get_queryset(self, *args, **kwargs):
        self._prepare(self.request.query_params)
        results = self.search()
        return results


class BaseFacetViewSet(ApiViewMixin,
                       ListModelMixin,
                       GenericViewSet,
                       SearchMixin):
    serializer_class = serializers.SearchFacetSerializer
    pagination_class = pagination.SolrFacetPagination

    # must be defined by subclasses
    field = None

    def get_queryset(self, *args, **kwargs):
        field = self.field

        self._prepare(self.request.query_params)
        facet = {
            'field': field,
            # fetch all facet values and do search and pagination locally
            'limit': -1,
        }

        results = self.search(only_facet=facet).get_facets()[field]

        search = self.request.query_params.get('search', '').strip()
        if search:
            def _matches(item):
                item = unaccent(item)
                terms = (t for t in search.split(" ") if t)

                return all(map(
                    lambda term: re.search(r'\b%s' % unaccent(term),
                                           item, re.I),
                    terms
                ))

            items = (item for item in results.items() if _matches(item[0]))
        else:
            items = results.items()

        return self.serializer_class.convert_results(items)
