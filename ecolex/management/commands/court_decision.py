from datetime import datetime, timedelta
import json
import logging
import logging.config

from django.conf import settings
from django.template.defaultfilters import slugify

from ecolex.management.commands.logging import LOG_DICT
from ecolex.management.definitions import COURT_DECISION
from ecolex.management.utils import EcolexSolr, get_json_from_url
from ecolex.management.utils import get_file_from_url


logging.config.dictConfig(LOG_DICT)
logger = logging.getLogger('import')
URL_CHANGE_FROM = 'http://www.ecolex.org/server2.php/server2neu.php/'
URL_CHANGE_TO = 'http://www.ecolex.org/server2neu.php/'
replace_url = lambda text: (URL_CHANGE_TO + text.split(URL_CHANGE_FROM)[-1]) if text.startswith(URL_CHANGE_FROM) else text


JSON_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
SOLR_DATE_FORMAT = '%Y-%m-%dT%H:%M:%SZ'
FIELD_MAP = {
    'title_field': 'cdTitleOfText',
    'field_abstract': 'cdAbstract',
    'field_abstract_other': 'cdAbstract_other',
    'field_document_abstract': 'cdLinkToAbstract',
    'field_alternative_record_id': 'cdAlternativeRecordId',
    'field_city': 'cdSeatOfCourt',
    'field_country': 'cdCountry',
    'field_court_decision_id_number': 'cdCourtDecisionIdNumber',
    'field_court_decision_subdivision': 'cdCourtDecisionSubdivision',
    'field_court_name': 'cdCourtName',
    'field_date_of_entry': 'cdDateOfEntry',
    'changed': 'cdDateOfModification',
    'field_ecolex_decision_status': 'cdStatusOfDecision',
    'field_ecolex_tags': 'cdSubject',
    'field_ecolex_url': 'cdEcolexUrl',
    'field_faolex_url': 'cdFaolexUrl',
    'field_files': 'cdFiles',
    'field_informea_tags': 'cdInformeaTags',
    'field_isis_number': 'cdIsisNumber',  # IsisMfn
    'field_jurisdiction': 'cdJurisdiction',
    'field_justices': 'cdJustices',
    'field_number_of_pages': 'cdNumberOfPages',
    'field_original_id': 'cdOriginalId',
    'field_reference_number': 'cdReferenceNumber',
    'field_related_url': 'cdRelatedUrl',  # relatedWebsite
    'field_source_language': 'cdLanguageOfDocument',
    'field_territorial_subdivision': 'cdTerritorialSubdivision',
    'field_type_of_text': 'cdTypeOfText',
    'field_url': 'cdLinkToFullText',
    'field_url_other': 'cdLinkToFullText_other',
    'field_notes': 'cdNotes',
    'field_available_in': 'cdAvailableIn',
    'field_court_decision_raw': 'cdCourtDecisionReference',
    'field_ecolex_keywords': 'cdKeyword',
    'field_faolex_reference_raw': 'cdFaolexReference',
    'field_instance': 'cdInstance',
    'field_official_publication': 'cdOfficialPublication',
    'field_region': 'cdRegion',  # fallback on field_region_ecolex
    'field_title_of_text_other': 'cdTitleOfText_other',
    'field_title_of_text_short': 'cdTitleOfTextShort',
    'field_ecolex_treaty_raw': 'cdTreatyReference',
    'field_sorting_date': 'cdDateOfText',
}
MULTILINGUAL_FIELDS = [
    'title_field',
    'field_abstract',
    'field_ecolex_url',
    'field_faolex_url',
    'field_related_url',
    'field_city',
]

FIELD_URL = ['field_url', 'field_files']

