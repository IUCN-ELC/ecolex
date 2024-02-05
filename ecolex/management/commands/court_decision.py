from datetime import datetime
from html import unescape
from urllib.parse import urlparse

from json.decoder import JSONDecodeError

import logging
import logging.config

import requests
from requests.adapters import HTTPAdapter

from django.conf import settings
from django.template.defaultfilters import slugify

from ecolex.management.commands.base import BaseImporter
from ecolex.management.commands.logging import LOG_DICT
from ecolex.management.definitions import COURT_DECISION
from ecolex.management.utils import get_file_from_url, get_dict_from_json
from ecolex.management.utils import keywords_informea_to_ecolex
from ecolex.management.utils import keywords_ecolex


logging.config.dictConfig(LOG_DICT)
logger = logging.getLogger('court_decision_import')
URL_CHANGE_FROM = 'http://www.ecolex.org/server2.php/server2neu.php/'
URL_CHANGE_TO = 'http://www.ecolex.org/server2neu.php/'


def replace_url(text):
    if text.startswith(URL_CHANGE_FROM):
        return (URL_CHANGE_TO + text.split(URL_CHANGE_FROM)[-1])
    return text


# JSON_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
JSON_DATE_FORMAT = '%Y-%m-%d'
SOLR_DATE_FORMAT = '%Y-%m-%dT%H:%M:%SZ'
FIELD_MAP = {
    'title_field': 'cdTitleOfText',
    'field_abstract': 'cdAbstract',
    'field_abstract_other': 'cdAbstract_other',
    'field_document_abstract': 'cdLinkToAbstract',
    'field_alternative_record_id': 'cdAlternativeRecordId',
    'field_seat_of_court': 'cdSeatOfCourt_en',
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
    'field_available_website': 'cdRelatedUrl',  # relatedWebsite
    'field_source_language': 'cdLanguageOfDocument',
    'field_territorial_subdivision': 'cdTerritorialSubdivision',
    'field_type_of_text': 'cdTypeOfText',
    'field_external_url': 'cdLinkToFullText',
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
    'field_available_website',
]

FILE_FIELDS = ['field_files', 'field_external_url']  # add to cdLinkToFullText

