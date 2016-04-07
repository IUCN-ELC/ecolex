from datetime import datetime, timedelta
import json
import logging
import logging.config

from django.template.defaultfilters import slugify

from ecolex.management.commands.logging import LOG_DICT
from ecolex.management.utils import EcolexSolr, get_json_from_url
from ecolex.management.utils import get_file_from_url
from ecolex.management.utils import COURT_DECISION

logging.config.dictConfig(LOG_DICT)
logger = logging.getLogger('import')

# TODO Harvest French and Spanish translations for the following fields:
#   - cdSubject  (the json field for this field is not multilingual)
#   - cdKeyword (the json field for this field is not multilingual)
#   - cdRegion (the json field for this field is not multilingual)

JSON_DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
SOLR_DATE_FORMAT = '%Y-%m-%dT%H:%M:%SZ'
FIELD_MAP = {
    'title_field': 'cdTitleOfText',
    'field_abstract': 'cdAbstract',
    'field_alternative_record_id': 'cdAlternativeRecordId',
    'field_city': 'cdSeatOfCourt',
    'field_country': 'cdCountry',
    'field_court_decision_id_number': 'cdCourtDecisionIdNumber',
    'field_court_decision_subdivision': 'cdCourtDecisionSubdivision',
    'field_court_name': 'cdCourtName',
    'field_date_of_entry': 'cdDateOfEntry',
    'field_date_of_modification': 'cdDateOfModification',
    'field_ecolex_decision_status': 'cdStatusOfDecision',
    'field_ecolex_tags': 'cdSubject_en',
    'field_ecolex_url': 'cdEcolexUrl',
    'field_faolex_url': 'cdFaolexUrl',
    'field_files': 'cdFiles',
    'field_informea_tags': 'cdInformeaTags',
    'field_internet_reference_url': 'cdInternetReference',
    'field_isis_number': 'cdIsisNumber',  # IsisMfn
    'field_jurisdiction': 'cdJurisdiction',
    'field_justices': 'cdJustices',
    'field_number_of_pages': 'cdNumberOfPages',
    'field_original_id': 'cdOriginalId',
    'field_reference_number': 'cdReferenceNumber',
    'field_reference_to_legislation': 'cdReferenceToLegislation',
    'field_related_url': 'cdRelatedUrl',  # relatedWebsite
    'field_source_language': 'cdLanguageOfDocument',
    'field_territorial_subdivision': 'cdTerritorialSubdivision',
    'field_type_of_text': 'cdTypeOfText',
    'field_url': 'cdLinkToFullText',
    'field_notes': 'cdNotes',
    'field_abstract_other': 'cdAbstractOther',
    'field_available_in': 'cdAvailableIn',
    'field_court_decision': 'cdCourtDecisionReference',
    'field_ecolex_keywords': 'cdKeyword_en',
    'field_faolex_reference': 'cdFaolexReference',
    'field_instance': 'cdInstance',
    'field_official_publication': 'cdOfficialPublication',
    'field_ecolex_region': 'cdRegion',
    'field_title_of_text_other': 'cdTitleOfTextOther',
    'field_title_of_text_short': 'cdTitleOfTextShort',
    'field_treaty': 'cdTreatyReference',
    'field_url_other': 'cdUrlOther',
    'field_sorting_date': 'cdDateOfText',
}
MULTILINGUAL_FIELDS = [
    'title_field',
    'field_abstract',
    'field_ecolex_url',
    'field_faolex_url',
    'field_internet_reference_url',
    'field_related_url',
    'field_city',
    'field_url',
]
FALSE_MULTILINGUAL_FIELDS = [
    'field_alternative_record_id',
    'field_court_name',
    'field_date_of_entry',
    'field_date_of_modification',
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
    'field_notes',
]
MULTIVALUED_FIELDS = [
    'field_justices',
    'field_ecolex_tags',
    'field_informea_tags',
    'field_ecolex_keywords',
    'field_notes',
]
DATE_FIELDS = [
    'field_date_of_entry',
    'field_date_of_modification',
    'field_sorting_date',
]
INTEGER_FIELDS = ['field_number_of_pages']
COUNTRY_FIELDS = ['field_country']
LANGUAGE_FIELDS = ['field_source_language']
REGION_FIELDS = ['field_ecolex_region']
FILES_FIELDS = ['field_files']
FULL_TEXT_FIELDS = ['field_url']
SUBDIVISION_FIELDS = ['field_territorial_subdivision']
REFERENCE_FIELDS = {'field_treaty': 'original_id',
                    'field_court_decision': 'uuid'}
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
                 solr):
        self.data = data
        self.countries = countries
        self.languages = languages
        self.regions = regions
        self.subdivisions = subdivisions
        self.solr = solr

    def is_recent(self, days_ago):
        changed = datetime.fromtimestamp(float(self.data['changed'] or '0'))
        last_update = datetime.now() - timedelta(hours=24*days_ago)
        return changed > last_update

    def get_solr_format(self, leo_id, solr_id):
        solr_decision = {
            'text': '',
            'type': COURT_DECISION,
            'source': 'InforMEA',
            'cdLeoId': leo_id,
            'id': solr_id,
        }
        for json_field, solr_field in FIELD_MAP.items():
            json_value = self.data.get(json_field, None)
            if not json_value:
                solr_decision[solr_field] = None
            elif json_field in FALSE_MULTILINGUAL_FIELDS:
                solr_decision[solr_field] = get_value(json_field,
                                                      json_value['und'])
            elif json_field in MULTILINGUAL_FIELDS:
                for lang, value in json_value.items():
                    key = '{}_{}'.format(solr_field, lang)
                    solr_decision[key] = get_value(json_field, value)
            elif json_field in COUNTRY_FIELDS:
                country = get_country_value(self.countries, json_value)
                for lang, value in country.items():
                    key = '{}_{}'.format(solr_field, lang)
                    solr_decision[key] = get_value(json_field, value)
            elif json_field in REFERENCE_FIELDS:
                solr_decision[solr_field] = [e.get(REFERENCE_FIELDS[json_field])
                                             for e in json_value]
            elif json_field in LANGUAGE_FIELDS:
                language_code = get_value(json_field, json_value['und'])
                languages = self.languages.get(language_code, language_code)
                for lang in LANGUAGES:
                    field = '{}_{}'.format(solr_field, lang)
                    solr_decision[field] = languages[lang]
            elif json_field in SUBDIVISION_FIELDS:
                subdivision_en = get_value(json_field, json_value)
                solr_decision[solr_field + '_en'] = subdivision_en
                values = self.subdivisions.get(subdivision_en, None)
                if values:
                    solr_decision[solr_field + '_es'] = values['Spanish']
                    solr_decision[solr_field + '_fr'] = values['French']
            elif json_field in REGION_FIELDS:
                region_en = get_value(json_field, json_value)
                solr_decision[solr_field + '_en'] = region_en
                values = self.regions.get(region_en.lower(), None)
                if values:
                    solr_decision[solr_field + '_es'] = values['es']
                    solr_decision[solr_field + '_fr'] = values['fr']
            else:
                solr_decision[solr_field] = get_value(json_field, json_value)

            if json_field in FILES_FIELDS and json_value:
                urls = [d.get('url') for d in json_value]
                files = [get_file_from_url(url) for url in urls if url]
                solr_decision['text'] += '\n'.join(self.solr.extract(f)
                                                   for f in files if f)

            if json_field in FULL_TEXT_FIELDS and json_value:
                urls = [d.get('url') for val in json_value.values()
                        for d in val]
                files = [get_file_from_url(url) for url in urls if url]
                solr_decision['text'] += '\n'.join(self.solr.extract(f)
                                                   for f in files if f)

        # Get faolex URL
        json_value = self.data.get(SOURCE_URL_FIELD, None)
        if json_value:
            solr_decision['cdFaoDefaultUrl'] = json_value.get('default', None)
            solr_decision['cdFaoEnglishUrl'] = json_value.get('en', None)

        title = (solr_decision.get('cdTitleOfText_en') or
                 solr_decision.get('cdTitleOfText_fr') or
                 solr_decision.get('cdTitleOfText_es'))
        slug = title + ' ' + solr_decision.get('cdLeoId')
        solr_decision['slug'] = slugify(slug)

        return solr_decision


