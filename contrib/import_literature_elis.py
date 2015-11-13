from bs4 import BeautifulSoup
import requests

from utils import EcolexSolr, valid_date, format_date, get_file_from_url

ELIS_URL = "http://ecolex.ecolex.org:8083/ecolex/ledge/view/ExportResult"
EXPORT = "?exportType=xml&index=literature"
FILTER = "searchDate_end=%d&searchDate_start=%d"
ORDER = "sortField=searchDate"
PAGE = "page=%d"

STOP_STRING = 'java.lang.NegativeArraySizeException'

DOCUMENT = 'document'

AUTHOR_START = '^a'
AUTHOR_SPACE = '^b'

FIELD_MAP = {
    'id': 'litId',
    'id2': 'litId',
    'authora': 'litAuthor',
    'authorm': 'litAuthor',
    'corpauthora': 'litCorpAuthor',
    'corpauthorm': 'litCorpAuthor',
    'dateofentry': 'litDateOfEntry',
    'dateofmodification': 'litDateOfModification',

    'titleabbreviation': 'litTitleAbbreviation',
    'titleoftext': 'litLongTitle',
    'titleoftextfr': 'litLongTitle_fr',
    'titleoftextsp': 'litLongTitle_sp',
    'titleoftextother': 'litLongTitle_other',

    'papertitleoftext': 'litPaperTitleOfText',
    'papertitleoftextfr': 'litPaperTitleOfText_fr',
    'papertitleoftextsp': 'litPaperTitleOfText_sp',
    'papertitleoftextother': 'litPaperTitleOfText_other',

    'titleoftextshort': 'litTitleOfTextShort',
    'titleoftextshortfr': 'litTitleOfTextShort_fr',
    'titleoftextshortsp': 'litTitleOfTextShort_sp',
    'titleoftextshortother': 'litTitleOfTextShort_other',

    'titleoftexttransl': 'litTitleOfTextTransl',
    'titleoftexttranslfr': 'litTitleOfTextTransl_fr',
    'titleoftexttranslsp': 'litTitleOfTextTransl_sp',

    'serialtitle': 'litSerialTitle',
    'isbn': 'litISBN',
    'publisher': 'litPublisher',
    'publplace': 'litPublPlace',
    'volumeno': 'litVolumeNo',
    'collation': 'litCollation',
    # TODO CLEAN dateoftext field
    'dateoftext': 'litDateOfText',
    'linktofulltext': 'litLinkToFullText',
    'typeoftext': 'litTypeOfText',
    'typeoftext_fr_fr': 'litTypeOfText_fr',
    'typeoftext_es_es': 'litTypeOfText_sp',

    'languageofdocument': 'litLanguageOfDocument',
    'languageofdocument_fr_fr': 'litLanguageOfDocument_fr',
    'languageofdocument_es_es': 'litLanguageOfDocument_sp',

    'subject': 'litSubject',
    'subject_fr_fr': 'litSubject_fr',
    'subject_es_es': 'litSubject_sp',

    'keyword': 'litKeyword',
    'keyword_fr_fr': 'litKeyword_fr',
    'keyword_es_es': 'litKeyword_sp',

    'scope': 'litScope',
    'scope_fr_fr': 'litScope_fr',
    'scope_es_es': 'litScope_sp',

    'intorg': 'litIntOrg',
    'intorg_fr_fr': 'litIntOrg_fr',
    'intorg_es_es': 'litIntOrg_sp',

    'country': 'litCountry',
    'country_fr_fr': 'litCountry_fr',
    'country_es_es': 'litCountry_sp',
    'displaytitle': 'litDisplayTitle',
    'displaydetails': 'litDisplayDetails',
    'displayregion': 'litDisplayRegion',
    'displayregion_fr_fr': 'litDisplayRegion_fr',
    'displayregion_es_es': 'litDisplayRegion_sp',

    'languageoftranslation': 'litLanguageOfTranslation',
    'languageoftranslation_fr_fr': 'litLanguageOfTranslation_fr',
    'languageoftranslation_es_es': 'litLanguageOfTranslation_sp',

    'region': 'litRegion',
    'region_fr_fr': 'litRegion_fr',
    'region_es_es': 'litRegion_sp',

    'abstract': 'litAbstract',
    'abstractfr': 'litAbstract_fr',
    'abstractsp': 'litAbstract_sp',
    'abstractother': 'litAbstract_other',
    'linktoabstract': 'litLinkToAbstract',

    'location': 'litLocation',
    'availablein': 'litAvailableIn',
    # TODO seriesFlag, serialStatus, formerTitle, modeOfAcquisition, frequency,
    # holdings, searchDate don't appear in xml files
    'seriesflag': 'litSeriesFlag',
    'serialstatus': 'litSerialStatus',
    'formertitle': 'litFormerTitle',
    'modeofacquisition': 'litModeOfAcquisition',
    'frequency': 'litFrequency',
    'holdings': 'litHoldings',
    'searchdate': 'litSearchDate',

    'relatedwebsite': 'litRelatedWebSite',
    'contributor': 'litContributor',
    'issn': 'litISSN',

    'confname': 'litConfName',
    'confname_fr_fr': 'litConfName_fr',
    'confname_es_es': 'litConfName_sp',
    'confnameOther': 'litConfName_other',
    'confno': 'litConfNo',
    'confplace': 'litConfPlace',
    'confdate': 'litConfDate',

    'dateoftextser': 'litDateOfTextSer',
    'territorialsubdivision': 'litTerritorialSubdivision',
    'territorialsubdivision_fr_fr': 'litTerritorialSubdivision_fr',
    'territorialsubdivision_es_es': 'litTerritorialSubdivision_sp',
    'edition': 'litEdition',
    'callno': 'litCallNo',
    'relatedmonograph': 'litRelatedMonograph',

    'basin': 'litBasin',
    'basin_fr_fr': 'litBasin_fr',
    'basin_es_es': 'litBasin_sp',

    'internetreference': 'litInternetReference',
    'referencetotreaties': 'litTreatyReference',
    'referencetocourtdecision': 'litCourtDecisionReference',
    'referencetoliterature': 'litLiteratureReference',
    'referencetofaolex': 'litFaolexReference',
    'referencetoeulegislation': 'litEULegislationReference',
    'referencetonationallegislation': 'litNationalLegislationReference',

}