FALSE_MULTILINGUAL_FIELDS = [
    'field_alternative_record_id',
    'field_document_abstract',
    'field_court_name',
    'field_seat_of_court',
    'field_date_of_entry',
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
    'field_external_url_alt',
    'field_official_publication',
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
SOURCE_URL_FIELDS = [
    'url',  # InforMEA
    'field_external_url_alt',  # judicial portal
]
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

    if type(value) is dict:
        if key in FALSE_MULTILINGUAL_FIELDS and 'und' in value:
            value = value.get('und')
        elif key not in MULTILINGUAL_FIELDS and 'en' in value:
            value = value.get('en')

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
    if 'und' in valdict or 'en' in valdict:
        value = valdict.get('en') or valdict.get('und')
    value = valdict.get(
        'value',
        valdict.get(
            'safe_value',
            valdict.get(
                'label',
                valdict.get(
                    'url',
                    valdict.get('uri')
                )
            )
        )
    )
    if value:
        return unescape(value)
    else:
        return None


def get_json_values(import_field, import_value, json_dict, mapping_dict, doc_id):
    values_en = get_value(import_field, import_value)
    result = {langcode: [] for langcode in LANGUAGES}
    for value in values_en:
        lower_value = value.lower()
        if lower_value not in json_dict:
            result['en'].append(value)
            logger.warning('Key missing from {}.json: {} ({})'
                           .format(mapping_dict, lower_value, doc_id))
            continue
        for k, v in result.items():
            v.append(json_dict[lower_value][k])
    return result


def request_json(url, *args, **kwargs):
    # needed to for retry
    s = requests.Session()
    s.mount(url, HTTPAdapter(max_retries=3))
    try:
        return s.get(url, *args, **kwargs).json()
    except Exception:
        logger.exception('Error fetching url: %s.', url)
        raise


def request_page(url, items_per_page, page=0):
    params = dict(
        items_per_page=items_per_page,
        page=page,
    )
    logger.info('Fetching page %s.', page)
    return request_json(url, params=params)


class CourtDecision(object):
    def __init__(self, data, countries, languages, regions, subdivisions,
                 keywords, informea_keywords, subjects, solr):
        self.data = data
        self.countries = countries
        self.languages = languages
        self.regions = regions
        self.subdivisions = subdivisions
        self.keywords = keywords
        self.informea_keywords = informea_keywords
        self.subjects = subjects
        self.solr = solr

    def informea_tags(self, lang):
        to_ecolex = keywords_informea_to_ecolex(
            self.informea_keywords,
            self.keywords,
            self.data.get('field_informea_tags', [])
        )

        return keywords_ecolex(to_ecolex, lang)

    def get_solr_format(self, informea_id, solr_id):
        solr_decision = {
            'cdText': '',
            'type': COURT_DECISION,
            'cdLeoId': informea_id,
            'id': solr_id,
            'cdCountry_en': [],
            'cdCountry_es': [],
            'cdCountry_fr': [],
            'cdLinkToFullText': [],
        }
        for json_field, solr_field in FIELD_MAP.items():
            json_value = self.data.get(json_field, None)
            # print(f"field: {json_field}, value: {json_value}")
            if not json_value:
                solr_decision[solr_field] = (None if solr_field
                                             not in solr_decision else
                                             solr_decision[solr_field])
            elif json_field in REFERENCE_FIELDS:
                if json_field in FALSE_MULTILINGUAL_FIELDS:
                    json_value = json_value['und']
                solr_decision[solr_field] = [e.get(REFERENCE_FIELDS[json_field])
                                             for e in json_value]
            elif json_field in FALSE_MULTILINGUAL_FIELDS:
                solr_decision[solr_field] = get_value(json_field,
                                                      json_value['und'])
            elif json_field in FILE_FIELDS:
                urls = [
                    x.get('uri') or x.get('url')
                    for x in json_value.get('en', [])
                    if x.get('uri') or x.get('url')
                ]
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
                                   '{} ({})'.format(language_code, informea_id))
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
                values = self.subdivisions.get(subdivision_en.lower(), None)
                if values:
                    solr_decision[solr_field + '_es'] = values['es']
                    solr_decision[solr_field + '_fr'] = values['fr']
                else:
                    logger.warning('Subdivision missing from json: '
                                   '{} ({})'.format(subdivision_en, informea_id))
            elif json_field in REGION_FIELDS:
                reg_dict = get_json_values(json_field, json_value, self.regions,
                                           'regions', informea_id)
                for lang, regions in reg_dict.items():
                    solr_decision['{}_{}'.format(solr_field, lang)] = regions
            elif json_field in KEYWORD_FIELDS:
                kw_dict = get_json_values(json_field, json_value, self.keywords,
                                          'keywords', informea_id)
                for lang, keywords in kw_dict.items():
                    keywords = list(set(keywords))
                    solr_decision['{}_{}'.format(solr_field, lang)] = keywords
            elif json_field in SUBJECT_FIELDS:
                sbj_dict = get_json_values(json_field, json_value,
                                           self.subjects, 'subjects', informea_id)
                for lang, subjects in sbj_dict.items():
                    subjects = list(set(subjects))
                    solr_decision['{}_{}'.format(solr_field, lang)] = subjects
            else:
                solr_decision[solr_field] = get_value(json_field, json_value)

            if json_field in FULL_TEXT_FIELDS and json_value:
                # Abstract is a file, should no longer happen
                urls = [replace_url(d.get('url')) for val in json_value.values()
                        for d in val]
                files = [get_file_from_url(url) for url in urls if url]
                text = '\n'.join([
                    self.solr.extract(f) or ''
                    for f in files if f
                ])
                solr_decision['cdText'] += text

        # cdRegion fallback on field_ecolex_region
        if not solr_decision.get('cdRegion_en'):
            backup_field = 'field_ecolex_region'
            solr_field = 'cdRegion'
            json_value = self.data.get(backup_field, None)
            if json_value:
                reg_dict = get_json_values(backup_field, json_value,
                                           self.regions, 'regions', informea_id)
                for lang, regions in reg_dict.items():
                    solr_decision['{}_{}'.format(solr_field, lang)] = regions

        full_text_urls = solr_decision.get('cdLinkToFullText') or []
        if not full_text_urls and solr_decision.get('cdRelatedUrl_en'):
            url = solr_decision.pop('cdRelatedUrl_en')
            solr_decision['cdLinkToFullText'] = [url]
            full_text_urls.append(url)

        for url in full_text_urls:
            file_obj = get_file_from_url(url)
            if file_obj:
                text = self.solr.extract(file_obj) or ''
                solr_decision['cdText'] += '\n' + text

        # Get Leo URL
        for url_field in SOURCE_URL_FIELDS:
            json_value = self.data.get(url_field, None)
            solr_decision['cdLeoEnglishUrl'] = get_value(url_field, json_value)
            break

        title = (solr_decision.get('cdTitleOfText_en') or
                 solr_decision.get('cdTitleOfText_fr') or
                 solr_decision.get('cdTitleOfText_es') or
                 solr_decision.get('cdTitleOfText_other') or '')
        if not title:
            logger.warning('Title missing for {}'.format(informea_id))
        slug = '{} {}'.format(title, informea_id)
        solr_decision['slug'] = slugify(slug)
        solr_decision['updatedDate'] = (datetime.now()
                                        .strftime('%Y-%m-%dT%H:%M:%SZ'))

        if 'cdKeyword_en' not in solr_decision:
            solr_decision.update({
                'cdKeyword_{}'.format(lang): self.informea_tags(lang)
                for lang in LANGUAGES
            })

        return solr_decision


