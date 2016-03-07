from django.conf.urls import patterns, url
from rest_framework.routers import DefaultRouter
from . import views


router = DefaultRouter()
router.register(r'search', views.SearchResultViewSet, base_name="search")
router.register(r'countries', views.CountryFacetViewSet, base_name="countries")
#router.register(r'subjects', views.SubjectFacetViewSet, base_name="subjects")
router.register(r'keywords', views.KeywordFacetViewSet, base_name="keywords")
router.register(r'authors', views.AuthorFacetViewSet, base_name="authors")


urlpatterns = router.urls
