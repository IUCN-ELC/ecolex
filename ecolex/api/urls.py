from django.conf.urls import patterns, url
from rest_framework.routers import DefaultRouter
from . import views


router = DefaultRouter()
router.register(r'search', views.SearchResultViewSet, base_name='s')
#router.register(r'authors', views.AuthorFacetViewSet)


urlpatterns = router.urls
