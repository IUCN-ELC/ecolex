import pysolr
from collections import OrderedDict
from django.conf import settings

from ecolex.lib.utils import camel_case_to__
from ecolex import definitions as defs
from ecolex.solr_models import (
    Treaty, Decision, Literature, CourtDecision, Legislation
)
from ecolex.schema import (
    CourtDecisionSchema, DecisionSchema, LegislationSchema, LiteratureSchema,
    TreatySchema,
)
from ecolex.forms import SearchForm


HIGHLIGHT_FIELDS = []
HIGHLIGHT_PARAMS = {
    'hl': 'true',
    'hl.simple.pre': '<em class="hl">',
    'hl.fragsize': '0',
}
PERPAGE = 20
ESCAPE_RULES = {
    '+': r'\+', '-': r'\-', '&': r'\&', '|': r'\|', '!': r'\!', '(': r'\(',
    ')': r'\)', '{': r'\{', '}': r'\}', '[': r'\[', ']': r'\]', '^': r'\^',
    '~': r'\~', '*': r'\*', '?': r'\?', ':': r'\:', ';': r'\;',
}


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

        # no-op
        def _prepare(val):
            return val

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

    def get_suggested_text(self):
        return self._suggested_text

    def count(self):
        if not self._hits:
            self.fetch()
        return self._hits

    def pages(self):
        number_of_pages = (len(self) // self.rows)
        if len(self) % self.rows != 0:
            number_of_pages += 1
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
    # hl = responses.highlighting.get(hit['id'])

    TYPE_TO_SCHEMA = {
        'treaty': TreatySchema,
        'decision': DecisionSchema,
        'literature': LiteratureSchema,
        'court_decision': CourtDecisionSchema,
        'legislation': LegislationSchema,
    }
    doctype = hit['type']
    schema = TYPE_TO_SCHEMA[doctype]()
    schema.context = {'language': 'en'}
    result, errors = schema.load(hit)
    return result


def parse_facets(facets):
    return {k: OrderedDict(zip(v[0::2], v[1::2])) for k, v in facets.items()}


def parse_suggestions(solr_suggestions):
    if not solr_suggestions or not any(solr_suggestions['suggestions']):
        return ''
    if 'collations' in solr_suggestions:
        return unescape_string(solr_suggestions['collations'][-1])
    if 'collation' in solr_suggestions['suggestions']:
        return unescape_string(solr_suggestions['suggestions'][-1])
    return ''


def escape_query(query):
    """ Code from: http://opensourceconnections.com/blog/2013/01/17/escaping-solr-query-characters-in-python/
    """

    def _esc(term):
        for char in query:
            if char in ESCAPE_RULES.keys():
                yield ESCAPE_RULES[char]
            else:
                yield char

    query = query.replace('\\', r'\\')
    return "".join(c for c in _esc(query))


def unescape_string(string):
    for char, escaped_char in ESCAPE_RULES.items():
        string = string.replace(escaped_char, char)
    return string


def get_hl(hl_details=False):
    fields = HIGHLIGHT_FIELDS
    for t in Decision, Treaty, Literature, CourtDecision, Legislation:
        fields += t.get_highlight_fields(hl_details=hl_details)
    fields = set(fields)
    HIGHLIGHT_PARAMS['hl.fl'] = ','.join(fields)
    return HIGHLIGHT_PARAMS


def get_sortby(sortby, has_search_term):
    if sortby == 'first':
        return 'docDate asc'
    elif sortby == 'last' or not has_search_term:
        return 'docDate desc'
    elif sortby == '':
        return ''
    return settings.SOLR_SORTING


def get_relevancy():
    def boost_pair_t(field, boost_factor):
        return field + "^" + str(boost_factor)

    params = {}
    params['defType'] = 'edismax'
    params['qf'] = ' '.join(
        boost_pair_t(field, boost_factor) for field, boost_factor in
        defs.RELEVANCY_FIELDS.items())

    return params


def get_fq(filters):
    # TODO: meh.
    FACETS_MAP = {
        'trTypeOfText_en': 'treaty',
        'trFieldOfApplication_en': 'treaty',
        'trStatus': 'treaty',
        'trPlaceOfAdoption': 'treaty',
        'trDepository_en': 'treaty',

        'decType': 'decision',
        'decStatus': 'decision',
        'decTreatyName_en': 'decision',

        'litTypeOfText_en': 'literature',
        'litAuthor': 'literature',
        'litSerialTitle': 'literature',
        'litPublisher': 'literature',

        'cdTypeOfText': 'court_decision',
        'cdTerritorialSubdivision_en': 'court_decision',
    }

    OR_FILTERS = [defs.FIELD_TO_FACET_MAPPING[f]
                  for f in defs._OR_OP_FACETS]

    AND_FILTERS = [defs.FIELD_TO_FACET_MAPPING[f]
                   for f in defs._AND_OP_FACETS]

    def multi_filter(filter, values):
        if filter == 'docDate':
            start, end = values
            start = start + '-01-01T00:00:00Z' if start else '*'
            end = end + '-12-31T23:59:59Z' if end else '*'
            return filter + ':[' + start + ' TO ' + end + ']'

        values = map(lambda v: '"%s"' % v, values)
        operator = (' AND ' if filter in AND_FILTERS
                    else ' OR ')

        # WARNING:
        # querying for "({!tag=xx}field:(yy))" throws parse error
        # TODO: is this a solr bug?
        #       might WhitespaceTokenizerFactory help?

        return "{filter}:({value})".format(filter=filter,
                                           value=escape_query(operator.join(values)))

    def type_filter(type, filters):
        if filters:
            return 'type:' + type + ' AND (' + ' AND '.join(filters) + ')'
        else:
            return 'type:' + type

    enabled_types = filters.get('type', []) or \
        ['treaty', 'decision', 'literature', 'court_decision', 'legislation']

    type_filters = {f: [] for f in enabled_types}
    global_filters = []

    for filter, values in filters.items():
        _filter = filter
        if filter.startswith('{!ex='):
            filter = '{!tag=' + filter[5:]
            _filter = filter[filter.index('}') + 1:]

        values = [v for v in values if v or _filter == 'docDate']

        if not values or _filter == 'type' or not any(values):
            continue

        # NOTE:
        # skipping on purpose to cause previous behaviour, i.e.
        # type-specific filters will cause only that type to be displayed.
        # see warning under multi_filter for explanation.
        # TODO: fix this, the behaviour differs from AND to OR.
        _skip_me = (_filter != filter)
        if _filter in FACETS_MAP and not _skip_me:
            if FACETS_MAP[_filter] in enabled_types:
                type_filters[FACETS_MAP[_filter]].append(
                    multi_filter(filter, values)
                )
        else:
            global_filters.append(multi_filter(filter, values))

    global_filters.append(' OR '.join(
        '(%s)' % type_filter(t, v)
        for t, v in type_filters.items()
    ))
    return global_filters


def search(user_query, filters=None, sortby=None, raw=None,
           **kwargs):
    return Queryset(user_query, filters=filters, sortby=sortby, raw=raw,
                    **kwargs)


def _search(user_query, filters=None, highlight=True, start=0, rows=PERPAGE,
            sortby=None, raw=None, facets=None, fields=None, hl_details=False,
            facets_page_size=None, only_facet=None):
    if facets_page_size is None:
        facets_page_size = settings.FACETS_PAGE_SIZE

    solr = pysolr.Solr(settings.SOLR_URI, timeout=60)

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

    if filters:
        params['fq'] = get_fq(filters)

    # include relevancy data early, because it alters facet results
    # TODO: why is that?
    params.update(get_relevancy())

    params.update({
        'facet': 'true',
        'facet.limit': facets_page_size,
        # it is always desirable to sort by index
        'facet.sort': 'index',
        # TODO: should this really be enum for authors?
        'facet.method': 'enum',
        # TODO: mincount should be 0 when facet_filter.op = OR
        # check show_empty parameter in SelectFacetsAjax
        'facet.mincount': 1,
    })

    # TODO: pass facet logic through the same code as api,
    # and sort it in proper alphabetical order in python
    # (also, cache it)
    if only_facet:
        fname = only_facet['field']
        # make sure we don't overwrite a field marked for exclusion
        # TODO: this smells. should be unified with filter logic.
        excl_fname = SearchMixin._get_excluded(fname)
        if excl_fname in filters:
            fname = excl_fname
        params.update({
            'facet.field': fname,
            'rows': 0,
            'facet.limit': only_facet.get('limit', facets_page_size),
            'facet.offset': only_facet.get('offset', 0),
            'facet.prefix': only_facet.get('prefix', '')
        })

        return solr.search(solr_query, **params)

    else:
        params['facet.field'] = facets or filters.keys()

    """
    if highlight:
        params.update(get_hl(hl_details=hl_details))
    """
    params['sort'] = get_sortby(sortby, highlight)

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


def get_documents_by_field(id_name, treaty_ids, rows=None, sortby=None):
    solr_query = id_name + ":(" + " ".join(treaty_ids) + ")"
    rows = len(treaty_ids) if rows is None else rows
    result = search(solr_query, rows=rows, sortby=sortby, raw=True)
    if not len(result):
        return []
    return result


def get_document(document_id, query='*', **kwargs):
    result = search(query, raw=True, filters={'id': [document_id]}, **kwargs)
    if not len(result):
        result = search('*', raw=True, filters={'id': [document_id]}, **kwargs)
    return result


def get_treaty_by_informea_id(informea_id):
    result = search('trInformeaId:' + informea_id, raw=True)
    if not len(result):
        return None
    return result.first()


def get_all_treaties():
    result = search('type:treaty', raw=True, rows=10000)
    return result


class SearchMixin(object):
    """
    Useful as a mixin for objects that perform search, e.g. views.
    """

    def _set_form_defaults(self, data):
        """
        This alters `data` in place with... some... defaults.
        """
        # TODO: why is this necessary?

        exclude_fields = ['q', 'sortby', 'yearmin', 'yearmax']
        fields = [x for x in SearchForm.base_fields if x not in exclude_fields]
        for field in fields:
            data.setdefault(field, [])
        if 'q' in data:
            data['q'] = data['q'][0]

        data.setdefault('sortby', [''])
        for y in ('yearmin', 'yearmax', 'sortby'):
            data[y] = data[y][0] if y in data else None

        return data

    def _get_filters(self, data):
        filters = {
            'type': data['type'] or dict(defs.DOC_TYPE).keys(),
            'docKeyword_en': data['xkeywords'],
            'docSubject_en': data['xsubjects'],
            'docCountry_en': data['xcountry'],
            'docRegion_en': data['xregion'],
            'docLanguage_en': data['xlanguage'],
            'docDate': (data['yearmin'], data['yearmax']),
        }
        for doc_type in filters['type']:
            mapping = defs.DOC_TYPE_FILTER_MAPPING[doc_type]
            for k, v in mapping.items():
                filters[k] = data[v]

        # add exclusion local param for OR-able fields
        for field in defs._OR_OP_FACETS:
            # but skip AND-able fields if we got an AND request
            if (field in defs._AND_OP_FACETS and
                data.get(
                    SearchForm.get_and_field_name_for(field)
                )
            ):
                continue

            solr_field = defs.FIELD_TO_FACET_MAPPING[field]
            try:
                filter = filters.pop(solr_field)
            except KeyError:
                pass
            else:
                filters[self._get_excluded(solr_field)] = filter

        return filters

    @classmethod
    def _get_excluded(cls, facet_name):
        """
        returns the field name, marked for solr exclusion
        """
        return '{!ex=%s}%s' % (
            camel_case_to__(facet_name), facet_name)

    def _prepare(self, data):
        """
        This has the side effects of setting object attributes.
        Must be called before search.
        """
        # TODO: this. is. so. ugly. Must... refactor...

        data = dict(data)
        self._set_form_defaults(data)
        self.form = SearchForm(data=data)

        # TODO: seriously, don't fetch the entire database on missing query
        self.query = self.form.data.get('q', '').strip() or '*'
        self.filters = self._get_filters(data)
        self.sortby = data['sortby']

    def search(self, **kwargs):
        query = kwargs.pop('query', self.query)

        kwargs.setdefault('filters', self.filters)
        kwargs.setdefault('sortby', self.sortby)
        kwargs.setdefault('fields', defs.SOLR_FIELDS)

        return search(query, **kwargs)