URL_FIELD = 'linktofulltext'

DATE_FIELDS = [
    'litDateOfEntry', 'litDateOfModification'
]

MULTIVALUED_FIELDS = [
    'litId', 'litAuthor', 'litCorpAuthor', 'litSubject', 'litSubject_fr',
    'litSubject_sp', 'litKeyword', 'litKeyword_fr', 'litKeyword_sp',
    'litContributor', 'litTypeOfText', 'litTypeOfText_sp', 'litTypeOfText_fr',
]


def fetch_literature():
    year_filter = FILTER % (2016, 1500)
    page = 0
    literatures = []

    while True:
        print(page)
        page_filter = PAGE % (page,)
        query = '%s%s&%s&%s&%s' % (ELIS_URL, EXPORT, year_filter, ORDER,
                                   page_filter)
        response = requests.get(query)

        if response.status_code != 200:
            raise ValueError('Invalid return code %d' % response.status_code)

        if STOP_STRING in str(response.content):
            break

        bs = BeautifulSoup(response.content)
        documents = bs.findAll(DOCUMENT)
        literatures.extend(documents)

        page += 1

    return literatures


def clean_text(text):
    if AUTHOR_START in text:
        text = text.replace(AUTHOR_START, '').replace(AUTHOR_SPACE, ' ')
    return text.strip()


def parse_literatures(raw_literatures):
    literatures = []
    solr = EcolexSolr()

    for raw_literature in raw_literatures:
        data = {'type': 'literature'}

        for k, v in FIELD_MAP.items():
            field_values = raw_literature.findAll(k)
            if (v in DATE_FIELDS and field_values
                    and valid_date(field_values[0].text)):
                assert len(field_values) == 1
                data[v] = format_date(clean_text(field_values[0].text))
            elif field_values:
                if v in data:
                    data[v].extend([clean_text(field.text) for field in field_values])
                else:
                    data[v] = [clean_text(field.text) for field in field_values]
                if v in data and v not in MULTIVALUED_FIELDS:
                    data[v] = data[v][0]

        if 'litTypeOfText' in data and len(data['litTypeOfText']) > 1:
            data['litTypeOfText'] = ' '.join(data['litTypeOfText'])

        if 'litTypeOfText_fr' in data and len(data['litTypeOfText_fr']) > 1:
            data['litTypeOfText_fr'] = ' '.join(data['litTypeOfText_fr'])

        if 'litTypeOfText_sp' in data and len(data['litTypeOfText_sp']) > 1:
            data['litTypeOfText_sp'] = ' '.join(data['litTypeOfText_sp'])

        value = raw_literature.find(URL_FIELD)
        if value:
            url = value.text
            file_obj = get_file_from_url(url)
            data['text'] = solr.extract(file_obj)

        literatures.append(data)
    return literatures


def literature_needs_update(old, new):
    for field in FIELD_MAP.values():
        old_value = old.get(field, None)
        new_value = new.get(field, None)

        if (not old_value and new_value == '') or (new_value == [] and
           not old_value):
            continue

        if (isinstance(new_value, list) and isinstance(old_value, list) and
           set(old_value) == set(new_value)):
            continue

        if isinstance(new_value, list) and '' in new_value:
            new_value.remove('')

        if (old_value != new_value and [old_value] != new_value and
           [new_value] != old_value):
            return True
    return False


def add_literature(literatures):
    solr = EcolexSolr()
    new_literatures = []
    updated_literatures = []
    already_indexed = 0

    for literature in literatures:
        lit_id = literature['litId'][0]
        literature_result = solr.search('Literature', lit_id)
        if literature_result:
            # CHECK AND UPDATE
            if literature_needs_update(literature_result, literature):
                literature['id'] = literature_result['id']
                updated_literatures.append(literature)
                print('Literature %s has been updated' % (lit_id,))
            else:
                already_indexed += 1
                print('Literature %s already indexed' % (lit_id,))
        else:
            new_literatures.append(literature)
            print('Added %s' % (lit_id,))
    solr.add_bulk(new_literatures)
    solr.add_bulk(updated_literatures)
    print('Added %d new treaties' % (len(new_literatures)))
    print('Updated %d treaties' % (len(updated_literatures)))
    print('Already indexed treaties %d' % (already_indexed,))

if __name__ == '__main__':
    raw_literatures = fetch_literature()
    literatures = parse_literatures(raw_literatures)
    add_literature(literatures)
