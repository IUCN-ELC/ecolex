from collections import OrderedDict
from datetime import datetime
from html import unescape
import functools

from django.core.urlresolvers import reverse
from django.utils.html import strip_tags
from django.template.defaultfilters import date as django_date_filter

from ecolex.definitions import DOC_SOURCES, LANGUAGE_MAP


def cached_property(func):
    return property(functools.lru_cache()(func))


def first(obj, default=None):
    if obj and type(obj) is list:
        return obj[0]
    return obj if obj else default

def all(obj, default=None):
    if obj and type(obj) is list:
        return '; '.join(obj)
    return obj if obj else default


# NOTE: code covered in schema marked with '#del'


class ObjectNormalizer:
    KEYWORD_FIELD = 'docKeyword' #del
    SUBJECT_FIELD = 'docSubject' #del

    def __init__(self, solr, hl):
        self.type = solr['type']
        self.solr = solr
        if hl:
            self._set_highlight(hl)

    def _set_highlight(self, hl):
        for field, hl_values in hl.items():
            if field not in self.solr:
                continue
            initial_value = self.solr[field]
            if isinstance(initial_value, list) and len(initial_value) > 1:
                for hl_value in hl_values:
                    idx = initial_value.index(strip_tags(hl_value))
                    initial_value[idx] = hl_value
            else:
                self.solr[field] = hl_values

    def type_of_document(self):
        type_of_doc = self.solr.get(self.DOCTYPE_FIELD)
        return all(type_of_doc, None)

    def id(self):
        return self.solr.get('id')

    def document_id(self):
        #TODO: remove first() after re-import of literature with litId.multiValued=false
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

    def summary(self):
        return first(self.solr.get(self.SUMMARY_FIELD), "")

    def optional_fields(self):
        res = []
        for field, label, type in self.OPTIONAL_INFO_FIELDS:
            entry = {}
            entry['label'] = label
            if isinstance(field, list):
                values = []
                for f in field:
                    value = self.solr.get(f)
                    if value:
                        values.append(value)
                if not values:
                    continue
                entry['value'] = type.join(values)
            else:
                if not self.solr.get(field):
                    continue
                entry['type'] = first(type, 'text')
                value = self.solr.get(field)

                if 'list' in type and isinstance(value, list):
                    value = ', '.join(sorted(value))
                elif 'date' in type:
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

    def get_link_to_full_text(self):
        pass

    def get_language(self):
        pass

    def get_body(self):
        pass

    def get_files(self):
        pass

    @property
    def keywords(self): #del
        return self.solr.get(self.KEYWORD_FIELD, [])

    @property
    def subjects(self): #del
        return self.solr.get(self.SUBJECT_FIELD, [])

    @classmethod
    def get_highlight_fields(cls, hl_details=False):
        hl_fields = cls.TITLE_FIELDS + [cls.SUMMARY_FIELD]
        if hl_details:
            hl_fields.extend([cls.KEYWORD_FIELD, cls.SUBJECT_FIELD])
        return hl_fields

    __repr__ = title


class TreatyParticipant(object):
    FIELD_MAP = {
        'partyCountry': 'country',
        'partyPotentialParty': 'potential party',
        'partyEntryIntoForce': 'entry into force',
        'partyDateOfRatification': 'ratification',
        'partyDateOfAccessionApprobation': 'accession/approbation',
        'partyDateOfAcceptanceApproval': 'acceptance/approval',
        'partyDateOfConsentToBeBound': 'consent to be bound',
        'partyDateOfSuccession': 'succession',
        'partyDateOfDefiniteSignature': 'definite signature',
        'partyDateOfSimpleSignature': 'simple signature',
        'partyDateOfProvisionalApplication': 'provisional application',
        'partyDateOfParticipation': 'participation',
        'partyDateOfReservation': 'reservation',
        'partyDateOfWithdrawal': 'withdrawal',
    }
    MANDATORY_FIELDS = ['entry into force']
    FIELD_GROUPS = {
        'date of ratification *': [
            'ratification',
            'accession/approbation',
            'acceptance/approval',
            'succession',
            'consent to be bound',
            'definite signature',
        ],
        'signature **': [
            'simple signature',
        ],
    }
    EVENTS_ORDER = [
        'potential party',
        'entry into force',
        'date of ratification *',
        'signature **',
        'provisional application',
        'participation',
        'reservation',
        'withdrawal',
    ]
    GROUPED_FIELDS = {field: group
                      for group, fields in FIELD_GROUPS.items()
                      for field in fields}
    EMPTY_VAL = {'date': None}

    def __init__(self, events, values):
        events = dict(zip(events, values))
        self.country = events.pop('country')

        self.events = {}
        for event, value in events.items():
            self._add_event(event, value)

        for field in self.MANDATORY_FIELDS:
            if field not in self.events:
                self.events[field] = None

    def _add_event(self, event, value):
        date = self._clean_date(value)
        group = self.GROUPED_FIELDS.get(event)
        if group and self.events.get(group, self.EMPTY_VAL) == self.EMPTY_VAL:
            self.events[group] = {'date': date}
            if date:
                self.events[group]['subgroup'] = event
                self.events[group]['idx'] = (
                    self.FIELD_GROUPS[group].index(event) + 1)
        else:
            self.events[event] = {'date': date}

    def _clean_date(self, d):
        return d if d != '0002-11-30T00:00:00Z' else None

    @property
    def available_events(self):
        return [event for event in self.EVENTS_ORDER if event in self.events]


