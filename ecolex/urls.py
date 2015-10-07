from django.conf.urls import patterns, url
from .views import (
    SearchResults, PageView, ResultDetailsDecisions, Homepage,
    ResultDetailsParticipants, debug, SearchResultsAjax, DecMeetingView,
    TreatyParticipantView, DecisionDetails, TreatyDetails, LiteratureDetails
)


urlpatterns = patterns('',
    url(r'^$', Homepage.as_view(), name="homepage"),
    url(r'^result/$', SearchResults.as_view(),
        name="results"),
    url(r'^result/ajax/', SearchResultsAjax.as_view(),
        name="results_ajax"),
    url(r'^meeting/(?P<id>[^/]+)/', DecMeetingView.as_view(),
        name="meeting_details"),
    url(r'^participant/(?P<id>[a-z\-]+)/', TreatyParticipantView.as_view(),
        name="participant_details"),
    url(r'^details/(?P<id>[^/]+)/decisions/$', ResultDetailsDecisions.as_view(),
        name="resultDecisions"),
    url(r'^details/(?P<id>[^/]+)/participants/$',
        ResultDetailsParticipants.as_view(), name="resultParticipants"),
    url(r'^details/decision/(?P<id>[^/]+)/$', DecisionDetails.as_view(),
        name="decision_details"),
    url(r'^details/treaty/(?P<id>[^/]+)/$', TreatyDetails.as_view(),
        name="treaty_details"),
    url(r'^details/literature/(?P<id>[^/]+)/$', LiteratureDetails.as_view(),
        name="literature_details"),

    url(r'^p/(?P<slug>\w+)/', PageView.as_view(),
        name="page"),
    url(r'^_debug', debug, name="debug"),
)
