from collections import OrderedDict
from datetime import datetime
from html import unescape
from os.path import basename
from urllib import parse as urlparse

import functools
import re

from django.core.urlresolvers import reverse
from django.utils.html import strip_tags
from django.template.defaultfilters import date as django_date_filter
from django.utils.translation import get_language

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


class ObjectNormalizer:
    KEYWORD_FIELD = 'docKeyword'
    SUBJECT_FIELD = 'docSubject_en'

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
                if type == 'attr':
                    value = getattr(self, field)
                    if value:
                        if isinstance(value, list):
                            value = ', '.join(sorted(value))
                        entry['value'] = value
                        res.append(entry)
                    continue
                elif not self.solr.get(field):
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

    def consolidation_date(self):
        pass

    @property
    def keywords(self):
        return self.solr.get(self.KEYWORD_FIELD, [])

    @property
    def subjects(self):
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
        'partyCountry_en': 'country',
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
    KEYWORD_FIELD = 'trKeyword_en'
    SUBJECT_FIELD = 'trSubject_en'
    OPTIONAL_INFO_FIELDS = [
        # (solr field, display text, type=text)
        ('trPlaceOfAdoption', 'Place of adoption', ''),
        ('trDepository_en', 'Depositary', ''),
        ('trLanguageOfDocument_en', 'Language', 'list'),
        # ('trUrl', 'Available web site', 'url'),
        # ('trOfficialPublication', 'Official publication', ''),
        # ('trInternetReference_en', 'Internet Reference', ''),
        ('trEntryIntoForceDate', 'Entry into force', 'date'),
        # ('trDateOfConsolidation', 'Consolidation Date', 'date')
    ]

    FULL_TEXT = 'trLinkToFullText'  # multilangual

    BACK_REFERENCE_LABELS = {
        'Enables:': 'trEnabledByTreaty',
        'Superseded by:': 'trSupersedesTreaty',
        'Cited by:': 'trCitesTreaty',
        'Amended by:': 'trAmendsTreaty',
    }

    REFERENCE_LABELS = {
        'Enabled by:': 'trEnabledByTreaty',
        'Supersedes:': 'trSupersedesTreaty',
        'Cites:': 'trCitesTreaty',
        'Amends:': 'trAmendsTreaty',
    }

    DIRECT_LABELS = ['Enables:', 'Supersedes:', 'Cites:', 'Amends:']
    BACK_LABELS = ['Enabled by:', 'Superseded by:', 'Cited by:', 'Amended by:']

    def jurisdiction(self):
        return first(self.solr.get('trJurisdiction_en'))

    def region(self):
        return self.solr.get('trRegion_en')

    def basin(self):
        return self.solr.get('trBasin_en')

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

    def get_treaty_references(self):
        from ecolex.search import get_documents_by_field
        references = {}
        for label, field in self.REFERENCE_LABELS.items():
            ids = [v for v in self.solr.get(field, [])]
            results = get_documents_by_field(self.ID_FIELD, ids, rows=100)
            if results:
                references[label] = results
        return references

    def get_treaty_back_references(self):
        from ecolex.search import get_documents_by_field
        references = {}
        tr_id = self.solr.get('trElisId')
        for label, field in self.BACK_REFERENCE_LABELS.items():
            results = get_documents_by_field(field, [tr_id], rows=100)
            if results:
                references[label] = results
        return references

    def references(self):
        data = {}
        for field, label in self.REFERENCE_FIELDS.items():
            values = [v for v in self.solr.get(field, [])]
            if values and any(values):
                data[field] = values
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
            urls = self.solr.get('{}_{}'.format(self.FULL_TEXT, code), [])
            for url in urls:
                links.append({'url': url, 'language': language})
        return links