class CourtDecisionImporter(BaseImporter):

    id_field = 'cdOriginalId'

    def __init__(self, config):
        super().__init__(config, logger, COURT_DECISION)
        self.base_url = config.get('base_url')
        self.items_per_page = config.get('items_per_page', 10)
        self.start_page = config.get('start_page', 0)
        self.max_page = config.get('max_page', False)
        self.force_update = config.get('force_update', False)
        self.countries_json = config.get('countries_json')
        self.countries = self._get_countries()
        self.subdivisions = get_dict_from_json(config.get('subdivisions_json'))

        # When we need to import only one decision
        self.uuid = config.get('uuid')

    def harvest(self, batch_size):
        if self.uuid:
            logger.info('Adding court decision {}'.format(self.uuid))
            solr_decision = self.solr.search(COURT_DECISION, self.uuid)
            u = urlparse(self.base_url)
            node = {
                'uuid': self.uuid,
                'data_url': f'{u.scheme}://{u.netloc}/node/{self.uuid}/json',
            }
            self._add_decision(node, solr_decision)
            return

        logger.info('[court decision] Harvesting started.')
        page_num = self.start_page
        while (True):
            if self.max_page and page_num >= self.max_page:
                logger.info('Forced stop at max_page %s.', page_num)
                break

            decisions = request_page(self.base_url, self.items_per_page, page_num)
            page_num += 1
            if not decisions:
                break

            for node in decisions:
                # uuid, last_update, data_url
                uuid = node['uuid']
                solr_decision = self.solr.search(COURT_DECISION, uuid)
                if solr_decision:
                    # logger.debug('%s found in solr!', uuid)
                    solr_date = solr_decision['cdDateOfModification']
                    solr_update = datetime.strptime(solr_date, SOLR_DATE_FORMAT)
                    node_date = int(node['last_update'])
                    node_update = datetime.fromtimestamp(node_date)

                    if self.force_update:
                        logger.info('Forced update: %s', uuid)
                    elif node_update > solr_update:
                        logger.info('%s outdated, updating.', uuid)
                    else:
                        logger.debug('%s is up to date.', uuid)
                        continue
                else:
                    logger.info('%s not in solr, adding.', uuid)

                self._add_decision(node, solr_decision)

        logger.info('[court decision] Harvesting finished.')

    def _add_decision(self, node, solr_decision):

        data = request_json(node['data_url'])
        if type(data) is list:
            data = data[0]

        dec = CourtDecision(
            data,
            self.countries, self.languages,
            self.regions, self.subdivisions,
            self.keywords, self.informea_keywords,
            self.subjects, self.solr
        )
        solr_id = solr_decision['id'] if solr_decision else None
        solr_decision = dec.get_solr_format(node['uuid'], solr_id)

        try:
            if self.solr.add(solr_decision):
                logger.info('Solr succesfully updated!')
            else:
                logger.error('Error updating solr!')
        except JSONDecodeError:
            logger.error(f"Invalid JSON at {node['data_url']}")
        except Exception:
            logger.exception('Error updating solr!')
            raise

    def _get_countries(self):
        data = get_dict_from_json(self.countries_json)
        codes = data['code_corresp']
        countries = data['official_names']
        reverse_codes = {v: k for k, v in codes.items()}
        return {reverse_codes.get(k, k): v for k, v in countries.items()}
