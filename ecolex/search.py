from datetime import datetime
import pysolr
from django.conf import settings


HIGHLIGHT_FIELDS = ('trTitleOfText', 'decTitleOfText')
HIGHLIGHT = ','.join(HIGHLIGHT_FIELDS)


def first(obj, default=None):
    if obj and type(obj) is list:
        return obj[0]
    return default


class ObjectNormalizer:
    def __init__(self, solr, hl):
        self.type = solr['type']
        self.solr = solr
        self.solr.update(hl)

    def id(self):
        return self.solr.get('id')

    def title(self):
        return max(self.solr[self.TITLE_FIELD], key=lambda i: len(i))

    def __str__(self):
        return str(self.solr)

    def jurisdiction(self):
        return "International"


class Treaty(ObjectNormalizer):
    TITLE_FIELD = 'trTitleOfText'

    def date(self):
        return datetime.strptime(self.solr['trDateOfText'],
                                 '%Y-%m-%dT%H:%M:%SZ').date()

    def jurisdiction(self):
        return first(self.solr.get('trJustices'))

    def url(self):
        return first(self.solr.get('trUrlTreatyText'))


class Decision(ObjectNormalizer):
    TITLE_FIELD = 'decTitleOfText'

    def date(self):
        if not self.solr['decPublishDate']:
            return None
        return datetime.strptime(self.solr['decPublishDate'][0],
                                 '%Y-%m-%dT%H:%M:%SZ').date()

    def url(self):
        return first(self.solr.get('decLink'))

    def status(self):
        return first(self.solr.get('decStatus'), "unknown")

    def number(self):
        return first(self.solr.get('decNumber'))


def parse_result(hit, responses):
    hl = responses.highlighting.get(hit['id'])
    if hit['type'] == 'treaty':
        return Treaty(hit, hl)
    elif hit['type'] == 'decision':
        return Decision(hit, hl)
    return hit


def search(user_query, types=None, highlight=True):
    solr = pysolr.Solr(settings.SOLR_URI, timeout=10)
    solr.optimize()
    solr_query = 'text:' + user_query
    params = {
        'facet': 'on',
        'facet.field': ['type'],
        'rows': '100',
    }
    if highlight:
        params.update({
            'hl': 'true',
            'hl.fl': HIGHLIGHT,
            'hl.simple.pre': '<em class="hl">',
        })
    fq = []
    if types:
        fq.append(' '.join('type:' + t for t in types))
    responses = solr.search(solr_query, fq=fq, **params)
    hits = responses.hits

    results = [parse_result(hit, responses) for hit in responses]
    print(responses.highlighting)

    facets = responses.facets['facet_fields']
    for k, v in facets.items():
        facets[k] = dict(zip(v[0::2], v[1::2]))

    return {
        'results': results,
        'query': user_query,
        'facets': facets,
        'hits': hits,
    }


def get_document(document_id):
    solr = pysolr.Solr(settings.SOLR_URI, timeout=10)
    solr_query = 'id:' + document_id
    responses = solr.search(solr_query)
    if not responses.hits:
        return None
    hit = list(responses)[0]
    return parse_result(hit)
