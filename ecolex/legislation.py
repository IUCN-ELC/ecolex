import json
import logging
import logging.config
import tempfile
from bs4 import BeautifulSoup
from datetime import datetime
from collections import OrderedDict
from pysolr import SolrError

from django.conf import settings
from django.template.defaultfilters import slugify

from ecolex.management.commands.logging import LOG_DICT
from ecolex.management.utils import EcolexSolr, LEGISLATION
from ecolex.models import DocumentText

logging.config.dictConfig(LOG_DICT)
logger = logging.getLogger('legislation_import')

DOCUMENT = 'record'
META = 'meta'
CONTENT = 'content'
REPEALED = 'repealed'
IN_FORCE = 'in force'

FIELD_MAP = {
    'id': 'legId',
    'faolexId': 'legId',
    'titleOfText': 'legTitle',
    'longTitleOfText': 'legLongTitle',
    'serialImprint': 'legSource',

    'year': 'legYear',
    'originalYear': 'legOriginalYear',

    'entryIntoForce': 'legEntryIntoForce',
    'country_ISO3': 'legCountry_iso',
    'country_en': 'legCountry_en',
    'country_fr': 'legCountry_fr',
    'country_es': 'legCountry_es',
    'territorialSubdivision_en': 'legTerritorialSubdivision',
    'geographicalArea_en': 'legGeoArea_en',
    'geographicalArea_fr': 'legGeoArea_fr',
    'geographicalArea_es': 'legGeoArea_es',
    'basin_en': 'legBasin_en',
    'basin_fr': 'legBasin_fr',
    'basin_es': 'legBasin_es',

    'typeOfTextCode': 'legTypeCode',
    'typeOfText_en': 'legType_en',
    'typeOfText_fr': 'legType_fr',
    'typeOfText_es': 'legType_es',

    'relatedWebSite': 'legRelatedWebSite',
    'recordLanguage': 'legLanguage_code',
    'documentLanguage_en': 'legLanguage_en',
    'documentLanguage_fr': 'legLanguage_fr',
    'documentLanguage_es': 'legLanguage_es',

    'textAbstract': 'legAbstract',
    'abstract': 'legAbstract',
    'subjectSelectionCode': 'legSubject_code',
    'subjectSelection_en': 'legSubject_en',
    'subjectSelection_fr': 'legSubject_fr',
    'subjectSelection_es': 'legSubject_es',
    'keywordCode': 'legKeyword_code',
    'keyword_en': 'legKeyword_en',
    'keyword_fr': 'legKeyword_fr',
    'keyword_es': 'legKeyword_es',

    'implement': 'legImplement',
    'amends': 'legAmends',
    'repeals': 'legRepeals',

}

MULTIVALUED_FIELDS = [
    'legLanguage_en', 'legLanguage_fr', 'legLanguage_es',
    'legKeyword_code', 'legKeyword_en', 'legKeyword_fr', 'legKeyword_es',
    'legGeoArea_en', 'legGeoArea_fr', 'legGeoArea_es',
    'legBasin_en', 'legBasin_fr', 'legBasin_es',
    'legImplement', 'legAmends', 'legRepeals',
    'legSubject_code', 'legSubject_en', 'legSubject_fr', 'legSubject_es',
]

def get_content(values):
    values = [v.get(CONTENT, None) for v in values]
    return values