FALSE_MULTILINGUAL_FIELDS = [
    'field_alternative_record_id',
    'field_document_abstract',
    'field_court_name',
    'field_date_of_entry',
    'field_sorting_date',
    'field_isis_number',
    'field_justices',
    'field_number_of_pages',
    'field_original_id',
    'field_reference_number',
    'field_available_in',
    'field_court_decision_subdivision',
    'field_title_of_text_short',
    'field_instance',
    'field_title_of_text_other',
    'field_url_other',
    'field_official_publication',
    'field_notes',
    'field_ecolex_treaty_raw',
    'field_faolex_reference_raw',
    'field_court_decision_raw',
]
MULTIVALUED_FIELDS = [
    'field_justices',
    'field_ecolex_tags',
    'field_informea_tags',
    'field_ecolex_keywords',
    'field_notes',
    'field_ecolex_treaty_raw',
    'field_faolex_reference_raw',
    'field_ecolex_region',
    'field_region',
]
DATE_FIELDS = [
    'field_date_of_entry',
    'field_sorting_date',
]
TIMESTAMP_FIELDS = [
    'changed',
]
INTEGER_FIELDS = ['field_number_of_pages']
COUNTRY_FIELDS = ['field_country']
LANGUAGE_FIELDS = ['field_source_language']
REGION_FIELDS = ['field_region']
KEYWORD_FIELDS = ['field_ecolex_keywords']
SUBJECT_FIELDS = ['field_ecolex_tags']
FULL_TEXT_FIELDS = ['field_document_abstract']
SUBDIVISION_FIELDS = ['field_territorial_subdivision']
REFERENCE_FIELDS = {'field_ecolex_treaty_raw': 'value',
                    'field_faolex_reference_raw': 'value',
                    'field_court_decision_raw': 'value'}
FILES_FIELDS = ['field_files', 'field_url']  # copy to cdLinkToFullText
SOURCE_URL_FIELD = 'url'
LANGUAGES = ['en', 'es', 'fr']


def get_country_value(countries, value):
    if len(value) != 1:
        logger.error('Unexpected value: {}!'.format(value))
        return {}
    country = countries.get(value[0], {})
    if not country:
        logger.error('Country code {} not found!'.format(value))
    return country


def get_value(key, value):
    if not value:
        return

    final_val = value

    if key in MULTIVALUED_FIELDS:
        final_val = [get_value_from_dict(d) for d in value]
    elif isinstance(value, list):
        value = value[0]
    if isinstance(value, dict):
        final_val = get_value_from_dict(value)

    if not final_val:
        return

    if key in DATE_FIELDS:
        date = datetime.strptime(final_val, JSON_DATE_FORMAT)
        final_val = date.strftime(SOLR_DATE_FORMAT)
    elif key in INTEGER_FIELDS:
        final_val = int(final_val)

    return final_val


def get_value_from_dict(valdict):
    return valdict.get('safe_value',
                       valdict.get('value',
                                   valdict.get('label', valdict.get('url'))))