class CourtDecisionImporter(object):
    def __init__(self, config):
        self.solr_timeout = config.getint('solr_timeout')
        self.days_ago = config.getint('days_ago')
        self.countries_json = config.get('countries_json')
        self.languages_json = config.get('languages_json')
        self.regions_json = config.get('regions_json')
        self.subdivisions_json = config.get('subdivisions_json')
        self.court_decisions_url = config.get('court_decisions_url')
        self.test_input_file = config.get('test_input_file')
        self.test_output_file = config.get('test_output_file')
        self.countries = self._get_countries()
        self.languages = self._get_languages()
        self.regions = self._get_regions()
        self.subdivisions = self._get_subdivisions()
        self.solr = EcolexSolr(self.solr_timeout)
        logger.info('Started Court Decision importer')

    def test(self):
        with open(self.test_input_file) as fi, open(self.test_output_file) as fo:
            init_decision = json.load(fi)
            expected_decision = json.load(fo)

        decision = CourtDecision(init_decision, self.countries, self.languages,
                                 self.solr)
        solr_decision = decision.get_solr_format(None, None)

        return solr_decision == expected_decision

    def harvest(self, batch_size):
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

    def _get_solr_decision(self, decision):
        data = self._get_decision(decision['data_url'])
        if not data:
            return
        new_decision = CourtDecision(data, self.countries, self.languages,
                                     self.regions, self.subdivisions,
                                     self.solr)

        existing_decision = self.solr.search(COURT_DECISION, decision['uuid'])
        if existing_decision and not new_decision.is_recent(self.days_ago):
            return
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
