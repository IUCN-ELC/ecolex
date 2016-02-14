import json
from bs4 import BeautifulSoup
from datetime import datetime
from collections import OrderedDict

from ecolex.management.utils import EcolexSolr
from ecolex.models import DocumentText

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

    'dateOfText': 'legDate',
    'dateOfOriginalText': 'legOriginalDate',
    'dateOfModification': 'legModificationDate',
    'dateOfConsolidation': 'legConsolidationDate',
    'dateOfEntry': 'legEntryDate',
    'searchDate': 'legSearchDate',

    'entryIntoForce': 'legEntryIntoForce',
    'country_ISO3': 'legCountry_iso',
    'country_en': 'legCountry_en',
    'country_fr': 'legCountry_fr',
    'country_es': 'legCountry_es',
    'territorialSubdivision_en': 'legTerritorialSubdivision',
    'geographicalArea_en': 'legGeoArea_en',
    'geographicalArea_fr': 'legGeoArea_fr',
    'geographicalArea_es': 'legGeoArea_es',

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
    'legImplement', 'legAmends', 'legRepeals',
    'legSubject_code', 'legSubject_en', 'legSubject_fr', 'legSubject_es',
]

DATE_FIELDS = [
    'legDate', 'legEntryDate', 'legSearchDate', 'legOriginalDate',
    'legModificationDate', 'legConsolidationDate',
]


def get_content(values):
    values = [v.get(CONTENT, None) for v in values]
    return values


def get_date_format(value):
    value = ' '.join([x for x in value.split() if not x.isupper()])
    date = datetime.strptime(value, '%a %b %d %H:%M:%S %Y')
    return date.strftime('%Y-%m-%dT%H:%M:%SZ')


def harvest_file(uploaded_file, logger):
    bs = BeautifulSoup(uploaded_file)
    documents = bs.findAll(DOCUMENT)
    legislations = []

    for document in documents:
        legislation = {
            'type': 'legislation',
            'source': 'fao',
        }

        for k, v in FIELD_MAP.items():
            field_values = get_content(document.findAll(META, {'name': k}))

            if field_values and v not in MULTIVALUED_FIELDS:
                field_values = field_values[0]

            if v in DATE_FIELDS and field_values:
                field_values = get_date_format(field_values)

            if field_values:
                legislation[v] = field_values

        #  remove duplicates
        for field_name in MULTIVALUED_FIELDS:
            field_values = legislation.get(field_name)
            if field_values:
                legislation[field_name] = list(OrderedDict.fromkeys(field_values).keys())

        url_value = document.attrs.get('url', None)
        if url_value:
            legislation['legLinkToFullText'] = url_value

        if (REPEALED.upper() in
                get_content(document.findAll(META, {'name': REPEALED}))):
            legislation['legStatus'] = REPEALED
        else:
            legislation['legStatus'] = IN_FORCE

        legislations.append(legislation)

    response = add_legislation(legislations, logger)
    return response


def legislation_needs_update(old, new, logger):
    if old['legModificationDate'] != new['legModificationDate']:
        return True
    return False


def add_legislation(legislations, logger):
    solr = EcolexSolr()
    new_docs = []
    updated_docs = []
    new_legislations = []
    updated_legislations = []
    already_indexed = 0

    for legislation in legislations:
        leg_id = legislation['legId']
        leg_result = solr.search('legislation', leg_id)
        if leg_result:
            if legislation_needs_update(leg_result, legislation, logger):
                legislation['updatedDate'] = (datetime.now()
                                              .strftime('%Y-%m-%dT%H:%M:%SZ'))
                updated_legislations.append(legislation)

                doc, _ = DocumentText.objects.get_or_create(doc_id=leg_id)
                doc.status = DocumentText.INDEXED
                doc.parsed_data = json.dumps(legislation)
                doc.url = legislation['legLinkToFullText']
                updated_docs.append(doc)
            else:
                already_indexed += 1
        else:
            new_legislations.append(legislation)
            doc = DocumentText(doc_id=leg_id,
                               url=legislation['legLinkToFullText'],
                               parsed_data=json.dumps(legislation),
                               status=DocumentText.INDEXED)
            new_docs.append(doc)

    result = solr.add_bulk(new_legislations)
    new_docs = index_is_failed(new_docs, result)

    result = solr.add_bulk(updated_legislations)
    updated_docs = index_is_failed(updated_docs, result)

    for doc in new_docs + updated_docs:
        doc.save()

    response = 'Total %d. Added %d. Updated %d. Already indexed %d' % (
        len(legislation),
        len(new_legislations),
        len(updated_legislations),
        already_indexed)
    return response


def index_is_failed(docs, index_result):
    if not index_result:
        for doc in docs:
            doc.status = DocumentText.INDEX_FAIL
    else:
        for doc in docs:
            doc.parsed_data = ''
    return docs
