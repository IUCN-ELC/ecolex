from django.contrib.sitemaps import Sitemap
from django.core.urlresolvers import reverse
from django.core.paginator import Paginator

from ecolex.definitions import STATIC_PAGES
from ecolex.xsearch import Queryer


class SolrQueryPaginator(Paginator):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.queryer = self.object_list
        self.object_list = self.queryer.findany(page_size=0)

    def page(self, number):
        number = self.validate_number(number)
        sliced_obj_list = self.queryer.findany(page=number,
                                               page_size=self.per_page)
        return self._get_page(sliced_obj_list, number, self)


class CustomSitemap(Sitemap):
    def _get_paginator(self):
        return SolrQueryPaginator(self.queryer(), self.limit)
    paginator = property(_get_paginator)


class StaticViewSitemap(Sitemap):
    priority = 0.5
    changefreq = 'yearly'

    def items(self):
        return STATIC_PAGES

    def location(self, item):
        return reverse('page', kwargs={'slug': item})


class DocumentSitemap(CustomSitemap):
    pritiority = 1
    changefreq = 'weekly'
    limit = 1000

    def queryer(self):
        return Queryer({}, language='en')

    def location(self, item):
        return item.details_url

    def lastmod(self, item):
        return item.updated_at or item.indexed_at
