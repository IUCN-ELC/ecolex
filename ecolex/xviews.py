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

    def get_query_data(self):
        # momentarily return a mish-mash of form's cleaned_data and data,
        # until form validation can be fully trusted
        self.form.is_valid()
        data = self.form.cleaned_data.copy()
        rem_keys = []
        # clean all empty things
        for k, v in data.items():
            if v in (None, []):
                rem_keys.append(k)
        for rk in rem_keys:
            del data[rk]

        data.update({
            k: v
            for k, v in self.form.data.lists()
            if k not in data
        })

        return data


class SearchResultsView(SearchViewMixin, TemplateView):
    template_name = 'list_results.html'

    def get(self, request, *args, **kwargs):
        if not self.form.changed_data:
            return homepage_view(request, *args, **kwargs)

        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        form = self.form
        # TODO: when not valid?
        #form.is_valid()

        if any(f in form.errors
               for f in (
                'page', 'sortby'
               )):
            response = SearchResponse()
            page = 1
        else:
            data = self.get_query_data()

            page = data.pop('page')
            sortby = data.pop('sortby')
            date_sort = {
                form.SORT_DEFAULT: None,
                form.SORT_FIRST: True,
                form.SORT_LAST: False,
            }[sortby]

            searcher = Searcher(data, language=get_language())
            response = searcher.search(page=page, date_sort=date_sort)

        ctx['form'] = self.form
        ctx['results'] = response
        ctx['facets'] = response.facets
        ctx['stats'] = response.stats
        # TODO: rename ctx to 'pages'
        ctx['page'] = self.get_page_details(page, response.count)

        return ctx

    def get_page_details(self, current, result_count, page_size=None):
        if page_size is None:
            page_size = settings.SEARCH_PAGE_SIZE

        _get_query = self.request.GET.copy()
        _get_query.pop('page', None)

        page_count = math.ceil(result_count / page_size)

        if page_count <= 1:
            _url = _get_query.urlencode()
            return {
                'number': 1,
                'no_pages': 1,
                'pages_list': [1],
                'pages_urls': {1: _url},
                'next_url': None,
                'prev_url': None,
                'first_url': _url,
                'last_url': _url,
            }

        def _get_url(page):
            if page != 1:
                _get_query['page'] = page
            else:
                _get_query.pop('page', None)
            return _get_query.urlencode()

        pages = OrderedDict((p, _get_url(p))
                            for p in range(max(current - 2, 1),
                                           min(current + 2, page_count) + 1))

        return {
            'number': current,
            'no_pages': page_count,
            'pages_list': pages.keys(),
            'pages_urls': pages,

            'next_url': current < page_count and _get_url(current + 1) or None,
            'prev_url': current > 1 and _get_url(current - 1) or None,

            'first_url': _get_url(1),
            'last_url': _get_url(page_count),
        }
