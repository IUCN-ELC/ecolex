import json
import logging
import logging.config
import tempfile
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from collections import OrderedDict
from pysolr import SolrError

from django.conf import settings
from django.utils import timezone
from django.template.defaultfilters import slugify

from ecolex.management.commands.logging import LOG_DICT
from ecolex.management.commands.legislation import LegislationImporter
from ecolex.management.definitions import LEGISLATION
from ecolex.management.utils import EcolexSolr
from ecolex.models import DocumentText

logging.config.dictConfig(LOG_DICT)
logger = logging.getLogger('legislation_import')

DOCUMENT = 'document'
REPEALED = 'repealed'
IN_FORCE = 'in force'

FIELD_MAP = {
    'id': 'legId',
    'FaolexId': 'legId',
    'Title_of_Text': 'legTitle',
    'Long_Title_of_text': 'legLongTitle',
    'Serial_Imprint': 'legSource',

    'Date_of_Text': 'legDate',

    'Entry_into_Force': 'legEntryIntoForce',
    'country_ISO': 'legCountry_iso',
    'Territorial_Subdivision': 'legTerritorialSubdivision',
    'Sub_file_code': 'legSubject_code',
    'basin_en': 'legBasin_en',
    'basin_fr': 'legBasin_fr',
    'basin_es': 'legBasin_es',

    'Type_of_Text': 'legTypeCode',

    'Related_Web_Site': 'legRelatedWebSite',
    'Record_Language': 'legLanguage_code',
    'Doc_Language': 'legLanguage_en',

    'Abstract': 'legAbstract',
    'mainClassifyingKeyword': 'legMainKeyword_code',
    'keyword': 'legKeyword_code',

    'implements': 'legImplement',
    'amends': 'legAmends',
    'repeals': 'legRepeals',

    'implementsTre': 'legImplementTreaty',
    'citesTre': 'legCitesTreaty',
}

MULTIVALUED_FIELDS = [
    'legLanguage_en',
    'legKeyword_code',
    'legBasin_en', 'legBasin_fr', 'legBasin_es',
    'legImplement', 'legAmends', 'legRepeals', 'legImplementTreaty',
    'legCitesTreaty',
    'legSubject_code',
]

LANGUAGE_FIELDS = ['legLanguage_en', 'legLanguage_fr', 'legLanguage_es']


def get_content(values):
    values = [v.string for v in values]
    return values


