from binascii import hexlify
from bs4 import BeautifulSoup
from datetime import datetime
import html
import logging
import logging.config

from ecolex.management.commands.logging import LOG_DICT
from ecolex.management.utils import EcolexSolr, LITERATURE
from ecolex.management.utils import get_content_from_url, valid_date
from ecolex.management.utils import format_date, get_file_from_url

logging.config.dictConfig(LOG_DICT)
logger = logging.getLogger('import')

TOTAL_DOCS = 'numberresultsfound'
DOCUMENT = 'document'
AUTHOR_START = '^a'
AUTHOR_SPACE = '^b'

FIELD_MAP = {
    'id': 'litId',
    'id2': 'litId2',
    'authora': 'litAuthorArticle',
    'authorm': 'litAuthor',
    'corpauthora': 'litCorpAuthorArticle',
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
    'doi': 'litLinkDOI',
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
    'litId2',
    'litAuthor', 'litCorpAuthor', 'litAuthorArticle', 'litCorpAuthorArticle',
    'litSubject', 'litSubject_fr', 'litSubject_sp',
    'litKeyword', 'litKeyword_fr', 'litKeyword_sp',
    'litContributor',
    'litTypeOfText', 'litTypeOfText_sp', 'litTypeOfText_fr',
    'litCountry', 'litCountry_sp', 'litCountry_fr',
]


class Literature(object):

    def __init__(self, data, solr):
        self.data = data
        self.solr = solr
        self.date_format = '%Y-%m-%dT%H:%M:%SZ'
        self.elis_id = 'litId'

    def is_modified(self, old_record):
        if 'litDateOfModification' in old_record:
            update_field = 'litDateOfModification'
        elif 'litDateOfEntry' in old_record:
            update_field = 'litDateOfEntry'
        else:
            return True
        old_date = datetime.strptime(old_record[update_field], self.date_format)
        new_date = datetime.strptime(self.data[update_field],self.date_format)

        if old_date < new_date:
            logger.info('Update on %s' % (self.data[self.elis_id]))
            return True
        logger.info('No update on %s' % (self.data[self.elis_id]))
        return False

    def get_solr_format(self, elis_id, solr_id):
        if solr_id:
            self.data['id'] = solr_id
        return self.data


class LiteratureImporter(object):

    def __init__(self, config):
        self.solr_timeout = config.getint('solr_timeout')
        self.literature_url = config.get('literature_url')
        self.import_field = config.get('import_field')
        self.query_format = config.get('query_format')
        self.query_filter = config.get('query_filter')
        self.query_export = config.get('query_export')
        self.query_skip = config.get('query_skip')
        self.query_type = config.get('query_type')
        self.per_page = config.getint('per_page')
        self.start_year = config.getint('start_year')
        now = datetime.now()
        self.end_year = config.getint('end_year', now.year)
        self.start_month = config.getint('start_month', now.month)
        self.end_month = config.getint('end_month', now.month)
        self.solr = EcolexSolr(self.solr_timeout)
        self.force_import_all = config.getboolean('force_import_all', False)
        logger.info('Started literature importer')

    def harvest(self, batch_size):
        total = 0
        year = self.end_year
        while year >= self.start_year:
            raw_literatures = []

            for month in range(self.start_month, self.end_month+1):
                skip = 0
                url = self._create_url(year, month, skip)
                content = get_content_from_url(url)
                bs = BeautifulSoup(content)
                if bs.find('error'):
                    logger.info('For %d/%d found 0 literatures' % (month, year))
                    continue

                total_docs = int(bs.find('result').attrs[TOTAL_DOCS])
                total += total_docs
                found_docs = len(bs.findAll(DOCUMENT))
                raw_literatures.append(content)
                logger.info(url)
                logger.info('For %d/%d found %d literatures' %
                            (month, year, total_docs))
                if total_docs > found_docs:
                    while skip < total_docs - found_docs:
                        skip += found_docs
                        url = self._create_url(year, month, skip)
                        content = get_content_from_url(url)
                        bs = BeautifulSoup(content)
                        if bs.find('error'):
                            logger.error(url)
                        raw_literatures.append(content)

            literatures = self._parse(raw_literatures)
            new_literatures = filter(bool, [self._get_solr_lit(lit) for
                                     lit in literatures])
            try:
                self.solr.add_bulk(new_literatures)
                year -= 1
            except:
                logger.exception('Error updating records, retrying')

        logger.info('Finished harvesting literatures')

    def _parse(self, raw_literatures):
        literatures = []
        for raw_lit in raw_literatures:
            bs = BeautifulSoup(raw_lit)
            for doc in bs.findAll(DOCUMENT):
                data = {'type': LITERATURE}

                for k, v in FIELD_MAP.items():
                    field_values = doc.findAll(k)
                    if (v in DATE_FIELDS and field_values
                            and valid_date(field_values[0].text)):
                        data[v] = format_date(
                            self._clean_text(field_values[0].text))
                    elif field_values:
                        if v in data:
                            data[v].extend([self._clean_text(field.text) for
                                           field in field_values])
                        else:
                            data[v] = [self._clean_text(field.text) for
                                       field in field_values]
                        if v in data and v not in MULTIVALUED_FIELDS:
                            data[v] = data[v][0]

                # fix server2.php/server2neu.php in full text links
                field_names = ['litLinkToFullText', 'litLinkToAbstract']
                change_from = 'http://www.ecolex.org/server2.php/server2neu.php/'
                change_to = 'http://www.ecolex.org/server2neu.php/'
                for field_name in field_names:
                    if data.get(field_name) and data[field_name].startswith(change_from):
                        data[field_name] = change_to + data[field_name].split(change_from)[-1]

                value = doc.find(URL_FIELD)
                if value:
                    file_obj = get_file_from_url(value.text)
                    data['text'] = self.solr.extract(file_obj)
                literatures.append(data)
        return literatures

    def _get_solr_lit(self, lit_data):
        new_lit = Literature(lit_data, self.solr)
        existing_lit = self.solr.search(LITERATURE, lit_data['litId'])
        if self.force_import_all or not existing_lit:
            logger.info('Importing new record %s' % (lit_data['litId']))
        elif not new_lit.is_modified(existing_lit):
            return None
        solr_id = existing_lit['id'] if existing_lit else None
        return new_lit.get_solr_format(lit_data['litId'], solr_id)

    def _clean_text(self, text):
        if AUTHOR_START in text:
            text = text.replace(AUTHOR_START, '').replace(AUTHOR_SPACE, ' ')
        return html.unescape(text.strip())

    def _create_url(self, year, month, skip):
        query_year = self.query_format % (year, month)
        query_hex = hexlify(str.encode(query_year)).decode()
        query = self.query_filter % (query_hex)
        page = self.query_skip % (skip)

        url = '%s%s%s%s%s' % (self.literature_url, self.query_export, query,
                              self.query_type, page)
        return url
