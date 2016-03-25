from ecolex.definitions import SELECT_FACETS as FACET_MAP
from django.conf.urls import include, url
from rest_framework.routers import DefaultRouter
from . import views


router = DefaultRouter()
router.register(r'search', views.SearchResultViewSet, base_name="search")

# to do this dynamically we need to provide a `field` initkwarg to as_view(),
# which the drf router can't handle
facet_urls = [
    url(r'%s-list/' % facet.replace('_', '-'),
        views.BaseFacetViewSet.as_view(actions={'get': 'list'}, field=field),
        name="%s-list" % facet.replace('_', '-')
    )
    for field, facet in FACET_MAP.items()
]


urlpatterns = [
    url(r'^v1.0/', include(router.urls + facet_urls))
]
