from django.conf.urls import patterns, include, url
from django.contrib import admin
from .views import (
    SearchView, SearchResults, PageView, ResultDetails, debug,
    SearchResultsAjax, Homepage,
)


urlpatterns = patterns('',
   url(r'^$', Homepage.as_view(), name="homepage"),
   url(r'^result/$', SearchResults.as_view(),
       name="results"),
   url(r'^result/ajax/', SearchResultsAjax.as_view(),
       name="results_ajax"),
   url(r'^details/(?P<id>[^/]+)/', ResultDetails.as_view(),
       name="result"),
   url(r'^p/(?P<slug>\w+)/', PageView.as_view(),
       name="page"),
   url(r'^_debug', debug, name="debug"),
)
