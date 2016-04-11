from django.conf import settings
from django.conf.urls import include, url
#from django.conf.urls.i18n import i18n_patterns
from solid_i18n.urls import solid_i18n_patterns as i18n_patterns

from .views import (
    CourtDecisionDetails, DecisionDetails, DesignPlayground, FaoFeedView,
    Homepage, LegislationDetails, LiteratureDetails, PageView,
    ResultDetailsCourtDecisions, ResultDetailsDecisions,
    ResultDetailsLiteratures, ResultDetailsParticipants, SearchResults,
    TreatyDetails, debug,
)
from .xviews import SearchResultsView
from .api import urls as api_urls

urlpatterns = [
    url(r'^fao/$', FaoFeedView.as_view(), name='fao_feeder'),
    url(r'^i18n/', include('django.conf.urls.i18n')),
]

urlpatterns += i18n_patterns(
    url(r'^$', Homepage.as_view(), name="homepage"),
    url(r'^result/$', SearchResults.as_view(),
        name="results"),

    url(r'^xresult/$', SearchResultsView.as_view(),
        name="xresults"),

    url(r'^details/(?P<id>[^/]+)/decisions/$',
        ResultDetailsDecisions.as_view(), name="resultDecisions"),
    url(r'^details/(?P<id>[^/]+)/literatures/$',
        ResultDetailsLiteratures.as_view(), name="resultLiteratures"),
    url(r'^details/(?P<id>[^/]+)/court-decisions/$',
        ResultDetailsCourtDecisions.as_view(), name="resultCourtDecisions"),
    url(r'^details/(?P<id>[^/]+)/participants/$',
        ResultDetailsParticipants.as_view(), name="resultParticipants"),
    url(r'^details/decision/(?P<id>[^/]+)/$', DecisionDetails.as_view(),
        name="decision_details"),
    url(r'^details/treaty/(?P<id>[^/]+)/$', TreatyDetails.as_view(),
        name="treaty_details"),
    url(r'^details/literature/(?P<id>[^/]+)/$', LiteratureDetails.as_view(),
        name="literature_details"),
    url(r'^details/court-decision/(?P<id>[^/]+)/$',
        CourtDecisionDetails.as_view(), name="court_decision_details"),
    url(r'^details/legislation/(?P<id>[^/]+)/$',
        LegislationDetails.as_view(), name="legislation_details"),
    url(r'^p/(?P<slug>\w+)/', PageView.as_view(),
        name="page"),
)

urlpatterns += [
    url(r'^api/', include(api_urls, namespace="api")),
]


if settings.DEBUG:
    urlpatterns += [
        url(r'^_debug', debug, name="debug"),
        url(r'^playground/$', DesignPlayground.as_view(), name="playground"),
    ]
    # Local urls
    try:
        from ecolex import local_urls
    except ImportError:
        pass
    else:
        urlpatterns.append(url(r'^', include(local_urls)))
