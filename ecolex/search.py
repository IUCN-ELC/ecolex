from datetime import datetime
import pysolr
from django.conf import settings


def search(user_query):
    solr = pysolr.Solr(settings.SOLR_URI, timeout=10)
    solr.optimize()
    solr_query = 'text:' + user_query
    params = {
        'facet': 'on',
        'facet.field': ['type'],
        'rows': '15'
    }
    responses = solr.search(solr_query, **params)

    results = []
    for hit in responses:
        #FIXME(catalinb): temporary
        if hit.get("decPublishDate"):
            if hit.get("decPublishDate"):
                parse_time = lambda d: datetime.strptime(d,
                                                         "%Y-%m-%dT%H:%M:%SZ")
                hit["decPublishDate"] = list(
                    map(parse_time, hit["decPublishDate"]))

            if hit.get("decBody"):
                parse_body = lambda body: body[:250] + "..."
                hit["decBody"] = list(map(parse_body, hit["decBody"]))
        results.append(hit)

    facets = responses.facets['facet_fields']
    for k, v in facets.items():
        facets[k] = dict(zip(v[0::2], v[1::2]))

    return {
        'results': results,
        'query': user_query,
        'facets': facets,
    }