def harvest_file(uploaded_file):
    if settings.DEBUG:
        with tempfile.NamedTemporaryFile(prefix=uploaded_file.name, delete=False) as f:
            logger.debug('Dumping data to %s' %(f.name))
            for chunk in uploaded_file.chunks():
                f.write(chunk)
            uploaded_file.seek(0)

    bs = BeautifulSoup(uploaded_file)
    documents = bs.findAll(DOCUMENT)
    legislations = []

    with open('/ecolex/ecolex/management/regions.json') as f:
        json_regions = json.load(f)

    for document in documents:
        legislation = {
            'type': LEGISLATION,
            'source': 'fao',
        }

        for k, v in FIELD_MAP.items():
            field_values = get_content(document.findAll(META, {'name': k}))

            if field_values and v not in MULTIVALUED_FIELDS:
                field_values = field_values[0]

            # if v in DATE_FIELDS and field_values:
            #    field_values = get_date_format(field_values)

            if field_values:
                legislation[v] = field_values

        #  remove duplicates
        for field_name in MULTIVALUED_FIELDS:
            field_values = legislation.get(field_name)
            if field_values:
                legislation[field_name] = list(OrderedDict.fromkeys(field_values).keys())

        if ('legGeoArea_en' in legislation and
                'legGeoArea_es' in legislation and
                'legGeoArea_fr' in legislation):
            regions_en = legislation.get('legGeoArea_en')
            regions_es = legislation.get('legGeoArea_es')
            regions_fr = legislation.get('legGeoArea_fr')
            regions = zip(regions_en, regions_es, regions_fr)
            new_regions = {'en': [], 'es': [], 'fr': []}
            for reg_en, reg_es, reg_fr in regions:
                values = json_regions.get(reg_en.lower())
                if values:
                    new_regions['en'].append(values['en'])
                    value_es = values['es']
                    value_fr = values['fr']
                    new_regions['es'].append(value_es)
                    new_regions['fr'].append(value_fr)
                    if value_es.lower() != reg_es.lower():
                        logger.error('Region name error: %s %s %s' %
                                     (legislation['legId'], value_es,
                                      reg_es))

                    if value_fr.lower() != reg_fr.lower():
                        logger.error('Region name error: %s %s %s' %
                                     (legislation['legId'], value_fr,
                                      reg_fr))
                else:
                    logger.error('New region name: %s %s %s %s' %
                                 (legislation['legId'], reg_en, reg_es,
                                  reg_fr))
                    new_regions['en'].append(reg_en.capitalize())
                    new_regions['es'].append(reg_es.capitalize())
                    new_regions['fr'].append(reg_fr.capitalize())
            legislation['legGeoArea_en'] = new_regions['en']
            legislation['legGeoArea_es'] = new_regions['es']
            legislation['legGeoArea_fr'] = new_regions['fr']

        legYear = legislation.get('legYear')
        if legYear:
            try:
                legDate = datetime.strptime(legYear, '%Y')
                legislation['docDate'] = legDate.strftime('%Y-%m-%dT%H:%M:%SZ')
            except Exception as e:
                logger.debug('Error parsing legYear %s' % (legYear))
                pass

        url_value = document.attrs.get('url', None)
        if url_value:
            legislation['legLinkToFullText'] = url_value

        if (REPEALED.upper() in
                get_content(document.findAll(META, {'name': REPEALED}))):
            legislation['legStatus'] = REPEALED
        else:
            legislation['legStatus'] = IN_FORCE

        title = legislation.get('legTitle') or legislation.get('legLongTitle')
        slug = title + ' ' + legislation.get('legId')
        legislation['slug'] = slugify(slug)

        legislations.append(legislation)

    response = add_legislations(legislations)
    return response

def add_legislations(legislations):
    solr = EcolexSolr()
    new_docs = []
    updated_docs = []
    new_legislations = []
    updated_legislations = []
    failed_docs = []

    for legislation in legislations:
        leg_id = legislation['legId']
        doc, _ = DocumentText.objects.get_or_create(doc_id=leg_id)
        doc.doc_type = LEGISLATION
        doc.status = DocumentText.INDEX_FAIL
        try:
            leg_result = solr.search(LEGISLATION, leg_id)
            if leg_result:
                legislation['updatedDate'] = (datetime.now()
                                              .strftime('%Y-%m-%dT%H:%M:%SZ'))
                legislation['id'] = leg_result['id']
                updated_legislations.append(legislation)
                updated_docs.append(doc)
            else:
                new_legislations.append(legislation)
                new_docs.append(doc)
        except SolrError as e:
            logger.error('Error importing legislation %s' % (leg_id,) )
            failed_docs.append(doc)
            if settings.DEBUG:
                logger.exception(e)

        doc.parsed_data=json.dumps(legislation)
        if ( doc.url != legislation['legLinkToFullText']):
            doc.url=legislation['legLinkToFullText']
            # will not re-parse if same url and doc_size
            doc.doc_size = None

    # Mix of exceptions and True/False return status
    # hoping that add_bulk has better performance than add
    count_new = index_and_log(solr, new_legislations, new_docs)
    count_updated = index_and_log(solr, updated_legislations, updated_docs)
    for doc in new_docs + updated_docs + failed_docs:
        doc.save()

    response = 'Total %d. Added %d. Updated %d. Failed %d.' % (
        len(legislations),
        count_new,
        count_updated,
        len(legislations)-count_new-count_updated
    )
    return response

def index_and_log(solr, legislations, docs):
    # solr.add_bulk returns False on fail
    if not solr.add_bulk(legislations):
        return 0
    for doc in docs:
        doc.status = DocumentText.INDEXED
        # no need to store what is already indexed in Solr
        doc.parsed_data = ''
    return len(legislations)

