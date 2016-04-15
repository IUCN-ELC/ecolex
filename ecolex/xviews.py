import math
from collections import OrderedDict
from django.conf import settings
from django.views.generic import TemplateView
from django.http import QueryDict
from django.utils.functional import cached_property
from django.utils.translation import get_language
from .xforms import SearchForm
from .xsearch import Searcher, SearchResponse


class HomepageView(TemplateView):
    template_name = 'homepage.html'

homepage_view = HomepageView.as_view()


class SearchViewMixin(object):
    @cached_property
    def form(self):
        return SearchForm(self.request.GET)


class SearchResultsView(SearchViewMixin, TemplateView):
    template_name = 'list_results.html'

    def get(self, request, *args, **kwargs):
        if not self.form.changed_data:
            return homepage_view(request, *args, **kwargs)

        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        form = self.form

        if not form.is_valid():
            response = SearchResponse()
            page = 1
        else:
            data = form.cleaned_data.copy()

            page = data.pop('page')
            sortby = data.pop('sortby')

            date_sort = {
                form.SORT_DEFAULT: None,
                form.SORT_ASC: True,
                form.SORT_DESC: False,
            }[sortby]

            searcher = Searcher(data, language=get_language())
            response = searcher.search(page=page, date_sort=date_sort)

        ctx['form'] = self.form
        ctx['results'] = response
        ctx['facets'] = response.facets
        ctx['stats'] = response.stats
        ctx['suggestions'] = (response.suggestions if settings.TEXT_SUGGESTION
                              else [])
        ctx['pages'] = self.get_page_details(page, response.count)

        return ctx

    def get_page_details(self, current, result_count, page_size=None):
        if page_size is None:
            page_size = settings.SEARCH_PAGE_SIZE

        page_count = math.ceil(result_count / page_size)

        if page_count <= 1:
            _url = self.form.urlencoded()
            return {
                'number': 1,
                'count': 1,
                'list': [1],
                'urls': {1: _url},
                'next_url': None,
                'prev_url': None,
                'first_url': _url,
                'last_url': _url,
            }

        def _get_url(page):
            return self.form.urlencoded(page=page)

        pages = OrderedDict((p, _get_url(p))
                            for p in range(max(current - 2, 1),
                                           min(current + 2, page_count) + 1))

        return {
            'number': current,
            'count': page_count,
            'list': pages.keys(),
            'urls': pages,

            'next_url': current < page_count and _get_url(current + 1) or None,
            'prev_url': current > 1 and _get_url(current - 1) or None,

            'first_url': _get_url(1),
            'last_url': _get_url(page_count),
        }
