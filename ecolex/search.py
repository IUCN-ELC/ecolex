from datetime import datetime
from collections import OrderedDict
import pysolr
from django.conf import settings


HIGHLIGHT_FIELDS = []
HIGHLIGHT_PARAMS = {
    'hl': 'true',
    'hl.simple.pre': '<em class="hl">',
    'hl.fragsize': '0',
}
PERPAGE = 20


class ObjectNormalizer:
    def __init__(self, solr, hl):
        self.type = solr['type']
        self.solr = solr
        if hl:
            self.solr.update(hl)

    def type_of_document(self):
        if self.solr.get('trTypeOfText'):
            return first(self.solr.get('trTypeOfText'))
        if self.solr.get('decType'):
            return first(self.solr.get('decType'))
        return "Unknown type of document"

    def id(self):
        return self.solr.get('id')

    def document_id(self):
        return first(self.solr.get(self.ID_FIELD))

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

    def jurisdiction(self):
        return first(self.solr.get('trJurisdiction', "International"))

    def summary(self):
        return first(self.solr.get(self.SUMMARY_FIELD), "")

    def optional_fields(self):
        res = []
        for field, label, type in self.OPTIONAL_INFO_FIELDS:
            if not self.solr.get(field):
                continue
            entry = {}
            entry['type'] = first(type, 'text')
            entry['label'] = label
            value = self.solr.get(field)

            if 'date' in type:
                try:
                    value = datetime.strptime(first(value),
                                              '%Y-%m-%dT%H:%M:%SZ').date()
                except:
                    pass
            entry['value'] = value
            res.append(entry)
        return res

    __repr__ = title


class Treaty(ObjectNormalizer):
    ID_FIELD = 'trElisId'
    SUMMARY_FIELD = 'trIntroText'
    TITLE_FIELDS = [
        'trPaperTitleOfText', 'trPaperTitleOfTextFr', 'trPaperTitleOfTextSp',
        'trPaperTitleOfTextOther', 'trTitleOfTextShort',
    ]
    DATE_FIELDS = ['trDateOfText', 'trDateOfEntry', 'trDateOfModification']
    OPTIONAL_INFO_FIELDS = [
        # (solr field, display text, type=text)
        ('trTitleAbbreviation', 'Title Abbreviation', ''),
        ('trEntryIntoForceDate', 'Entry into force', 'date'),
        ('trPlaceOfAdoption', 'Place of adoption', ''),
        ('trAvailableIn', 'Available in', ''),
        ('trRegion', 'Geographical area', ''),
        ('trDepository', 'Depository', ''),
        ('trUrl', 'Available web site', 'url'),
        ('trLinkToFullText', 'Link to full text', 'url'),
        #('trLinkToFullTextSp', 'Link to full text (spanish)', 'url'),
        #('trLinkToFullTextFr', 'Link to full text (french)', 'url'),
        #('trLinkToFullTextOther', 'Link to full text (other)', 'url'),
        ('trLanguageOfDocument', 'Language', 'keyword'),
        ('trLanguageOfTranslation', 'Translation', ''),
        ('trAbstract', 'Abstract', 'text'),
        # display comments the same way as texts
        ('trComment', 'Comment', 'text'),
        # keywords are considered safe.
        ('trSubject', 'Subject', 'keyword'),
        ('trKeyword', 'Keywords', 'keyword'),
        ('trNumberOfPages', 'Number of pages', ''),
        ('trOfficialPublication', 'Official publication', ''),
        ('trInternetReference', 'Internet Reference', ''),
        ('trDateOfEntry', 'Date of Entry', 'date'),
        ('trDateOfConsolidation', 'Consolidation Date', 'date')
    ]

    REFERENCE_FIELDS = {
        'trAmendsTreaty': 'Amends:',
        'trSupersedesTreaty': 'Supersedes:',
        'trCitesTreaty': 'Cites:',
        'trEnablesTreaty': 'Enables:',
        'trEnabledByTreaty': 'Enabled by:',
        'trAmendedBy': 'Amended by:',
        'trSupersededBy': 'Superseded by:',
        'trCitedBy': 'Cited by:',
    }

    def jurisdiction(self):
        return first(self.solr.get('trJurisdiction'))

    def field_of_application(self):
        return first(self.solr.get('trFieldOfApplication'))

    def url(self):
        return first(self.solr.get('trUrlTreatyText'))

    def participants(self):
        PARTY_MAP = OrderedDict((
            ('partyCountry', 'country'),
            ('partyPotentialParty', 'potential party'),
            ('partyEntryIntoForce', 'entry into force'),
            ('partyDateOfRatification', 'ratification'),
            ('partyDateOfAccessionApprobation', 'accession approbation'),
            ('partyDateOfAcceptanceApproval', 'acceptance approval'),
            ('partyDateOfConsentToBeBound', 'consent to be bound'),
            ('partyDateOfSuccession', 'succession'),
            ('partyDateOfDefiniteSignature', 'definite signature'),
            ('partyDateOfSimpleSignature', 'simple signature'),
            ('partyDateOfProvisionalApplication', 'provisional application'),
            ('partyDateOfDeclaration', 'declaration'),
            ('partyDateOfParticipation', 'participation'),
            ('partyDateOfReservation', 'reservation'),
            ('partyDateOfWithdrawal', 'withdrawal'),
        ))

        clean = lambda d: d if d != '0002-11-30T00:00:00Z' else None
        data = OrderedDict()
        for field, event in PARTY_MAP.items():
            values = [clean(v) for v in self.solr.get(field, [])]
            if values and any(values):
                data[event] = values
        results = []
        for i, country in enumerate(data['country']):
            results.append(
                OrderedDict((v, data[v][i]) for v in data.keys())
            )
        ret = {
            'countries': results,
            'events': [c for c in data.keys() if c != 'country'],
        }
        return ret

    def get_references_ids_set(self):
        ids = set()
        for field, label in self.REFERENCE_FIELDS.items():
            values = [v for v in self.solr.get(field, [])]
            if values and any(values):
                ids.update(values)

        return ids

    def references(self):
        data = {}
        for field, label in self.REFERENCE_FIELDS.items():
            values = [v for v in self.solr.get(field, [])]
            if values and any(values):
                data[label] = values
        return data

    def full_title(self):
        return '{} ({})'.format(self.title(), self.date())

    def informea_id(self):
        return first(self.solr.get('trInformeaId'))