def harvest_file(upfile):
    bs = BeautifulSoup(upfile, 'xml')
    documents = bs.findAll(DOCUMENT)
    legislations = []
    count_ignored = 0

    with open(settings.SOLR_IMPORT['common']['subjects_xml'], encoding='utf-8') as f:
        bs = BeautifulSoup(f.read(), 'xml')
        subjects = {subject.Classification_Sec_Area.string: subject
                    for subject in bs.findAll('dictionary_term')}

    with open(settings.SOLR_IMPORT['common']['keywords_xml'], encoding='utf-8') as f:
        bs = BeautifulSoup(f.read(), 'xml')
        keywords = {keyword.Code.string: keyword for keyword in bs.findAll('dictionary_term')}

    with open(settings.SOLR_IMPORT['common']['leg_regions_json'], encoding='utf-8') as f:
        json_regions = json.load(f)

    with open(settings.SOLR_IMPORT['common']['fao_countries_json'], encoding='utf-8') as f:
        json_countries = json.load(f)

    with open(settings.SOLR_IMPORT['common']['languages_json'], encoding='utf-8') as f:
        languages_codes = json.load(f)

    all_languages = {}
    for k, v in languages_codes.items():
        key = v['en'].lower()
        all_languages[key] = v
        if 'en2' in v:
            key = v['en2'].lower()
            all_languages[key] = v

    for document in documents:
        legislation = {
            'type': LEGISLATION,
            'legLanguage_es': set(),
            'legLanguage_fr': set(),
            'legKeyword_en': [],
            'legKeyword_fr': [],
            'legKeyword_es': [],
            'legSubject_en': [],
            'legSubject_fr': [],
            'legSubject_es': [],
        }

        for k, v in FIELD_MAP.items():
            field_values = get_content(document.findAll(k))

            if field_values and v not in MULTIVALUED_FIELDS:
                field_values = field_values[0]

            if field_values:
                if v == 'legKeyword_code':
                    if ('legMainKeyword_code' in legislation and
                            'legMainKeyword_code' in field_values):
                        field_values.insert(0, field_values.pop(
                                field_values.index(legislation.get('legMainKeyword_code'))))
                        del legislation['legMainKeyword_code']
                legislation[v] = field_values

        #  remove duplicates
        for field_name in MULTIVALUED_FIELDS:
            field_values = legislation.get(field_name)
            if field_values:
                legislation[field_name] = list(
                    OrderedDict.fromkeys(field_values).keys())

        langs = legislation.get('legLanguage_en', [])
        legislation['legLanguage_en'] = set()
        for lang in langs:
            key = lang.lower()
            if key in all_languages:
                for lang_field in LANGUAGE_FIELDS:
                    legislation[lang_field].add(all_languages[key][lang_field[-2:]])
            else:
                for lang_field in LANGUAGE_FIELDS:
                    legislation[lang_field].add(lang)
                logger.error(f'Language not found {lang}')

        for lang_field in LANGUAGE_FIELDS:
            legislation[lang_field] = list(legislation[lang_field])

        if 'legTypeCode' in legislation:
            if legislation['legTypeCode'] == 'A':
                # Ignore International agreements
                logger.debug(f"Ignoring {legislation.get('legId')}")
                count_ignored += 1
                continue

        _set_values_from_dict2(legislation, 'legSubject_', subjects)
        _set_values_from_dict2(legislation, 'legKeyword_', keywords)

        # overwrite countries with names from the dictionary
        iso_country = legislation.get('legCountry_iso')
        if iso_country:
            fao_country = json_countries.get(iso_country)
            if fao_country:
                legislation['legCountry_en'] = fao_country.get('en')
                legislation['legCountry_es'] = fao_country.get('es')
                legislation['legCountry_fr'] = fao_country.get('fr')

                region = json_regions.get(fao_country.get('en'))
                if region:
                    legislation['legGeoArea_en'] = region.get('en')
                    legislation['legGeoArea_fr'] = region.get('fr')
                    legislation['legGeoArea_es'] = region.get('es')

        if 'legDate' in legislation:
            try:
                legDate = datetime.strptime(legislation.get('legDate'), '%Y-%m-%d')
                legislation['legYear'] = legDate.strftime('%Y')
                legislation['legDate'] = legDate.strftime('%Y-%m-%dT%H:%M:%SZ')
            except Exception:
                logger.debug(f"Error parsing legDate {legislation['legDate']}")

        filenames = get_content(document.findAll('link_to_full_text'))
        url_values = []
        for filename in filenames:
            extension = filename.rsplit('.')[-1]
            url = settings.FULL_TEXT_URLS.get(extension.lower())
            if url:
                url_values.append(f'{url}{filename}')
            else:
                logger.error(f'URL not found for {extension.lower()}')

        if (REPEALED.upper() in
                get_content(document.findAll(REPEALED))):
            legislation['legStatus'] = REPEALED
        else:
            legislation['legStatus'] = IN_FORCE

        treaties = legislation.get('legImplementTreaty', [])
        cleaned_treaties = []
        for treaty in treaties:
            if treaty.endswith('.pdf'):
                treaty = treaty[:-4]
            cleaned_treaties.append(treaty)
        legislation['legImplementTreaty'] = cleaned_treaties

        title = legislation.get('legTitle') or legislation.get('legLongTitle')
        slug = title + ' ' + legislation.get('legId')
        legislation['slug'] = slugify(slug)

        for url_value in url_values:
            legislation_copy = legislation.copy()
            legislation_copy['legLinkToFullText'] = url_value
            legislations.append(legislation_copy)

    add_legislations(legislations, count_ignored)


