from datetime import datetime
import pysolr
from django.conf import settings

def first(obj, default=None):
    if type(obj) is list and obj:
        return obj[0]
    return default

class ObjectNormalizer:
    def __init__(self, solr):
        self.type = solr["type"]
        self.solr = solr

    def title(self, field):
        return max(self.solr[field], key=lambda i: len(i))

    def __str__(self):
        return str(self.solr)

    def jurisdiction(self):
        return "International"

class Treaty(ObjectNormalizer):
    def title(self):
        return super(Treaty, self).title("trTitleOfText")

    def date(self):
        return datetime.strptime(self.solr["trDateOfText"],
                                 "%Y-%m-%dT%H:%M:%SZ").date()

    def jurisdiction(self):
        return first(self.solr["trJustices"])

    def url(self):
        return first(self.solr["trUrlTreatyText"])

class Decision(ObjectNormalizer):
    def title(self):
        return super(Decision, self).title("decTitleOfText")

    def date(self):
        if not self.solr["decPublishDate"]:
            return None
        return datetime.strptime(self.solr["decPublishDate"][0],
                                 "%Y-%m-%dT%H:%M:%SZ").date()
    def url(self):
        return first(self.solr["decLink"])

    def status(self):
        return first(self.solr["decStatus"], "unknown")

    def number(self):
        return first(self.solr["decNumber"])

def search(user_query):
    solr = pysolr.Solr(settings.SOLR_URI, timeout=10)
    solr.optimize()
    solr_query = 'text:' + user_query
    params = {
        'facet': 'on',
        'facet.field': ['type'],
        'rows': '100'
    }
    responses = solr.search(solr_query, **params)

    results = []
    for hit in responses:
        if hit["type"] == "treaty":
            results.append(Treaty(hit))
        else:
            results.append(Decision(hit))

    facets = responses.facets['facet_fields']
    for k, v in facets.items():
        facets[k] = dict(zip(v[0::2], v[1::2]))

    return {
        'results': results,
        'query': user_query,
        'facets': facets,
    }
