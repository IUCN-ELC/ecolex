from datetime import datetime
import pysolr
from django.conf import settings


HIGHLIGHT_FIELDS = ('trTitleOfText', 'decTitleOfText')
HIGHLIGHT = ','.join(HIGHLIGHT_FIELDS)
HIGHLIGHT_PARAMS = {
    'hl': 'true',
    'hl.fl': HIGHLIGHT,
    'hl.simple.pre': '<em class="hl">',
}
PERPAGE = 20


def first(obj, default=None):
    if obj and type(obj) is list:
        return obj[0]
    return default


class ObjectNormalizer:
    def __init__(self, solr, hl):
        self.type = solr['type']
        self.solr = solr
        if hl:
            self.solr.update(hl)

    def id(self):
        return self.solr.get('id')

    def title(self):
        if self.solr.get(self.TITLE_FIELD):
            return max(self.solr[self.TITLE_FIELD], key=lambda i: len(i))

    def __str__(self):
        return str(self.solr)

    def jurisdiction(self):
        return "International"


class Treaty(ObjectNormalizer):
    TITLE_FIELD = 'trTitleOfText'

    def date(self):
        if not self.solr.get('trDateOfText'):
            return ""
        return datetime.strptime(self.solr['trDateOfText'],
                                 '%Y-%m-%dT%H:%M:%SZ').date()

    def jurisdiction(self):
        return first(self.solr.get('trJustices'))

    def url(self):
        return first(self.solr.get('trUrlTreatyText'))

    def summary(self):
        return first(self.solr.get('trIntroText'))


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


class Queryset(object):
    def __init__(self, query=None, filters=None, highlight=None):
        self.query = query
        self.filters = filters
        self.highlight = highlight
        self.start = 0
        self.perpage = PERPAGE
        self._result_cache = None
        self._hits = None
        self._facets = {}

    def set_page(self, page, perpage=None):
        self.perpage = perpage or PERPAGE
        self.start = (page - 1) * self.perpage

    def fetch(self):
        result = _search(self.query, filters=self.filters,
                         highlight=self.highlight, start=self.start,
                         rows=self.perpage)
        self._result_cache = result['results']
        self._hits = result['hits']
        self._facets = result['facets']
        return self._result_cache

    def get_facets(self):
        if not self._facets:
            self.fetch()
        return self._facets

    def count(self):
        if not self._hits:
            self.fetch()
        return self._hits

    def pages(self):
        return self.perpage and int(len(self) / self.perpage)

    def __len__(self):
        return self.count()

    def __iter__(self):
        if not self._result_cache:
            self.fetch()
        return self._result_cache.__iter__()


def parse_result(hit, responses):
    hl = responses.highlighting.get(hit['id'])
    if hit['type'] == 'treaty':
        return Treaty(hit, hl)
    elif hit['type'] == 'decision':
        return Decision(hit, hl)
    return hit


def escape_query(query):
    """ Code from: http://opensourceconnections.com/blog/2013/01/17/escaping-solr-query-characters-in-python/
    """
    escapeRules = {
        '+': r'\+', '-': r'\-', '&': r'\&', '|': r'\|', '!': r'\!', '(': r'\(',
        ')': r'\)', '{': r'\{', '}': r'\}', '[': r'\[', ']': r'\]', '^': r'\^',
        '~': r'\~', '*': r'\*', '?': r'\?', ':': r'\:', '"': r'\"', ';': r'\;',
        ' ': r'\ ',
    }

    def _esc(term):
        for char in query:
            if char in escapeRules.keys():
                yield escapeRules[char]
            else:
                yield char

    query = query.replace('\\', r'\\')
    return "".join(c for c in _esc(query))


def get_default_filters():
    return 'type', 'trTypeOfText'


def search(user_query, filters=None, highlight=True):
    return Queryset(user_query, filters=filters, highlight=highlight)


def _search(user_query, filters=None, highlight=True, start=0, rows=PERPAGE):
    solr = pysolr.Solr(settings.SOLR_URI, timeout=10)
    solr.optimize()
    if user_query == '*':
        solr_query = 'text:*'
        highlight = False
    else:
        solr_query = 'text:' + escape_query(user_query)
    filters = filters or get_default_filters()
    params = {
        'rows': rows,
        'start': start,
    }
    params.update({
        'facet': 'on',
        'facet.field': filters.keys(),
    })
    params['fq'] = [
        ' '.join(facet + ':' + t for t in values)
        for facet, values in filters.items()
    ]
    if highlight:
        params.update(HIGHLIGHT_PARAMS)

    responses = solr.search(solr_query, **params)
    hits = responses.hits

    results = [parse_result(hit, responses) for hit in responses]

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
    return parse_result(hit, responses)