class Treaty(ObjectNormalizer):
    ID_FIELD = 'trElisId'
    SUMMARY_FIELD = 'trAbstract_en'
    TITLE_FIELD = 'trPaperTitleOfText'  # multilangual
    # IUCN asked to show all translations of the title
    # TODO: do not repeat the title of the current language
    TITLE_FIELDS = [
        'trPaperTitleOfText_en', 'trPaperTitleOfText_fr',
        'trPaperTitleOfText_es', 'trPaperTitleOfText_other',
        'trTitleOfText', 'trTitleOfTextShort',
    ]
    DATE_FIELDS = ['trDateOfText', 'trDateOfEntry', 'trDateOfModification']
    DOCTYPE_FIELD = 'trTypeOfText_en'
    KEYWORD_FIELD = 'trKeyword_en' #del
    SUBJECT_FIELD = 'trSubject_en' #del
    OPTIONAL_INFO_FIELDS = [
        # (solr field, display text, type=text)
        ('trPlaceOfAdoption', 'Place of adoption', ''),
        ('trRegion', 'Geographical area', ''),
        ('trBasin_en', 'Basin', ''),
        ('trDepository_en', 'Depository', ''),
        ('trUrl', 'Available web site', 'url'),
        ('trOfficialPublication', 'Official publication', ''),
        ('trInternetReference_en', 'Internet Reference', ''),
        ('trDateOfConsolidation', 'Consolidation Date', 'date')
    ]

    FULL_TEXT = 'trLinkToFullText'  # multilangual

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
        return first(self.solr.get('trJurisdiction_en'))

    def place_of_adoption(self):
        return first(self.solr.get('trPlaceOfAdoption'))

    def field_of_application(self):
        return first(self.solr.get('trFieldOfApplication_en'))

    def url(self):
        return first(self.solr.get('trUrlTreatyText'))

    def entry_into_force(self):
        return datetime.strptime(
            first(self.solr.get(
                'trEntryIntoForceDate')), '%Y-%m-%dT%H:%M:%SZ').date()

    @cached_property
    def participants(self):
        party_dict = OrderedDict(
            (event, self.solr.get(field))
            for field, event in TreatyParticipant.FIELD_MAP.items()
            if self.solr.get(field))
        participants = [TreatyParticipant(list(party_dict.keys()), values)
                        for values in zip(*(list(party_dict.values())))]
        if participants:
            participants.sort(key=lambda p: p.country)
            return {'events': participants[0].available_events,
                    'participants': participants}

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

    def title_translations(self):
        titles = []
        for code, language in LANGUAGE_MAP.items():
            if code == 'en':
                # TODO fix this when multilinguality feature is on
                continue
            title = self.solr.get('{}_{}'.format(self.TITLE_FIELD, code))
            if title:
                titles.append({'alttitle': first(title), 'language': language})
        return titles

    @cached_property
    def link_to_full_text(self):
        links = []
        for code, language in LANGUAGE_MAP.items():
            url = self.solr.get('{}_{}'.format(self.FULL_TEXT, code))
            if url:
                links.append({'url': first(url), 'language': language})
        return links


