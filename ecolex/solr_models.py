from collections import OrderedDict
from datetime import datetime
from html import unescape

from django.core.urlresolvers import reverse

from ecolex.definitions import DOC_SOURCES, LANGUAGE_MAP


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

    def type_of_document(self):
        type_of_doc = self.solr.get(self.DOCTYPE_FIELD)
        return first(type_of_doc, "Unknown type of document")

    def id(self):
        return self.solr.get('id')

    def document_id(self):
        return first(self.solr.get(self.ID_FIELD))

    def title(self):
        for title_field in self.TITLE_FIELDS:
            title = self.solr.get(title_field)
            if not title:
                continue

            if isinstance(title, list):
                title = max(title, key=lambda x: len(x))
            if len(title):
                return unescape(title)
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

    def details_url(self):
        raise NotImplementedError

    def source(self):
        source = DOC_SOURCES.get(self.type, "Unknown source")
        return source

    __repr__ = title


class Treaty(ObjectNormalizer):
    ID_FIELD = 'trElisId'
    SUMMARY_FIELD = 'trIntroText'
    TITLE_FIELDS = [
        'trPaperTitleOfText', 'trPaperTitleOfTextFr', 'trPaperTitleOfTextSp',
        'trPaperTitleOfTextOther', 'trTitleOfTextShort',
    ]
    DATE_FIELDS = ['trDateOfText', 'trDateOfEntry', 'trDateOfModification']
    DOCTYPE_FIELD = 'trTypeOfText'
    OPTIONAL_INFO_FIELDS = [
        # (solr field, display text, type=text)
        ('trTitleAbbreviation', 'Title Abbreviation', ''),
        #('trEntryIntoForceDate', 'Entry into force', 'date'),
        ('trPlaceOfAdoption', 'Place of adoption', ''),
        ('trAvailableIn', 'Available in', ''),
        ('trRegion', 'Geographical area', ''),
        ('trBasin', 'Basin', ''),
        ('trDepository', 'Depository', ''),
        ('trUrl', 'Available web site', 'url'),
        #('trLinkToFullText', 'Link to full text', 'url'),
        #('trLinkToFullTextSp', 'Link to full text (spanish)', 'url'),
        #('trLinkToFullTextFr', 'Link to full text (french)', 'url'),
        #('trLinkToFullTextOther', 'Link to full text (other)', 'url'),
        ('trLanguageOfDocument', 'Language', ''),
        ('trLanguageOfTranslation', 'Translation', ''),
        #('trAbstract', 'Abstract', 'text'),
        # display comments the same way as texts
        #('trComment', 'Comment', 'text'),
        # keywords are considered safe.
        #('trSubject', 'Subject', 'keyword'),
        # ('trKeyword', 'Keywords', 'keyword'),
        #('trNumberOfPages', 'Number of pages', ''),
        ('trOfficialPublication', 'Official publication', ''),
        ('trInternetReference', 'Internet Reference', ''),
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

    def place_of_adoption(self):
        return first(self.solr.get('trPlaceOfAdoption'))

    def field_of_application(self):
        return first(self.solr.get('trFieldOfApplication'))

    def url(self):
        return first(self.solr.get('trUrlTreatyText'))

    def entry_into_force(self):
        return datetime.strptime(
            first(self.solr.get(
                'trEntryIntoForceDate')), '%Y-%m-%dT%H:%M:%SZ').date()

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

    def get_decisions(self):
        from ecolex.search import get_documents_by_field
        if not self.informea_id():
            return []
        return get_documents_by_field('decTreatyId',
                                      [self.informea_id()], rows=100)

    def get_literatures(self):
        from ecolex.search import get_documents_by_field
        return get_documents_by_field('litTreatyReference',
                                      [self.solr.get('trElisId')], rows=100)

    def get_court_decisions(self):
        from ecolex.search import get_documents_by_field
        return get_documents_by_field('cdTreatyReference',
                                      [self.solr.get('trElisId')], rows=100)

    def full_title(self):
        return '{} ({})'.format(self.title(), self.date())

    def informea_id(self):
        return first(self.solr.get('trInformeaId'))

    def details_url(self):
        return reverse('treaty_details', kwargs={'id': self.id()})


class Decision(ObjectNormalizer):
    ID_FIELD = 'decNumber'
    SUMMARY_FIELD = 'decBody'
    TITLE_FIELDS = ['decTitleOfText']
    DATE_FIELDS = ['decPublishDate', 'decUpdateDate']
    DOCTYPE_FIELD = 'decType'
    OPTIONAL_INFO_FIELDS = [
        ('decUpdateDate', 'Date of Update', 'date'),
    ]

    def url(self):
        return first(self.solr.get('decLink'))

    def details_url(self):
        return reverse('decision_details', kwargs={'id': self.id()})

    def status(self):
        return first(self.solr.get('decStatus'), "unknown")


class Literature(ObjectNormalizer):
    ID_FIELD = 'litId'
    SUMMARY_FIELD = 'litAbstract'
    TITLE_FIELDS = ['litLongTitle', 'litLongTitle_fr', 'litLongTitle_sp',
                    'litLongTitle_other',
                    'litPaperTitleOfText', 'litPaperTitleOfText_fr',
                    'litPaperTitleOfText_sp', 'litPaperTitleOfText_other',
                    'litTitleOfTextShort', 'litTitleOfTextShort_fr',
                    'litTitleOfTextShort_sp', 'litTitleOfTextShort_other',
                    'litTitleOfTextTransl', 'litTitleOfTextTransl_fr',
                    'litTitleOfTextTransl_sp']
    DATE_FIELDS = ['litDateOfEntry', 'litDateOfModification']
    DOCTYPE_FIELD = 'litTypeOfText'
    REFERENCE_TO_FIELDS = {
        'litTreatyReference': 'treaty',
        'litLiteratureReference': 'literature',
        'litCourtDecisionReference': 'court_decision',
    }
    REFERENCE_MAPPING = {
        'treaty': 'trElisId',
        'literature': 'litId',
        'court_decision': 'cdOriginalId',
    }
    REFERENCE_FROM_FIELDS = {
        'litLiteratureReference': 'literature',
    }

    def get_references_ids_dict(self):
        ids_dict = {}
        for field, doc_type in self.REFERENCE_TO_FIELDS.items():
            values = [v for v in self.solr.get(field, [])]
            if values and any(values):
                ids_dict[doc_type] = values
        return ids_dict

    def get_references_from_ids(self, ids_dict):
        from ecolex.search import get_documents_by_field
        references = {}
        for doc_type, ids in ids_dict.items():
            results = get_documents_by_field(self.REFERENCE_MAPPING[doc_type],
                                             ids, rows=10)
            if results:
                references[doc_type] = results
        return references

    def get_references_from(self):
        from ecolex.search import get_documents_by_field
        lit_id = self.document_id()
        references = {}

        for field, doc_type in self.REFERENCE_FROM_FIELDS.items():
            results = get_documents_by_field(field, [lit_id])
            if results:
                references[doc_type] = results
        return references

    def details_url(self):
        return reverse('literature_details', kwargs={'id': self.id()})

    def jurisdiction(self):
        return first(self.solr.get('litScope'))

    def authors(self):
        authors = self.solr.get('litAuthor')
        if not authors:
            authors = self.solr.get('litCorpAuthor')
        return authors

    def country(self):
        return first(self.solr.get('litCountry'))

    def publisher(self):
        return first(self.solr.get('litPublisher'))

    def publication_place(self):
        return first(self.solr.get('litPublPlace'))

    def publication_date(self):
        return first(self.solr.get('litDateOfText'))

    def keywords(self):
        return first(self.solr.get('litKeyword'))

    def abstract(self):
        return first(self.solr.get('litAbstract'))


class CourtDecision(ObjectNormalizer):
    ID_FIELD = 'cdLeoId'
    SUMMARY_FIELD = 'cdAbstract_en'
    TITLE_FIELDS = ['cdTitleOfText_en', 'cdTitleOfText_es', 'cdTitleOfText_fr']
    DATE_FIELDS = ['cdDateOfText']
    DOCTYPE_FIELD = 'cdTypeOfText'
    REFERENCE_FIELDS = {'treaty': 'cdTreatyReference'}
    SOURCE_REF_FIELDS = {'treaty': 'trElisId'}
    REFERENCED_BY_FIELDS = {'literature': 'litCourtDecisionReference'}

    def details_url(self):
        return reverse('court_decision_details', kwargs={'id': self.id()})

    def get_references(self):
        from ecolex.search import get_documents_by_field
        references = {}
        for doc_type, ref_field in self.REFERENCE_FIELDS.items():
            ref_id = first(self.solr.get(ref_field))
            if not ref_id:
                continue
            docs = get_documents_by_field(self.SOURCE_REF_FIELDS[doc_type],
                                          [ref_id], rows=100)
            if docs:
                references[doc_type] = docs
        return references

    def get_referenced_by(self):
        from ecolex.search import get_documents_by_field
        references = {}
        original_id = first(self.solr.get('cdOriginalId'))
        for doc_type, ref_field in self.REFERENCED_BY_FIELDS.items():
            docs = get_documents_by_field(ref_field, [original_id], rows=100)
            if docs:
                references[doc_type] = docs
        return references

    def language(self):
        langcodes = self.solr.get('cdLanguageOfDocument')
        return ', '.join([LANGUAGE_MAP.get(code, code) for code in langcodes])
