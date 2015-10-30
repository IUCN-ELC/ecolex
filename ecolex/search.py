import os
from collections import OrderedDict
import json
import pysolr
from django.conf import settings

from ecolex.solr_models import Treaty, Decision, Literature


HIGHLIGHT_FIELDS = []
HIGHLIGHT_PARAMS = {
    'hl': 'true',
    'hl.simple.pre': '<em class="hl">',
    'hl.fragsize': '0',
}
PERPAGE = 20


class Queryset(object):
    def __init__(self, query=None, filters=None, **kwargs):
        self.query = query
        self.filters = filters
        self.start = 0
        self.rows = kwargs.get('rows') or PERPAGE
        self.maxscore = None
        self._result_cache = None
        self._hits = None
        self._debug_response = None
        self._suggested_text = None
        self._facets = {}
        self._stats = {}
        self._query_kwargs = kwargs

    def set_page(self, page, perpage=None):
        self.rows = perpage or PERPAGE
        self.start = (page - 1) * self.rows

    def fetch(self):
        responses = _search(self.query, filters=self.filters,
                            start=self.start, **self._query_kwargs)
        return self._fetch(responses)

    def _fetch(self, responses):
        if responses.facets:
            self._facets = parse_facets(responses.facets['facet_fields'])
        self._result_cache = [
            parse_result(hit, responses) for hit in responses
        ]
        self._hits = responses.hits
        self._stats = responses.stats
        self.maxscore = (
            responses.maxscore if hasattr(responses, 'maxscore') else None
        )
        self._suggested_text = parse_suggestions(responses.spellcheck)
        self._debug_response = responses
        return self._result_cache

    def get_facets(self):
        if not self._facets:
            self.fetch()

        def _prepare(v):
            # data = [(k.capitalize(), v) for k, v in v.items()]
            data = [(k, v) for k, v in v.items()]
            return OrderedDict(
                sorted(data, key=lambda v: v[0].lower())
            )

        return {
            k: _prepare(v)
            for k, v in self._facets.items()
        }

    def get_field_stats(self):
        if not self._stats:
            self.fetch()
        return self._stats.get('stats_fields')

    def get_referred_treaties(self, id_name, ids_list):
        if not any(ids_list):
            return {}
        return get_documents_by_field(id_name, ids_list)

    def get_facet_treaty_names(self):
        """ Returns map of names for treaties returned by the decTreaty facet.
        """
        facets = self.get_facets()
        if not facets.get('decTreatyId'):
            return []
        return get_documents_by_field('trInformeaId',
                                      facets['decTreatyId'].keys())

    def get_suggested_text(self):
        return self._suggested_text

    def count(self):
        if not self._hits:
            self.fetch()
        return self._hits

    def pages(self):
        number_of_pages = (len(self) // self.rows) + 1
        return number_of_pages

    def first(self):
        if not self._hits:
            self.fetch()
        return self._result_cache[0]

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
    elif hit['type'] == 'literature':
        return Literature(hit, hl)
    return hit


def parse_facets(facets):
    return {k: dict(zip(v[0::2], v[1::2])) for k, v in facets.items()}


def parse_suggestions(solr_suggestions):
    if not solr_suggestions or not any(solr_suggestions['suggestions']):
        return ''

    return solr_suggestions['suggestions'][-1]


def escape_query(query):
    """ Code from: http://opensourceconnections.com/blog/2013/01/17/escaping-solr-query-characters-in-python/
    """
    escapeRules = {
        '+': r'\+', '-': r'\-', '&': r'\&', '|': r'\|', '!': r'\!', '(': r'\(',
        ')': r'\)', '{': r'\{', '}': r'\}', '[': r'\[', ']': r'\]', '^': r'\^',
        '~': r'\~', '*': r'\*', '?': r'\?', ':': r'\:', '"': r'\"', ';': r'\;',
    }

    def _esc(term):
        for char in query:
            if char in escapeRules.keys():
                yield escapeRules[char]
            else:
                yield char

    query = query.replace('\\', r'\\')
    return "".join(c for c in _esc(query))


def get_hl():
    fields = HIGHLIGHT_FIELDS
    for t in Decision, Treaty, Literature:
        fields += [t.SUMMARY_FIELD] + t.TITLE_FIELDS
    fields = set(fields)
    HIGHLIGHT_PARAMS['hl.fl'] = ','.join(fields)
    return HIGHLIGHT_PARAMS


def get_sortby(sortby):
    if sortby == 'last':
        return 'docDate desc'
    elif sortby == 'first':
        return 'docDate asc'
    elif sortby == '':
        return ''
    return settings.SOLR_SORTING


def get_relevancy():
    RELEVANCY_FIELDS = {
        'trPaperTitleOfText': 100,
        'decLongTitle_en': 100,
        'decLongTitle_es': 100,
        'decLongTitle_fr': 100,
        'decLongTitle_ru': 100,
        'decLongTitle_ar': 100,
        'decLongTitle_zh': 100,
        'decShortTitle_en': 100,
        'decShortTitle_es': 100,
        'decShortTitle_fr': 100,
        'decShortTitle_ru': 100,
        'decShortTitle_ar': 100,
        'decShortTitle_zh': 100,

        'litLongTitle': 100,
        'litLongTitle_fr': 100,
        'litLongTitle_sp': 100,
        'litLongTitle_other': 100,

        'trTitleAbbreviation': 75,
        'decSummary': 50,
        'decBody': 50,
        'trAbstract': 50,
        'trKeyword': 30,
        'decKeyword': 30,
        'litKeyword': 30,
        'doc_content': 10,
    }

    def boost_pair_t(field, boost_factor):
        return field + "^" + str(boost_factor)

    params = {}
    params['defType'] = 'edismax'
    params['qf'] = ' '.join(
        boost_pair_t(field, boost_factor) for field, boost_factor in
        RELEVANCY_FIELDS.items())
    return params


def get_fq(filters):
    FACETS_MAP = {
        'trTypeOfText': 'treaty',
        'trFieldOfApplication': 'treaty',
        'partyCountry': 'treaty',
        'trRegion': 'treaty',
        'trBasin': 'treaty',
        'trSubject': 'treaty',
        'trLanguageOfDocument': 'treaty',
        'decType': 'decision',
        'decStatus': 'decision',
        'decTreatyId': 'decision',
        'litTypeOfText': 'literature',
        'litAuthor': 'literature',
        'litCountry': 'literature',
        'lit_region': 'literature',
        'lit_basin': 'literature',
        'lit_serial': 'literature',
        'lit_publisher': 'literature',
        'lit_subject': 'literature',
        'lit_language': 'literature',
    }

    AND_FILTERS = [
        'docKeyword',
    ]

    def multi_filter(filter, values):
        if filter == 'docDate':
            start, end = values
            start = start + '-01-01T00:00:00Z' if start else '*'
            end = end + '-12-31T23:59:00Z' if end else '*'
            return filter + ':[' + start + ' TO ' + end + ']'
        values = ('"' + v + '"' for v in values)
        operator = ' AND ' if filter in AND_FILTERS else ' OR '
        return filter + ':(' + operator.join(t for t in values) + ')'

    def type_filter(type, filters):
        if filters:
            return 'type:' + type + ' AND (' + ' AND '.join(filters) + ')'
        else:
            return 'type:' + type

    enabled_types = filters.get('type', []) or ['treaty', 'decision', 'literature']
    type_filters = {f: [] for f in enabled_types}
    global_filters = []
    for filter, values in filters.items():
        values = [v for v in values if v or filter == 'docDate']
        if not values or filter == 'type' or not any(values):
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


def search(user_query, filters=None, sortby=None, raw=None,
           **kwargs):
    return Queryset(user_query, filters=filters, sortby=sortby, raw=raw,
                    **kwargs)


def _search(user_query, filters=None, highlight=True, start=0, rows=PERPAGE,
            sortby=None, raw=None, facets=None, fields=None):
    solr = pysolr.Solr(settings.SOLR_URI, timeout=10)
    if user_query == '*':
        solr_query = '*:*'
        highlight = False
    else:
        solr_query = user_query if raw else escape_query(user_query)
    filters = filters or {}
    params = {
        'rows': rows,
        'start': start,
        'stats': 'true',
        'stats.field': 'docDate',
    }
    params.update({
        'facet': 'on',
        'facet.field': facets or filters.keys(),
        'facet.limit': '-1',
        'facet.method': 'enum',
    })
    params['fq'] = get_fq(filters)
    if highlight:
        params.update(get_hl())
    params['sort'] = get_sortby(sortby)
    params.update(get_relevancy())
    # add spellcheck
    params.update({
        'spellcheck': 'true',
        'spellcheck.collate': 'true',
    })
    if fields:
        params['fl'] = ','.join(f for f in fields)

    if settings.DEBUG:
        params['debug'] = True
    return solr.search(solr_query, **params)


def get_documents_by_field(id_name, treaty_ids, rows=None):
    solr_query = id_name + ":(" + " ".join(treaty_ids) + ")"
    rows = len(treaty_ids) if rows is None else rows
    result = search(solr_query, rows=rows, raw=True)
    if not len(result):
        return None
    return result


def get_document(document_id):
    result = search('id:' + document_id, raw=True,
                    filters={'decTreatyId': ''})
    if not len(result):
        return None
    return result


def get_treaty_by_informea_id(informea_id):
    result = search('trInformeaId:' + informea_id, raw=True)
    if not len(result):
        return None
    return result.first()


def load_treaties_cache():
    if not os.path.exists(settings.TREATIES_JSON):
        print("Missing {}. Please run ./manage.py treaties_cache".format(
            settings.TREATIES_JSON)
        )
        return None
    try:
        data = json.load(open(settings.TREATIES_JSON, encoding='utf-8'))
    except:
        data = json.load(open(settings.TREATIES_JSON))
    response = data['response']
    result_kwargs = {}
    numFound = response.get('numFound', 0)
    results = pysolr.Results(response.get('docs', ()), numFound,
                             **result_kwargs)
    qs = Queryset()
    qs._fetch(results)
    return qs


_treaties = None


def get_all_treaties():
    global _treaties
    if _treaties is None:
        _treaties = load_treaties_cache()
    return _treaties