class Decision(ObjectNormalizer):
    ID_FIELD = 'decNumber'
    SUMMARY_FIELD = 'decBody'
    TITLE_FIELDS = ['decShortTitle_en', 'decShortTitle_fr', 'decShortTitle_es',
                    'decShortTitle_ru', 'decShortTitle_ar', 'decShortTitle_zh']
    DATE_FIELDS = ['decPublishDate', 'decUpdateDate']
    DOCTYPE_FIELD = 'decType'
    KEYWORD_FIELD = 'decKeyword'
    OPTIONAL_INFO_FIELDS = [
    ]

    def url(self):
        return first(self.solr.get('decLink'))

    def details_url(self):
        return reverse('decision_details', kwargs={'id': self.id()})

    def status(self):
        return first(self.solr.get('decStatus'), "unknown")

    def get_language(self):
        lang_code = first(self.solr.get('decLanguage'))
        if lang_code:
            return LANGUAGE_MAP.get(lang_code, lang_code)
        return 'Document language'

    def summary(self):
        # TODO - Multilangual selector
        return (first(self.solr.get('decSummary_en') or
                      self.solr.get('decSummary_es') or
                      self.solr.get('decSummary_fr')) or
                '')

    def get_body(self):
        # TODO - Multilangual selector
        return (self.solr.get('decBody_en') or self.solr.get('decBody_es') or
                self.solr.get('decBody_fr') or '')

    def get_files(self):
        urls = self.solr.get('decFileUrls')
        filenames = self.solr.get('decFileNames')
        return list(zip(urls, filenames))


class Literature(ObjectNormalizer):
    ID_FIELD = 'litId'
    LANGUAGE_FIELD = 'litLanguageOfDocument'
    SUMMARY_FIELD = 'litAbstract'
    TITLE_FIELDS = [
        'litPaperTitleOfText', 'litPaperTitleOfText_fr',
        'litPaperTitleOfText_sp', 'litPaperTitleOfText_other',
        'litLongTitle', 'litLongTitle_fr', 'litLongTitle_sp', 'litLongTitle_other',
        'litTitleOfTextShort', 'litTitleOfTextShort_fr',
        'litTitleOfTextShort_sp', 'litTitleOfTextShort_other',
        'litTitleOfTextTransl', 'litTitleOfTextTransl_fr', 'litTitleOfTextTransl_sp'
    ]
    DATE_FIELDS = ['litDateOfEntry', 'litDateOfModification']
    OPTIONAL_INFO_FIELDS = [
        ('litVolumeNo', 'Volume', ''),
        (['litPublisher', 'litPublPlace'], 'Publisher', ' | '),
        ('litDateOfText', 'Date of publication', ''),
        ('litISBN', 'ISBN', ''),
        ('litCollation', 'Pages', ''),
        ('litSeriesFlag', 'Series', ''),
         # TODO: litConfName is a translatable field
        (['litConfName', 'litConfNo', 'litConfDate', 'litConfPlace'], 'Conference', ' | '),
        ('litLanguageOfDocument', 'Language of document', 'list'),
    ]
    DOCTYPE_FIELD = 'litTypeOfText'
    KEYWORD_FIELD = 'litKeyword' #del
    SUBJECT_FIELD = 'litSubject' #del
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

    def document_id(self):
        obj = self.solr.get(self.ID_FIELD)
        #TODO remove after re-import of literature using single value litId
        if obj and type(obj) is list:
            return obj[-1]
        return obj

    def details_url(self):
        return reverse('literature_details', kwargs={'id': self.id()})

    def jurisdiction(self):
        return first(self.solr.get('litScope'))

    def corp_authors(self):
        authors = self.solr.get('litCorpAuthorArticle', [])
        if not authors:
            authors = self.solr.get('litCorpAuthor', [])
        return authors

    def people_authors(self):
        authors = self.solr.get('litAuthorArticle', [])
        if not authors:
            authors = self.solr.get('litAuthor', [])
        return authors

    def authors(self):
        return self.people_authors() or self.corp_authors()

    def countries(self):
        return self.solr.get('litCountry')

    def publisher(self):
        return first(self.solr.get('litPublisher'))

    def region(self):
        return first(self.solr.get('litRegion'))

    def basin(self):
        return first(self.solr.get('litBasin'))

    def publication_place(self):
        return first(self.solr.get('litPublPlace'))

    def publication_date(self):
        return first(self.solr.get('litDateOfTextSer')) or first(self.solr.get('litDateOfText'))

    def parent_title(self):
        parent_title = first(self.solr.get('litLongTitle')) or first(self.solr.get('litSerialTitle'))
        if not parent_title or parent_title == self.title():
            return None
        return parent_title

    def abstract(self):
        return first(self.solr.get('litAbstract'))

    @cached_property
    def link_to_full_text(self):
        links = []
        languages = self.solr.get(self.LANGUAGE_FIELD)
        for idx, link in enumerate(self.solr.get('litLinkToFullText', [])):
            links.append((link, languages[idx]))
        return links

    def get_language(self):
        # TODO: literature can have multiple languages - see ANA-082928
        return (first(self.solr.get('litLanguageOfDocument') or
                      self.solr.get('litLanguageOfDocument_fr') or
                      self.solr.get('litLanguageOfDocument_sp')) or
                'Document language')