class Decision(ObjectNormalizer):
    ID_FIELD = 'decNumber'
    SUMMARY_FIELD = 'decBody'
    TITLE_FIELDS = ['decTitleOfText']
    DATE_FIELDS = ['decPublishDate', 'decUpdateDate']
    OPTIONAL_INFO_FIELDS = [
        ('decMeetingTitle', 'Meeting Title', ''),
        ('decMeetingUrl', 'Meeting URL', 'url'),
        ('decLink', 'Link to decision', 'url'),
        ('decSummary', 'Summary', 'text'),
        ('decBody', 'Decision Body', 'text'),
        ('decDocUrls', 'Documents', 'url'),
        ('decKeyword', 'Keywords', 'keyword'),
        ('decUpdateDate', 'Date of Update', 'date'),
    ]

    def url(self):
        return first(self.solr.get('decLink'))

    def status(self):
        return first(self.solr.get('decStatus'), "unknown")


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
        return {
            k: OrderedDict(
                sorted(tuple(v.items()), key=lambda v: v[0].lower()))
            for k, v in self._facets.items()
        }

    def get_field_stats(self):
        if not self._stats:
            self.fetch()
        return self._stats.get('stats_fields')

    def get_referred_treaties(self, id_name, ids_list):
        if not any(ids_list):
            return {}
        return get_treaties_by_id(id_name, ids_list)

    def get_facet_treaty_names(self):
        """ Returns map of names for treaties returned by the decTreaty facet.
        """
        facets = self.get_facets()
        if not facets.get('decTreatyId'):
            return []
        return get_treaties_by_id('trInformeaId',
                                  facets['decTreatyId'].keys())

    def get_suggested_text(self):
        return self._suggested_text

    def count(self):
        if not self._hits:
            self.fetch()
        return self._hits

    def pages(self):
        return self.rows and int(len(self) / self.rows)

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


def first(obj, default=None):
    if obj and type(obj) is list:
        return obj[0]
    return obj if obj else default


def parse_result(hit, responses):
    hl = responses.highlighting.get(hit['id'])
    if hit['type'] == 'treaty':
        return Treaty(hit, hl)
    elif hit['type'] == 'decision':
        return Decision(hit, hl)
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
    for t in Decision, Treaty:
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
        'trPaperTitleOfTextSp': 100,
        'trPaperTitleOfTextFr': 100,
        'trPaperTitleOfTextOther': 100,
        'decLongTitle': 100,
        'decShortTitle': 100,
        'decSummary': 50,
        'decBody': 50,
        'trAbstract': 50,
        'trKeyword': 30,
        'decKeyword': 30,
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
        'trSubject': 'treaty',
        'decType': 'decision',
        'decStatus': 'decision',
        'decTreatyId': 'decision',
    }

    def multi_filter(filter, values):
        if filter == 'docDate':
            start, end = values
            start = start + '-01-01T00:00:00Z' if start else '*'
            end = end + '-12-31T23:59:00Z' if end else '*'
            return filter + ':[' + start + ' TO ' + end + ']'
        values = ('"' + v + '"' for v in values)
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
            sortby=None, raw=None, facets=None):
    solr = pysolr.Solr(settings.SOLR_URI, timeout=10)
    solr.optimize()
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
    })
    params['fq'] = get_fq(filters)
    if highlight:
        params.update(get_hl())
    params['sort'] = get_sortby(sortby)
    params.update(get_relevancy())
    #add spellcheck
    params.update({
        'spellcheck': 'true',
        'spellcheck.collate': 'true',
    })
    if settings.DEBUG:
        params['fl'] = '*,score'
        params['debug'] = True

    return solr.search(solr_query, **params)


def get_treaties_by_id(id_name, treaty_ids):
    solr_query = id_name + ":(" + " ".join(treaty_ids) + ")"
    result = search(solr_query, rows=len(treaty_ids), raw=True)
    if not len(result):
        return None
    return result


def get_document(document_id):
    result = search('id:' + document_id, raw=True,
                    filters={'decTreatyId': ''})
    if not len(result):
        return None
    return result