class CourtDecision(object):
    def __init__(self, data, countries, languages, regions, subdivisions,
                 keywords, subjects, solr, changed):
        self.data = data
        self.countries = countries
        self.languages = languages
        self.regions = regions
        self.subdivisions = subdivisions
        self.keywords = keywords
        self.subjects = subjects
        self.solr = solr
        if changed and self.data['changed'] != changed:
            logger.error('Changed timestamp incosistency on {}'.format(
                self.data['uuid']))

    def get_solr_format(self, leo_id, solr_id):
        solr_decision = {
            'cdText': '',
            'type': COURT_DECISION,
            'cdLeoId': leo_id,
            'id': solr_id,
            'cdCountry_en': [],
            'cdCountry_es': [],
            'cdCountry_fr': [],
            'cdLinkToFullText': [],
        }
        for json_field, solr_field in FIELD_MAP.items():
            json_value = self.data.get(json_field, None)
            if not json_value:
                solr_decision[solr_field] = None
            elif json_field in REFERENCE_FIELDS:
                if json_field in FALSE_MULTILINGUAL_FIELDS:
                    json_value = json_value['und']
                solr_decision[solr_field] = [e.get(REFERENCE_FIELDS[json_field])
                                             for e in json_value]
            elif json_field in FALSE_MULTILINGUAL_FIELDS:
                solr_decision[solr_field] = get_value(json_field,
                                                      json_value['und'])
            elif json_field in FIELD_URL:
                urls = [x.get('url') for x in json_value.get('en', [])
                        if x.get('url')]
                if solr_decision['cdLinkToFullText'] is None:
                    solr_decision['cdLinkToFullText'] = []
                for url in urls:
                    if url not in solr_decision['cdLinkToFullText']:
                        solr_decision['cdLinkToFullText'].append(url)
            elif json_field in TIMESTAMP_FIELDS:
                date_value = datetime.fromtimestamp(float(json_value))
                date_string = date_value.strftime(SOLR_DATE_FORMAT)
                solr_decision[solr_field] = date_string
            elif json_field in MULTILINGUAL_FIELDS:
                for lang, value in json_value.items():
                    if lang in settings.LANGUAGE_MAP:
                        key = '{}_{}'.format(solr_field, lang)
                        solr_decision[key] = get_value(json_field, value)
            elif json_field in COUNTRY_FIELDS:
                for country_code in json_value:
                    countries = self.countries.get(country_code, {})
                    for lang, country_name in countries.items():
                        key = '{}_{}'.format(solr_field, lang)
                        solr_decision[key].append(country_name)
            elif json_field in LANGUAGE_FIELDS:
                language_code = get_value(json_field, json_value['und'])
                if language_code not in self.languages:
                    logger.warning('Language code missing from languages.json: '
                                   '{} ({})'.format(language_code, leo_id))
                    continue
                languages = self.languages[language_code]
                for lang in LANGUAGES:
                    field = '{}_{}'.format(solr_field, lang)
                    if languages:
                        solr_decision[field] = languages[lang]
                    else:
                        solr_decision[field] = language_code
            elif json_field in SUBDIVISION_FIELDS:
                subdivision_en = get_value(json_field, json_value)
                solr_decision[solr_field + '_en'] = subdivision_en
                values = self.subdivisions.get(subdivision_en, None)
                if values:
                    solr_decision[solr_field + '_es'] = values['Spanish']
                    solr_decision[solr_field + '_fr'] = values['French']
            elif json_field in REGION_FIELDS:
                regions_en = get_value(json_field, json_value)
                solr_decision[solr_field + '_en'] = []
                solr_decision[solr_field + '_fr'] = []
                solr_decision[solr_field + '_es'] = []
                for reg_en in regions_en:
                    region_en = reg_en.lower()
                    if region_en not in self.regions:
                        solr_decision[solr_field + '_en'].append(reg_en)
                        logger.warning('Region missing from regions.json: '
                                       '{} ({})'.format(region_en, leo_id))
                        continue
                    solr_decision[solr_field + '_en'].append(
                        self.regions[region_en]['en'])
                    solr_decision[solr_field + '_fr'].append(
                        self.regions[region_en]['fr'])
                    solr_decision[solr_field + '_es'].append(
                        self.regions[region_en]['es'])
            elif json_field in KEYWORD_FIELDS:
                # This is shitty, must refactor TODO
                keywords_en = get_value(json_field, json_value)
                solr_decision[solr_field + '_en'] = []
                solr_decision[solr_field + '_fr'] = []
                solr_decision[solr_field + '_es'] = []
                for kw_en in keywords_en:
                    keyword_en = kw_en.lower()
                    if keyword_en not in self.keywords:
                        solr_decision[solr_field + '_en'].append(kw_en)
                        logger.warning('Keyword missing from keywords.json: '
                                       '{} ({})'.format(keyword_en, leo_id))
                        continue
                    solr_decision[solr_field + '_en'].append(
                        self.keywords[keyword_en]['en'])
                    solr_decision[solr_field + '_fr'].append(
                        self.keywords[keyword_en]['fr'])
                    solr_decision[solr_field + '_es'].append(
                        self.keywords[keyword_en]['es'])
            elif json_field in SUBJECT_FIELDS:
                # This is shitty, must refactor TODO
                subjects_en = get_value(json_field, json_value)
                solr_decision[solr_field + '_en'] = []
                solr_decision[solr_field + '_fr'] = []
                solr_decision[solr_field + '_es'] = []
                for subj_en in subjects_en:
                    subject_en = subj_en.lower()
                    if subject_en not in self.subjects:
                        solr_decision[solr_field + '_en'].append(subj_en)
                        logger.warning('Subject missing from subjects.json: '
                                       '{} ({})'.format(subject_en, leo_id))
                        continue
                    solr_decision[solr_field + '_en'].append(
                        self.subjects[subject_en]['en'])
                    solr_decision[solr_field + '_fr'].append(
                        self.subjects[subject_en]['fr'])
                    solr_decision[solr_field + '_es'].append(
                        self.subjects[subject_en]['es'])
            else:
                solr_decision[solr_field] = get_value(json_field, json_value)

            if json_field in FULL_TEXT_FIELDS and json_value:
                urls = [replace_url(d.get('url')) for val in json_value.values()
                        for d in val]
                files = [get_file_from_url(url) for url in urls if url]
                solr_decision['cdText'] += '\n'.join(self.solr.extract(f)
                                                     for f in files if f)
        # cdRegion fallback on field_ecolex_region
        if not solr_decision.get('cdRegion_en'):
            backup_field = 'field_ecolex_region'
            solr_field = 'cdRegion'
            json_value = self.data.get(backup_field, None)
            if json_value:
                regions_en = get_value(backup_field, json_value)
                solr_decision[solr_field + '_en'] = []
                solr_decision[solr_field + '_fr'] = []
                solr_decision[solr_field + '_es'] = []
                for reg_en in regions_en:
                    region_en = reg_en.lower()
                    if region_en not in self.regions:
                        solr_decision[solr_field + '_en'].append(reg_en)
                        logger.warning('Region missing from regions.json: '
                                       '{} ({})'.format(region_en, leo_id))
                        continue
                    solr_decision[solr_field + '_en'].append(
                        self.regions[region_en]['en'])
                    solr_decision[solr_field + '_fr'].append(
                        self.regions[region_en]['fr'])
                    solr_decision[solr_field + '_es'].append(
                        self.regions[region_en]['es'])

        full_text_urls = solr_decision.get('cdLinkToFullText') or []
        if not full_text_urls and solr_decision.get('cdRelatedUrl_en'):
            url = solr_decision.pop('cdRelatedUrl_en')
            solr_decision['cdLinkToFullText'] = [url]
            full_text_urls.append(url)

        for url in full_text_urls:
            file_obj = get_file_from_url(url)
            if file_obj:
                solr_decision['cdText'] += '\n'.join(self.solr.extract(file_obj))

        # Get Leo URL
        json_value = self.data.get(SOURCE_URL_FIELD, None)
        if json_value:
            solr_decision['cdLeoDefaultUrl'] = json_value.get('default', None)
            solr_decision['cdLeoEnglishUrl'] = json_value.get('en', None)

        title = (solr_decision.get('cdTitleOfText_en') or
                 solr_decision.get('cdTitleOfText_fr') or
                 solr_decision.get('cdTitleOfText_es') or
                 solr_decision.get('cdTitleOfText_other') or '')
        if not title:
            logger.warning('Title missing for {}'.format(leo_id))
        slug = '{} {}'.format(title, leo_id)
        solr_decision['slug'] = slugify(slug)

        return solr_decision


