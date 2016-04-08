from django.conf import settings
from django.conf.urls import include, patterns, url
from django.conf.urls.i18n import i18n_patterns
from rest_framework import routers

from .views import (
    SearchResults, PageView, ResultDetailsDecisions, Homepage,
    ResultDetailsParticipants, debug, SearchResultsAjax,
    DecisionDetails, TreatyDetails, LiteratureDetails,
    CourtDecisionDetails, ResultDetailsLiteratures, FaoFeedView,
    ResultDetailsCourtDecisions, LegislationDetails,
    SelectFacetsAjax, DesignPlayground, LegislationRedirectView,
)
from .api import urls as api_urls

urlpatterns = patterns(
    '',
    url(r'^fao/$', FaoFeedView.as_view(), name='fao_feeder'),
    url(r'^i18n/', include('django.conf.urls.i18n')),
)

urlpatterns += i18n_patterns(
    '',
    url(r'^$', Homepage.as_view(), name="homepage"),
    url(r'^result/$', SearchResults.as_view(),
        name="results"),
    url(r'^result/ajax/', SearchResultsAjax.as_view(),
        name="results_ajax"),
    url(r'^facets/ajax/', SelectFacetsAjax.as_view(),
        name="facets_ajax"),

    url(r'^details/(?P<slug>[^/]+)/decisions/$',
        ResultDetailsDecisions.as_view(), name="resultDecisions"),
    url(r'^details/(?P<slug>[^/]+)/literatures/$',
        ResultDetailsLiteratures.as_view(), name="resultLiteratures"),
    url(r'^details/(?P<slug>[^/]+)/court-decisions/$',
        ResultDetailsCourtDecisions.as_view(), name="resultCourtDecisions"),
    url(r'^details/(?P<slug>[^/]+)/participants/$',
        ResultDetailsParticipants.as_view(), name="resultParticipants"),

    url(r'^details/decision/(?P<slug>[^/]+)/$', DecisionDetails.as_view(),
        name="decision_details"),
    url(r'^details/treaty/(?P<slug>[^/]+)/$', TreatyDetails.as_view(),
        name="treaty_details"),
    url(r'^details/literature/(?P<slug>[^/]+)/$', LiteratureDetails.as_view(),
        name="literature_details"),
    url(r'^details/court-decision/(?P<slug>[^/]+)/$',
        CourtDecisionDetails.as_view(), name="court_decision_details"),
    url(r'^details/legislation/(?P<slug>[^/]+)/$',
        LegislationDetails.as_view(), name="legislation_details"),
    url(r'^p/(?P<slug>\w+)/', PageView.as_view(),
        name="page"),

    url(r'^(?P<doc_type>\w+)/details/(?P<doc_id>[^/]+)/$',
        LegislationRedirectView.as_view(), name="legislation_redirect"),
)

urlpatterns += patterns(
    '',
    url(r'^api/', include(api_urls, namespace="api")),
)


if settings.DEBUG:
    urlpatterns += patterns(
        '',
        url(r'^_debug', debug, name="debug"),
        url(r'^playground/$', DesignPlayground.as_view(), name="playground"),
    )