class Decision(ObjectNormalizer):
    ID_FIELD = 'decNumber'
    SUMMARY_FIELD = 'decBody_en'
    TITLE_FIELDS = ['decShortTitle_en', 'decShortTitle_fr', 'decShortTitle_es',
                    'decShortTitle_ru', 'decShortTitle_ar', 'decShortTitle_zh']
    DATE_FIELDS = ['decPublishDate', 'decUpdateDate']
    DOCTYPE_FIELD = 'decType'
    KEYWORD_FIELD = 'decKeyword_en'
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
        return (first(self.solr.get('decBody_en') or
                      self.solr.get('decBody_es') or
                      self.solr.get('decBody_fr'))
                or '')

    def get_files(self):
        urls = self.solr.get('decFileUrls', [])
        filenames = self.solr.get('decFileNames', [])
        return list(zip(urls, filenames))


class Literature(ObjectNormalizer):
    ID_FIELD = 'litId'
    LANGUAGE_FIELD = 'litLanguageOfDocument_en'
    SUMMARY_FIELD = 'litAbstract_en'

    TITLE_FIELD_MAP = {
        'MON': 'litLongTitle',
        'ANA': 'litPaperTitleOfText'
    }
    TITLE_FIELDS = [
        'litPaperTitleOfText_en', 'litLongTitle_en',
        'litPaperTitleOfText_fr', 'litLongTitle_fr',
        'litPaperTitleOfText_es', 'litLongTitle_es',
        'litPaperTitleOfText_other', 'litLongTitle_other',
    ]

    DATE_FIELDS = ['litDateOfEntry', 'litDateOfModification']
    OPTIONAL_INFO_FIELDS = [
        (['litPublisher', 'litPublPlace'], 'Publisher', ' | '),
        ('litISBN', 'ISBN', 'list'),
        ('litISSN', 'ISSN', ''),
        ('collation', 'Pages', 'attr'),
        ('type_of_document', 'Document type', 'attr'),
        # TODO: litConfName is a translatable field
        (['litConfName_en', 'litConfNo', 'litConfDate', 'litConfPlace'], 'Conference', ' | '),
        # literature can have multiple languages - see ANA-082928
        ('litLanguageOfDocument_en', 'Language', 'list'),
    ]
    DOCTYPE_FIELD = 'litTypeOfText_en'
    KEYWORD_FIELD = 'litKeyword_en'
    SUBJECT_FIELD = 'litSubject_en'
    REFERENCE_TO_FIELDS = {
        'litTreatyReference': 'treaty',
        'litLiteratureReference': 'literature',
        'litCourtDecisionReference': 'court_decision',
        'litFaolexReference': 'legislation',
        'litEULegislationReference': 'legislation',
        'litNationalLegislationReference': 'legislation',
    }
    REFERENCE_MAPPING = {
        'treaty': 'trElisId',
        'literature': 'litId',
        'court_decision': 'cdOriginalId',
        'legislation': 'legId',
    }
    REFERENCE_FROM_FIELDS = {
        'litLiteratureReference': 'literature',
    }

    def get_references_to(self):
        from ecolex.search import get_documents_by_field
        ids_dict = {}
        for field, doc_type in self.REFERENCE_TO_FIELDS.items():
            values = [v for v in self.solr.get(field, [])]
            if values and any(values):
                ids_dict[doc_type] = values

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
        return self.solr.get(self.ID_FIELD)

    def date(self):
        return self.solr.get('litYearOfText') or self.solr.get('litDateOfTextSer')

    def details_url(self):
        return reverse('literature_details', kwargs={'id': self.id()})

    def jurisdiction(self):
        return first(self.solr.get('litScope_en'))

    def corp_authors(self):
        authors = self.solr.get('litCorpAuthorA', [])
        if not authors:
            authors = self.solr.get('litCorpAuthorM', [])
        return authors

    def people_authors(self):
        authors = self.solr.get('litAuthorA', [])
        if not authors:
            authors = self.solr.get('litAuthorM', [])
        return authors

    def authors(self):
        return self.people_authors() or self.corp_authors()

    def countries(self):
        return self.solr.get('litCountry_en')

    def publisher(self):
        return first(self.solr.get('litPublisher'))

    def region(self):
        return self.solr.get('litRegion_en')

    def basin(self):
        return self.solr.get('litBasin_en')

    def publication_place(self):
        return first(self.solr.get('litPublPlace'))

    def publication_date(self):
        return first(self.solr.get('litDateOfTextSer')) or first(self.solr.get('litDateOfText'))

    def title_field(self):
        return self.TITLE_FIELD_MAP.get(self.document_id()[:3])

    def get_multilingual(self, field, lang_code):
        # TODO: probably something similar already implemented by Iulia
        return self.solr.get('{}_{}'.format(field, lang_code))

    def get_field_current(self, field):
        # TODO: probably something similar already implemented by Iulia
        # Try current language first
        value = self.get_multilingual(field, get_language())
        if not value:
            for lang_code in LANGUAGE_MAP.keys():
                value = self.get_multilingual(field, lang_code)
                if value:
                    break;
        return value

    def title(self):
        title = first(self.get_field_current(self.title_field()))
        # first is necessary because of excerpt highlighting
        return title or "Unknown Document"

    def title_translations(self):
        titles = []
        main_title = self.title()
        for code, language in LANGUAGE_MAP.items():
            if code == get_language():
                continue
            title = first(self.get_multilingual(self.title_field(), code))
            if title and title != main_title:
                titles.append({'alttitle': title, 'language': language})
        return titles

    @cached_property
    def parent_title(self):
        # only for chapters
        if self.lit_is_chapter:
            return self.get_field_current('litLongTitle')
        return None

    @cached_property
    def lit_is_article(self):
        # TODO: also check document_id ?
        return bool(self.solr.get('litDateOfTextSer', '').strip())

    @cached_property
    def lit_is_chapter(self):
        return self.document_id()[:3] == 'ANA' and not self.lit_is_article

    @cached_property
    def collation(self):
        if not self.lit_is_article:
            # for articles, the collation is included in serial_title
            volume = self.solr.get('litVolumeNo', '')
            collation = self.solr.get('litCollation')
            if volume and collation:
                return ' | '.join([volume, collation])
            else:
                return volume or collation
        return None

    @cached_property
    def serial_title(self):
        if self.lit_is_article:
            # TODO: why don't we include always volume and collation
            # since they are always displayed together?
            return self.solr.get('litSerialTitle')
        else:
            # TODO: when is this shown???
            litSerialTitle = self.solr.get('litSerialTitle', '')
            litVolumeNo = self.solr.get('litVolumeNo', '')
            if litVolumeNo and litSerialTitle:
                return ' | '.join([litSerialTitle, litVolumeNo])
            elif litVolumeNo:
                return litVolumeNo
            else:
                return litSerialTitle
        return None

    @cached_property
    def link_to_full_text(self):
        links = []
        for link in self.solr.get('litLinkToFullText', []):
            filename = basename(urlparse.urlparse(link).path)
            links.append((link, filename))
        return links


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
        languages = self.solr.get('cdLanguageOfDocument_es', None)
        if languages:
            return ', '.join(languages)
        return 'Document language'

    def abstract(self):
        return first(self.solr.get('cdAbstract_en'))

    def country(self):
        return first(self.solr.get('cdCountry_en'))


class Legislation(ObjectNormalizer):
    ID_FIELD = 'legId'
    SUMMARY_FIELD = 'legAbstract'
    TITLE_FIELDS = ['legTitle', 'legLongTitle']
    KEYWORD_FIELD = 'legKeyword_en'
    SUBJECT_FIELD = 'legSubject_en'
    DOCTYPE_FIELD = 'legType_en'
    OPTIONAL_INFO_FIELDS = []

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

    def region(self):
        return self.solr.get('legGeoArea_en')

    def basin(self):
        return self.solr.get('legBasin_en')

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
        return self.solr.get('legYear')

    def consolidation_date(self):
        legOriginalYear = self.solr.get('legOriginalYear')
        if legOriginalYear:
            return legOriginalYear
