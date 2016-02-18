from rest_framework.viewsets import GenericViewSet
from rest_framework.mixins import ListModelMixin#, RetrieveModelMixin
from ecolex import definitions
from ecolex.search import SearchMixin
from . import serializers
from . import pagination


class SearchResultViewSet(ListModelMixin,
                          GenericViewSet,
                          SearchMixin):
    serializer_class = serializers.SearchResultSerializer
    pagination_class = pagination.SolrQuerysetPagination

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_queryset(self, *args, **kwargs):
        self._prepare(self.request.query_params)
        results = self.search()
        return results


'''
class AuthorFacetViewSet(ListModelMixin,
                         GenericViewSet):
    pass
'''
