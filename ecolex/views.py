from datetime import datetime
import pysolr
from django.http import HttpResponse
from django.shortcuts import render
from django.views.generic import TemplateView
from ecolex.search import search, get_document
from ecolex.forms import SearchForm


class SearchView(TemplateView):
    template_name = 'search.html'

    def get_context_data(self, **kwargs):
        ctx = super(SearchView, self).get_context_data(**kwargs)
        data = dict(self.request.GET)
        if 'q' in data:
            data['q'] = data['q'][0]
        data.setdefault('type', ('t', 'd'))
        ctx['form'] = self.form = SearchForm(data=data)
        return ctx


class SearchViewWithResults(SearchView):
    template_name = 'list_results.html'

    def get(self, request, **kwargs):
        ctx = self.get_context_data(**kwargs)
        query = self.form.data['q'].strip() or '*'
        context = search(query)
        ctx.update(context)
        return render(request, 'list_results.html', ctx)


def page(request, slug):
    return HttpResponse("slug=" + slug)


class ResultDetails(TemplateView):
    template_name = 'details.html'

    def get_context_data(self, **kwargs):
        context = super(ResultDetails, self).get_context_data(**kwargs)
        context['document'] = get_document(kwargs['id'])
        return context
