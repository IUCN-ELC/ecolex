from datetime import datetime
import pysolr
from django.http import HttpResponse
from django.shortcuts import render
from django.views.generic import TemplateView
from ecolex.search import search


class SearchView(TemplateView):
    template_name = "search.html"


class SearchViewWithResults(SearchView):
    template_name = "list_results.html"

    def get_context_data(self, **kwargs):
        ctx = super(SearchViewWithResults, self).get_context_data(**kwargs)
        return ctx

    def get(self, request, **kwargs):
        query = request.GET.get('q', '')
        query = query.strip()
        if query:
            context = search(query)
        else:
            context = search('*')

        return render(request, 'list_results.html', context)


def page(request, slug):
    return HttpResponse("slug=" + slug)