def add_legislations(legislations, count_ignored):
    solr = EcolexSolr()
    new_docs = []
    updated_docs = []
    new_legislations = []
    updated_legislations = []
    failed_docs = []

    config = settings.SOLR_IMPORT
    importer_config = config['common']
    importer_config.update(config['legislation'])
    importer = LegislationImporter(importer_config)
    local_time = timezone.now()

    for legislation in legislations:
        leg_id = legislation.get('legId')
        docs = DocumentText.objects.filter(doc_id=leg_id,
                updated_datetime__lt=local_time).order_by('updated_datetime')

        if not docs:
            doc = DocumentText.objects.create(doc_id=leg_id)
        else:
            doc = docs[0]

        doc.doc_type = LEGISLATION
        legislation['updatedDate'] = (datetime.now()
                                      .strftime('%Y-%m-%dT%H:%M:%SZ'))
        try:
            leg_result = solr.search(LEGISLATION, leg_id)
            if leg_result:
                legislation['id'] = leg_result['id']
                updated_legislations.append(legislation)
                updated_docs.append(doc)
            else:
                new_legislations.append(legislation)
                new_docs.append(doc)
        except SolrError as e:
            logger.error(f'Error importing legislation {leg_id}')
            failed_docs.append(doc)
            if settings.DEBUG:
                logger.exception(e)

        doc.parsed_data = json.dumps(legislation)
        if (doc.url != legislation.get('legLinkToFullText')):
            doc.url = legislation.get('legLinkToFullText')
            # will not re-parse if same url and doc_size
            doc.doc_size = None
        doc.save()

    # Mix of exceptions and True/False return status
    # hoping that add_bulk has better performance than add
    count_new = index_and_log(solr, new_legislations, new_docs)
    count_updated = index_and_log(solr, updated_legislations, updated_docs)

    for doc in failed_docs:
        importer.reindex_failed(doc)

    logger.info(f'[Legislation] Update full text started.')
    for doc in new_docs + updated_docs + failed_docs:
        doc.save()
        importer.update_full_text(doc)
    logger.info(f'[Legislation] Update full text finished.')

    logger.info(f'Total {len(legislations) + count_ignored}. '
                f'Added {count_new}. Updated {count_updated}. '
                f'Failed {len(legislations) - count_new - count_updated}. '
                f'Ignored {count_ignored}')

def _set_values_from_dict2(data, field, local_dict):
    if (field + 'code') not in data:
        return

    for field_value in data[field + 'code']:
        if field_value in local_dict:
            data[field + 'en'].append(local_dict.get(field_value).Name_en_US.string)
            data[field + 'fr'].append(local_dict.get(field_value).Name_fr_FR.string)
            data[field + 'es'].append(local_dict.get(field_value).Name_es_ES.string)


def _set_values_from_dict(data, field, local_dict):
    id_field = 'legId'
    langs = ['en', 'fr', 'es']
    fields = ['{}_{}'.format(field, lang_code) for lang_code in langs]
    new_values = {x: [] for x in langs}
    if all(map((lambda x: x in data), fields)):
        values = zip(*[data[x] for x in fields])
        for val_en, val_fr, val_es in values:
            dict_values = local_dict.get(val_en.lower())
            if dict_values:
                new_values['en'].append(dict_values['en'])
                dict_value_fr = dict_values['fr']
                dict_value_es = dict_values['es']
                if val_fr != dict_value_fr:
                    logger.debug(f'{field}_fr name different: {data[id_field]} '
                                 f'{val_fr} {dict_value_fr}')
                new_values['fr'].append(dict_value_fr)
                if val_es != dict_value_es:
                    logger.debug(f'{field}_es name different: {data[id_field]} '
                                 f'{val_es} {dict_value_es}')
                new_values['es'].append(dict_value_es)
            else:
                logger.warning(f'New {field} name: {data[id_field]} {val_en} '
                               f'{val_fr} {val_es}')
                new_values['en'].append(val_en)
                new_values['fr'].append(val_fr)
                new_values['es'].append(val_es)
    elif fields[0] in data:
        values_en = data.get(fields[0], []) or []
        for val_en in values_en:
            dict_values = local_dict.get(val_en.lower())
            if dict_values:
                for lang in langs:
                    new_values[lang].append(dict_values[lang])
            else:
                logger.warning(f'New {field}_en name: {data[id_field]} {val_en}')
                new_values['en'].append(val_en)
    for field in fields:
        data[field] = new_values[field[-2:]]


def index_and_log(solr, legislations, docs):
    # solr.add_bulk returns False on fail
    faolex_enabled = getattr(settings, 'FAOLEX_ENABLED', False)
    if faolex_enabled:
        if not solr.add_bulk(legislations):
            return 0
        for doc in docs:
            # no need to store what is already indexed in Solr
            doc.parsed_data = ''
    return len(legislations)
