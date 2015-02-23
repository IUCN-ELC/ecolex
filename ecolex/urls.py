from django.conf.urls import patterns, include, url
from django.contrib import admin
from .views import (
    SearchView, SearchResults, PageView, ResultDetails, debug,
    SearchResultsAjax, Homepage, DecMeetingView, TreatyParticipantView
)


urlpatterns = patterns('',
   url(r'^$', Homepage.as_view(), name="homepage"),
   url(r'^result/$', SearchResults.as_view(),
       name="results"),
   url(r'^result/ajax/', SearchResultsAjax.as_view(),
       name="results_ajax"),
   url(r'^meeting/(?P<id>[^/]+)/', DecMeetingView.as_view(),
       name="meeting_details"),
   url(r'^participant/(?P<id>[^/]+)/', TreatyParticipantView.as_view(),
       name="participant_details"),
   url(r'^details/(?P<id>[^/]+)/', ResultDetails.as_view(),
       name="result"),
   url(r'^p/(?P<slug>\w+)/', PageView.as_view(),
       name="page"),
   url(r'^_debug', debug, name="debug"),
)
