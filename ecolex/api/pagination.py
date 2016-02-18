from django.core.paginator import Paginator as DjangoPaginator
from rest_framework.pagination import BasePagination, PageNumberPagination


class SolrQuerysetPaginator(DjangoPaginator):
    def page(self, number):
        number = int(number)
        self.object_list.set_page(number, perpage=self.per_page)
        return self._get_page(self.object_list, number, self)

    @property
    def num_pages(self):
        return self.object_list.pages()


class SolrQuerysetPagination(PageNumberPagination):
    django_paginator_class = SolrQuerysetPaginator
