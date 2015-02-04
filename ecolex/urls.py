from django.conf.urls import patterns, include, url
from django.contrib import admin
from .views import SearchView, SearchViewWithResults, page, ResultDetails


urlpatterns = patterns('',
    url(r'^$', SearchView.as_view(), name="homepage"),
    url(r'^result/', SearchViewWithResults.as_view(), name="results"),
    url(r'^details/(?P<id>[^/]+)/', ResultDetails.as_view(), name="result"),
    url(r'^p/(?P<slug>\w+)/', page, name="page"),
)
