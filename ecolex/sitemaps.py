from django.contrib.sitemaps import Sitemap
from django.core.urlresolvers import reverse

from ecolex.definitions import STATIC_PAGES
from ecolex.xsearch import Queryer


class StaticViewSitemap(Sitemap):
    priority = 0.5
    changefreq = 'yearly'

    def items(self):
        return STATIC_PAGES

    def location(self, item):
        return reverse('page', kwargs={'slug': item})


class DocumentSitemap(Sitemap):
    pritiority = 1
    changefreq = 'weekly'
    limit = 15000

    def items(self):
        queryer = Queryer({}, language='en')
        response = queryer.findany(page_size=999999)
        return response.results

    def location(self, item):
        return item.details_url

    def lastmod(self, item):
        return item.updated_at or item.indexed_at