class CourtDecisionImporter(object):
    def __init__(self, config):
        self.solr_timeout = config.get('solr_timeout')
        self.days_ago = config.get('days_ago')
        self.update = config.get('update')
        self.countries_json = config.get('countries_json')
        self.languages_json = config.get('languages_json')
        self.regions_json = config.get('regions_json')
        self.subdivisions_json = config.get('subdivisions_json')
        self.keywords_json = config.get('keywords_json')
        self.subjects_json = config.get('subjects_json')
        self.court_decisions_url = config.get('court_decisions_url')
        self.test_input_file = config.get('test_input_file')
        self.test_output_file = config.get('test_output_file')
        self.countries = self._get_countries()
        self.languages = self._get_languages()
        self.regions = self._get_regions()
        self.subdivisions = self._get_subdivisions()
        self.keywords = self._get_keywords()
        self.subjects = self._get_subjects()
        self.solr = EcolexSolr(self.solr_timeout)
        # When we need to import only one decision
        self.uuid = config.get('uuid')
        self.data_url = config.get('data_url')
        if (self.uuid):
            self.data_url = self.data_url % (self.uuid,)
        logger.info('Started Court Decision importer')

    def test(self):
        with open(self.test_input_file) as fi, open(self.test_output_file) as fo:
            init_decision = json.load(fi)
            expected_decision = json.load(fo)

        decision = CourtDecision(init_decision, self.countries, self.languages,
                                 self.solr, '0')
        solr_decision = decision.get_solr_format(None, None)

        return solr_decision == expected_decision

    def harvest(self, batch_size):
        if self.uuid:
            logger.info('Adding court decision {}'.format(self.uuid))
            decision = {'data_url': self.data_url, 'uuid': self.uuid}
            self.solr.add_bulk([self._get_solr_decision(decision)])
            return

        decisions = self._get_decisions()
        start = 0
        while start < len(decisions):
            end = min(start + batch_size, len(decisions))
            new_decisions = list(
                filter(bool, [self._get_solr_decision(decision)
                              for decision in decisions[start:end]]))
            logger.info('Adding {} court decisions'.format(len(new_decisions)))
            self.solr.add_bulk(new_decisions)
            start = end

    def needs_update(self, decision, existing_decision):
        current_timestamp = decision.get('last_update')
        if not current_timestamp:
            return True
        old_timestamp = existing_decision['cdDateOfModification']
        current_date = datetime.fromtimestamp(float(current_timestamp))
        old_date = datetime.strptime(old_timestamp, SOLR_DATE_FORMAT)
        delta = current_date - old_date
        if delta.total_seconds() == 0:
            logger.info('Skip {} - no update'.format(decision['uuid']))
            return False
        return True

    def _get_solr_decision(self, decision):
        existing_decision = self.solr.search(COURT_DECISION, decision['uuid'])
        if self.update and existing_decision:
            if not self.needs_update(decision, existing_decision):
                return

        data = self._get_decision(decision['data_url'])
        if not data:
            return
        last_update = decision.get('last_update')
        new_decision = CourtDecision(data, self.countries, self.languages,
                                     self.regions, self.subdivisions,
                                     self.keywords, self.subjects, self.solr,
                                     last_update)
        solr_id = existing_decision['id'] if existing_decision else None
        return new_decision.get_solr_format(decision['uuid'], solr_id)

    def _get_decision(self, url):
        headers = {'Accept': 'application/json'}
        return get_json_from_url(url, headers)

    def _get_decisions(self):
        return get_json_from_url(self.court_decisions_url)

    def _get_countries(self):
        with open(self.countries_json) as f:
            codes_countries = json.load(f)
        codes = codes_countries['code_corresp']
        countries = codes_countries['official_names']
        reverse_codes = {v: k for k, v in codes.items()}
        return {reverse_codes.get(k, k): v for k, v in countries.items()}

    def _get_languages(self):
        with open(self.languages_json) as f:
            languages_codes = json.load(f)
        return languages_codes

    def _get_regions(self):
        with open(self.regions_json) as f:
            regions = json.load(f)
        return regions

    def _get_subdivisions(self):
        with open(self.subdivisions_json) as f:
            subdivisions = json.load(f)
        return subdivisions

    def _get_keywords(self):
        with open(self.keywords_json) as f:
            keywords = json.load(f)
        return keywords

    def _get_subjects(self):
        with open(self.subjects_json) as f:
            subjects = json.load(f)
        return subjects
