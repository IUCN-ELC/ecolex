from django import forms
from django.http import HttpResponse
from django.shortcuts import render
from django.views.generic import TemplateView
from datetime import datetime

import pysolr, json

class SearchView(TemplateView):
    template_name = "search.html"

class SearchViewWithResults(SearchView):
    template_name = "list_results.html"

    def get_context_data(self, **kwargs):
        ctx = super(SearchViewWithResults, self).get_context_data(**kwargs)
        return ctx

    def get(self, request, **kwargs):
        if 'q' in request.GET:
            solr = pysolr.Solr('http://10.0.0.98:8983/solr/ecolex', timeout=10)
            solr.optimize()

            user_query = request.GET['q']
            solr_query = 'trTitleOfText:' + user_query + ' decBody:' + user_query
            responses = solr.search(solr_query, rows=15)

        results = []
        for hit in responses:
            #FIXME(catalinb): temporary
            if hit.get("decPublishDate"):
                parse_time = lambda date: datetime.strptime(date, "%Y-%m-%dT%H:%M:%SZ")
                hit["decPublishDate"] = list(map(parse_time, hit["decPublishDate"]))
                parse_body = lambda body: body[:250] + "..."
                hit["decBody"] = list(map(parse_body, hit["decBody"]))
            results.append(hit)

        return render(request, 'list_results.html', {'results': results, 'query': request.GET['q']})

def page(request, slug):
    return HttpResponse("slug=" + slug)
