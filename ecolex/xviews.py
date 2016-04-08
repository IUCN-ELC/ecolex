from django.views.generic import TemplateView
from django.http import QueryDict
from django.utils.translation import get_language
from .xsearch import Search, SearchViewMixin


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
                }#if k in form.changed_data}

        search = Search(data, language=get_language())
        response = search.execute()

        print(response.result.numFound)

        #results.set_page(page)

        ctx['results'] = response.result.docs
        ctx['form'] = self.form

        return ctx
