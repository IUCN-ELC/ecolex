from datetime import datetime, timedelta
import json
import requests
from pathlib import Path

from utils import get_file_from_url, EcolexSolr

COURT_DECISIONS_URL = 'http://leo.informea.org/ws/court-decisions'
COUNTRIES_JSON = 'countries.json'
UPDATE_INTERVAL = 1  # expressed in hours
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
    'field_ecolex_tags': 'cdSubject',
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
    'field_ecolex_keywords': 'cdKeywords',
    'field_faolex_reference': 'cdFaolexReference',
    'field_instance': 'cdInstance',
    'field_official_publication': 'cdOfficialPublication',
    'field_region': 'cdRegion',
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
    'field_source_language',
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
CONTENT_FIELDS = ['field_url']
REFERENCE_FIELDS = ['field_treaty']


def get_content(url, headers={}):
    resp = requests.get(url, headers=headers)
    if not resp.status_code == 200:
        raise RuntimeError('Unexpected request status code')

    try:
        return json.loads(resp.text)
    except ValueError as ex:
        # TODO: replace this with logging
        print(url, ex)


def get_decision(url):
    headers = {'Accept': 'application/json'}
    return get_content(url, headers)


def get_decisions():
    return get_content(COURT_DECISIONS_URL)


def is_recent(decision):
    changed = datetime.fromtimestamp(float(decision['changed'] or '0'))
    last_update = datetime.now() - timedelta(hours=UPDATE_INTERVAL)
    return changed > last_update


def load_countries():
    json_path = Path(__file__).parent.absolute().joinpath(COUNTRIES_JSON)
    with json_path.open() as f:
        codes_countries = json.load(f)
    codes = codes_countries['code_corresp']
    countries = codes_countries['official_names']
    reverse_codes = {v: k for k, v in codes.items()}
    return {reverse_codes.get(k, k): v for k, v in countries.items()}


def get_country_value(value):
    if len(value) != 1:
        print('Unexpected value: {}!'.format(value))
        return {}
    country = countries.get(value[0], {})
    if not country:
        print('Country code {} not found!'.format(value))
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


def parse_decision(decision, leo_id, solr_id):
    solr_decision = {'text': ''}
    for json_field, solr_field in FIELD_MAP.items():
        json_value = decision.get(json_field, None)
        if not json_value:
            solr_decision[solr_field] = None
        elif json_field in FALSE_MULTILINGUAL_FIELDS:
            solr_decision[solr_field] = get_value(json_field, json_value['und'])
        elif json_field in MULTILINGUAL_FIELDS:
            for lang, value in json_value.items():
                key = '{}_{}'.format(solr_field, lang)
                solr_decision[key] = get_value(json_field, value)
        elif json_field in COUNTRY_FIELDS:
            country = get_country_value(json_value)
            for lang, value in country.items():
                key = '{}_{}'.format(solr_field, lang)
                solr_decision[key] = get_value(json_field, value)
        elif json_field in REFERENCE_FIELDS:
            solr_decision[solr_field] = json_value[0].get('uuid')
        else:
            solr_decision[solr_field] = get_value(json_field, json_value)

        if json_field in CONTENT_FIELDS and json_value:
            urls = [d.get('url') for val in json_value.values() for d in val]
            files = [get_file_from_url(url) for url in urls if url]
            solr_decision['text'] += '\n'.join(solr.extract(f) for f in files)

    solr_decision['type'] = 'court_decision'
    solr_decision['source'] = 'InforMEA'
    solr_decision['cdLeoId'] = leo_id
    solr_decision['id'] = solr_id
    return solr_decision


def update_decision(solr, decision):
    new_decision = get_decision(decision['data_url'])
    if not new_decision:
        return

    existing_decision = solr.search(solr.COURT_DECISION, decision['uuid'])
    if existing_decision and not is_recent(new_decision):
        return
    solr_id = existing_decision['id'] if existing_decision else None

    solr_decision = parse_decision(new_decision, decision['uuid'], solr_id)
    solr.add(solr_decision)


if __name__ == '__main__':
    solr = EcolexSolr()
    decisions = get_decisions()
    countries = load_countries()

    for decision in decisions:
        update_decision(solr, decision)
