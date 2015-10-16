from bs4 import BeautifulSoup
import pprint

from import_elis import valid_date, format_date
from utils import SolrWrapper

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

}

DATE_FIELDS = [
    'litDateOfEntry', 'litDateOfModification'
]

MULTIVALUED_FIELDS = [
    'litId', 'litAuthor', 'litCorpAuthor', 'litSubject', 'litSubject_fr',
    'litSubject_sp', 'litKeyword', 'litKeyword_fr', 'litKeyword_sp',
    'litContributor', 'litTypeOfText', 'litTypeOfText_sp', 'litTypeOfText_fr',
]


def fetch_literature():
    """ This function is temporary. It will be replaced with the actual
    data fetcher when we get access to the elis endpoint.
     """
    literatures = []
    bs = BeautifulSoup(open('literature2.xml', 'r', encoding='utf-8'))

    documents = bs.findAll(DOCUMENT)
    literatures.extend(documents)
    return literatures


def clean_text(text):
    if AUTHOR_START in text:
        text = text.replace(AUTHOR_START, '').replace(AUTHOR_SPACE, ' ')
    return text.strip()


def parse_literatures(raw_literatures):
    pp = pprint.PrettyPrinter(indent=4)
    literatures = []

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
        pp.pprint(data)
        literatures.append(data)
    return literatures


def literature_needs_update(old, new):
    return False


def add_literature(literatures):
    solr = SolrWrapper()
    new_literatures = []
    updated_literatures = []

    for literature in literatures:
        lit_id = literature['litId'][0]
        literature_result = solr.search_literature(lit_id)
        if literature_result:
            # CHECK AND UPDATE
            if literature_needs_update(literature_result, literature):
                literature['id'] = literature_result['id']
                updated_literatures.append(literature)
                print('Literature %s has been updated' % (lit_id,))
            else:
                print('Literature %s already indexed' % (lit_id,))
        else:
            new_literatures.append(literature)
            print('Added %s' % (lit_id,))
    solr.add_documents(new_literatures)
    solr.add_documents(updated_literatures)

if __name__ == '__main__':
    raw_literatures = fetch_literature()
    literatures = parse_literatures(raw_literatures)
    add_literature(literatures)
