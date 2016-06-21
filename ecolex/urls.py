from django.conf import settings
from django.conf.urls import include, url
from django.contrib import admin
from django.contrib.sitemaps.views import index, sitemap
from django.views.generic import TemplateView
# from django.conf.urls.i18n import i18n_patterns
from solid_i18n.urls import solid_i18n_patterns as i18n_patterns

from ecolex.sitemaps import DocumentSitemap, StaticViewSitemap
from .views import (
    DesignPlayground, FaoFeedView, Homepage,
    LegislationRedirectView, OldEcolexRedirectView,
    PageView, debug, ExportView
)
from . import xviews as views
from .api import urls as api_urls


sitemaps = {
    'static': StaticViewSitemap,
    'documents': DocumentSitemap,
}
admin.autodiscover()

urlpatterns = [
    url(r'^fao/$', FaoFeedView.as_view(), name='fao_feeder'),
    url(r'^i18n/', include('django.conf.urls.i18n')),
    url(r'^sitemap\.xml$', index, {'sitemaps': sitemaps}),
    url(r'^sitemap-(?P<section>.+)\.xml$', sitemap, {
        'sitemaps': sitemaps,
        'template_name': 'sitemaps/translated_sitemap.xml',
    }),
    url(r'^export/$', ExportView.as_view(), name='export'),
]

urlpatterns += i18n_patterns(
    url(r'^$', Homepage.as_view(), name="homepage"),

    url(r'^result/$', views.SearchResults.as_view(),
        name="results"),

    url(r'^details/(?P<slug>[^/]+)/decisions/$',
        views.RelatedDecisions.as_view(),
        name="related_decisions"),
    url(r'^details/(?P<slug>[^/]+)/literatures/$',
        views.RelatedLiteratures.as_view(),
        name="related_literatures"),
    url(r'^details/(?P<slug>[^/]+)/court-decisions/$',
        views.RelatedCourtDecisions.as_view(),
        name="related_court_decisions"),

    url(r'^details/(?P<slug>[^/]+)/participants/$',
        views.TreatyParticipants.as_view(), name="treaty-participants"),

    url(r'^details/decision/(?P<slug>[^/]+)/$',
        views.DecisionDetails.as_view(),
        name="decision_details"),
    url(r'^details/treaty/(?P<slug>[^/]+)/$',
        views.TreatyDetails.as_view(),
        name="treaty_details"),
    url(r'^details/literature/(?P<slug>[^/]+)/$',
        views.LiteratureDetails.as_view(),
        name="literature_details"),
    url(r'^details/court-decision/(?P<slug>[^/]+)/$',
        views.CourtDecisionDetails.as_view(),
        name="court_decision_details"),
    url(r'^details/legislation/(?P<slug>[^/]+)/$',
        views.LegislationDetails.as_view(),
        name="legislation_details"),

    url(r'^delete/$', views.DocumentDeleteSearch.as_view(),
        name='delete_search'),
    url(r'^delete/(?P<slug>[^/]+)/$', views.DocumentDelete.as_view(),
        name='delete_record'),

    url(r'^p/(?P<slug>\w+)/', PageView.as_view(),
        name="page"),

    url(r'^ecolex/ledge/view/RecordDetails/$',
        OldEcolexRedirectView.as_view(), name="oldecolex_redirect"),
    url(r'^(?P<doc_type>\w+)/details/(?P<doc_id>[^/]+)/$',
        LegislationRedirectView.as_view(), name="legislation_redirect"),
)


urlpatterns += [
    url(r'^api/', include(api_urls, namespace="api")),
    url(r'^admin/', include(admin.site.urls)),
]

handler404 = views.PageNotFound.as_view()
handler500 = views.InternalError.as_view()


if settings.DEBUG:
    urlpatterns += [
        url(r'^_debug', debug, name="debug"),
        url(r'^playground/$', DesignPlayground.as_view(), name="playground"),
        # Do not allow indexing on staging (assuming DEBUG=True on staging)
        # For more complex indexing rules, see:
        # https://github.com/jazzband/django-robots
        url(r'^robots.txt/$', TemplateView.as_view(template_name='robots.txt',
            content_type='text/plain')),
    ]
    # Local urls
    try:
        from ecolex import local_urls
    except ImportError:
        pass
    else:
        urlpatterns.append(url(r'^', include(local_urls)))
