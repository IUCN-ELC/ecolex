from django.conf.urls import include, url
from rest_framework.routers import DefaultRouter
from ecolex.schema import FACET_FIELDS
from . import views


router = DefaultRouter()
router.register(r'search', views.SearchResultViewSet, base_name="search")

# to do this dynamically we need to provide a `field` initkwarg to as_view(),
# which the drf router can't handle
facet_urls = [
    url(r'%s-list/' % field.replace('_', '-'),
        views.BaseFacetViewSet.as_view(actions={'get': 'list'}, field=field),
        name="%s-list" % field.replace('_', '-')
    )
    for field in FACET_FIELDS.keys()
]


urlpatterns = [
    url(r'^v1.0/', include(router.urls + facet_urls))
]