class CourtDecision(ObjectNormalizer):
    ID_FIELD = 'cdLeoId'
    SUMMARY_FIELD = 'cdAbstract_en'
    TITLE_FIELDS = ['cdTitleOfText_en', 'cdTitleOfText_es', 'cdTitleOfText_fr']
    DATE_FIELDS = ['cdDateOfText']
    DOCTYPE_FIELD = 'cdTypeOfText'
    KEYWORD_FIELD = 'cdKeywords'
    SUBJECT_FIELD = 'cdSubject'
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
        if not original_id:
            return []
        for doc_type, ref_field in self.REFERENCED_BY_FIELDS.items():
            docs = get_documents_by_field(ref_field, [original_id], rows=100)
            if docs:
                references[doc_type] = docs
        return references

    def language(self):
        langcodes = self.solr.get('cdLanguageOfDocument')
        if langcodes:
            return ', '.join([LANGUAGE_MAP.get(code, code)
                             for code in langcodes])
        return 'Document language'

    def abstract(self):
        return first(self.solr.get('cdAbstract_en'))

    def country(self):
        return first(self.solr.get('cdCountry_en'))


class Legislation(ObjectNormalizer):
    ID_FIELD = 'legId'
    SUMMARY_FIELD = 'legAbstract'
    TITLE_FIELDS = ['legTitle', 'legLongTitle']
    DATE_FIELDS = ['legDate', 'legOriginalDate']
    KEYWORD_FIELD = 'legKeyword_en' #del
    SUBJECT_FIELD = 'legSubject_en' #del

    LEGISLATION_REFERENCE_FIELDS = {
        'legImplement': 'Implements:',
        'legAmends': 'Amends:',
        'legRepeals': 'Repeals:'
    }

    LEGISLATION_BACK_REFERENCE = {
        'legImplement': 'Implemented by:',
        'legAmends': 'Amended by:',
        'legRepeals': 'Repealed by:',
    }

    def get_legislation_references(self):
        from ecolex.search import get_documents_by_field
        references = {}
        for field, label in self.LEGISLATION_REFERENCE_FIELDS.items():
            ids = [v for v in self.solr.get(field, [])]
            results = get_documents_by_field(self.ID_FIELD, ids, rows=100)
            if results:
                references[label] = results
        return references

    def get_legislation_back_references(self):
        from ecolex.search import get_documents_by_field
        references = {}
        leg_id = first(self.solr.get('legId'))
        for field, label in self.LEGISLATION_BACK_REFERENCE.items():
            results = get_documents_by_field(field, [leg_id], rows=100)
            if results:
                references[label] = results
        return references

    def details_url(self):
        return reverse('legislation_details', kwargs={'id': self.id()})

    def country(self):
        return first(self.solr.get('legCountry_en'))

    def status(self):
        return first(self.solr.get('legStatus'))

    def type(self):
        return first(self.solr.get('legType'))

    def language(self):
        languages = self.solr.get('legLanguage_en', [])
        return '/'.join(languages)

    def abstract(self):
        return first(self.solr.get('legAbstract'))

    def date(self):
        text_date = first(self.solr.get('legDate'))
        if text_date:
            return django_date_filter(datetime.strptime(
                   text_date, '%Y-%m-%dT%H:%M:%SZ'), 'b j, Y').title()
        original_date = first(self.solr.get('legOriginalDate'))
        consolidation_date = first(self.solr.get('legConsolidationDate'))
        #import pdb;pdb.set_trace()
        if original_date:
            original_date = django_date_filter(datetime.strptime(original_date,
                            '%Y-%m-%dT%H:%M:%SZ'), 'b j, Y').title()
            if consolidation_date:
                consolidation_date = django_date_filter(datetime.strptime(
                    consolidation_date,'%Y-%m-%dT%H:%M:%SZ'), ' (b j, Y)').title()
            return '%s %s' % (original_date, consolidation_date or '')
        return ""
