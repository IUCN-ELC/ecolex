from datetime import datetime
from collections import OrderedDict
import pysolr
from django.conf import settings


HIGHLIGHT_FIELDS = (
    'trTitleOfText', 'decTitleOfText', 'decBody', 'trIntroText')
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
    return obj if obj else default


class ObjectNormalizer:
    def __init__(self, solr, hl):
        self.type = solr['type']
        self.solr = solr
        if hl:
            self.solr.update(hl)

    def id(self):
        return self.solr.get('id')

    def title(self):
        for title_field in self.TITLE_FIELDS:
            if not self.solr.get(title_field):
                continue
            t = max(self.solr.get(title_field), key=lambda i: len(i))
            if len(t):
                return t
        return "Unknown Document"

    def date(self):
        for date_field in self.DATE_FIELDS:
            try:
                return datetime.strptime(first(self.solr.get(date_field)),
                                         '%Y-%m-%dT%H:%M:%SZ').date()
            except:
                continue
        return ""


    def __str__(self):
        return str(self.solr)

    def jurisdiction(self):
        return "International"


class Treaty(ObjectNormalizer):
    TITLE_FIELDS = ['trPaperTitleOfText', 'trPaperTitleOfTextFr',
                    'trPaperTitleOfTextSp', 'trPaperTitleOfTextOther',
                    'trTitleOfTextShort']
    DATE_FIELDS = ['trDateOfText', 'trDateOfEntry', 'trDateOfModification']

    def jurisdiction(self):
        return first(self.solr.get('trJurisdiction'))

    def url(self):
        return first(self.solr.get('trUrlTreatyText'))

    def summary(self):
        return first(self.solr.get('trIntroText'), "")

    def participants(self):
        PARTY_MAP = {
            'partyCountry': 'country',
            # 'partyPotentialParty': 'partyPotentialParty',
            # 'partyEntryIntoForce': 'partyEntryIntoForce',
            'partyDateOfRatification': 'ratification',
            'partyDateOfAccessionApprobation': 'accessionapprobation',
            'partyDateOfAcceptanceApproval': 'acceptanceapproval',
            'partyDateOfConsentToBeBound': 'consenttobebound',
            'partyDateOfSuccession': 'succession',
            'partyDateOfDefiniteSignature': 'definitesignature',
            'partyDateOfSimpleSignature': 'simplesignature',
            'partyDateOfProvisionalApplication': 'provisionalapplication',
            'partyDateOfParticipation': 'participation',
            'partyDateOfDeclaration': 'declaration',
            'partyDateOfReservation': 'reservation',
            'partyDateOfWithdrawal': 'withdrawal',
        }
        clean = lambda d: d if d != '0002-11-30T00:00:00Z' else '-'
        data = {}
        for k, v in PARTY_MAP.items():
            data[v] = self.solr.get(k, [])
        results = []
        for i, country in enumerate(data['country']):
            results.append(
                {v: clean(data[v][i]) for v in PARTY_MAP.values()}
            )
        return results


class Decision(ObjectNormalizer):
    TITLE_FIELDS = ['decTitleOfText']
    DATE_FIELDS = ['decPublishDate', 'decUpdateDate']

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
        return {
            k: OrderedDict(sorted(tuple(v.items()), key=lambda v: v[0]))
            for k, v in self._facets.items()
        }

    def get_treaty_names(self):
        """ Returns map of names for treaties returned by the decTreaty facet.
        """
        facets = self.get_facets()
        if not facets.get('decTreatyId'):
            return {}

        results = get_treaties_by_id(facets['decTreatyId'].keys())
        return dict(
            (r.solr.get("trInformeaId", -1), r.title()) for r in results)

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
    return 'type', 'trTypeOfText', 'decType'


def get_fq(filters):
    FACETS_MAP = {
        'trTypeOfText': 'treaty',
        'trFieldOfApplication': 'treaty',
        'partyCountry': 'treaty',
        'trSubject': 'treaty',
        'decType': 'decision',
        'decStatus': 'decision',
        'decTreatyId': 'decision',
    }

    def multi_filter(filter, values):
        return filter + ':(' + ' OR '.join(t for t in values) + ')'

    def type_filter(type, filters):
        if filters:
            return 'type:' + type + ' AND (' + ' AND '.join(filters) + ')'
        else:
            return 'type:' + type

    enabled_types = filters.get('type', []) or ['treaty', 'decision']
    type_filters = {f: [] for f in enabled_types}
    global_filters = []
    for filter, values in filters.items():
        if not values or filter is enabled_types:
            continue
        if filter in FACETS_MAP:
            if FACETS_MAP[filter] in enabled_types:
                type_filters[FACETS_MAP[filter]].append(
                    multi_filter(filter, values)
                )
        else:
            global_filters.append(multi_filter(filter, values))
    global_filters.append(' OR '.join(
        '(' + type_filter(t, v) + ')' for t, v in type_filters.items())
    )
    return global_filters


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
    params['fq'] = get_fq(filters)
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


def get_treaties_by_id(treaty_ids):
    solr = pysolr.Solr(settings.SOLR_URI, timeout=10)
    solr_query = "trInformeaId:(" + " ".join(treaty_ids) + ")"
    responses = solr.search(solr_query, rows=len(treaty_ids))
    if not responses.hits:
        return None
    return [parse_result(hit, responses) for hit in responses]


def get_document(document_id):
    solr = pysolr.Solr(settings.SOLR_URI, timeout=10)
    solr_query = 'id:' + document_id
    responses = solr.search(solr_query)
    if not responses.hits:
        return None
    hit = list(responses)[0]
    return parse_result(hit, responses)
