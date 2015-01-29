from django import forms
from django.http import HttpResponse
from django.shortcuts import render

import pysolr, json

def search(request):
    return render(request, 'search.html')

def result(request):
    if 'q' in request.GET:
        solr = pysolr.Solr('http://10.0.0.98:8983/solr/ecolex', timeout=10)
        solr.optimize()
        responses = solr.search('text:' + request.GET['q'], rows=10000)
        
        results = []
        for hit in responses:
            results.append(json.dumps(hit))

        return render(request, 'list_results.html', {'results': results, 'query': request.GET['q']})
    else:
        message = "Please enter a search term"

    return HttpResponse(message)
