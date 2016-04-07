from django.views.generic import TemplateView
from django.http import QueryDict
from .xsearch import searcher, SearchViewMixin


class HomepageView(TemplateView):
    template_name = 'homepage.html'

homepage_view = HomepageView.as_view()


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
        form.is_valid()

        data = {k: v for k, v in form.data.lists()
                if k in form.changed_data}

        response = searcher.search(data, 'en')

        #results.set_page(page)

        ctx['results'] = response.result.docs
        ctx['form'] = self.form

        return ctx
