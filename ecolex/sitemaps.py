from django.contrib.sitemaps import Sitemap
from django.core.urlresolvers import reverse

from ecolex.definitions import STATIC_PAGES


class StaticViewSitemap(Sitemap):
    priority = 0.5
    changefreq = 'yearly'

    def items(self):
        return STATIC_PAGES

    def location(self, item):
        return reverse('page', kwargs={'slug': item})
