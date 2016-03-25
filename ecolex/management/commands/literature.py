from binascii import hexlify
from bs4 import BeautifulSoup
from datetime import datetime
import json
import html
import logging
import logging.config
import re

from ecolex.management.commands.logging import LOG_DICT
from ecolex.management.utils import EcolexSolr, LITERATURE
from ecolex.management.utils import get_content_from_url, valid_date
from ecolex.management.utils import format_date, get_file_from_url
from ecolex.models import DocumentText

logging.config.dictConfig(LOG_DICT)
logger = logging.getLogger('literature_import')

TOTAL_DOCS = 'numberresultsfound'
DOCUMENT = 'document'
AUTHOR_START = '^a'
AUTHOR_SPACE = '^b'

FIELD_MAP = {
    'id': 'litId',
    'id2': 'litId2',
    'authora': 'litAuthorA',
    'authorm': 'litAuthorM',
    'corpauthora': 'litCorpAuthorA',
    'corpauthorm': 'litCorpAuthorM',
    'dateofentry': 'litDateOfEntry',
    'dateofmodification': 'litDateOfModification',

    'titleabbreviation': 'litTitleAbbreviation',
    'titleoftext': 'litLongTitle_en',
    'titleoftextfr': 'litLongTitle_fr',
    'titleoftextsp': 'litLongTitle_es',
    'titleoftextother': 'litLongTitle_other',

    'papertitleoftext': 'litPaperTitleOfText_en',
    'papertitleoftextfr': 'litPaperTitleOfText_fr',
    'papertitleoftextsp': 'litPaperTitleOfText_es',
    'papertitleoftextother': 'litPaperTitleOfText_other',

    'titleoftextshort': 'litTitleOfTextShort_en',
    'titleoftextshortfr': 'litTitleOfTextShort_fr',
    'titleoftextshortsp': 'litTitleOfTextShort_es',
    'titleoftextshortother': 'litTitleOfTextShort_other',

    'titleoftexttransl': 'litTitleOfTextTransl_en',
    'titleoftexttranslfr': 'litTitleOfTextTransl_fr',
    'titleoftexttranslsp': 'litTitleOfTextTransl_es',

    'serialtitle': 'litSerialTitle',
    'isbn': 'litISBN',
    'publisher': 'litPublisher',
    'publplace': 'litPublPlace',
    'volumeno': 'litVolumeNo',
    'collation': 'litCollation',
    'dateoftext': 'litDateOfText',
    'yearoftext': 'litYearOfText',
    'linktofulltext': 'litLinkToFullText',
    'doi': 'litLinkDOI',
    'typeoftext': 'litTypeOfText_en',
    'typeoftext_fr_fr': 'litTypeOfText_fr',
    'typeoftext_es_es': 'litTypeOfText_es',

    'languageofdocument': 'litLanguageOfDocument_en',
    'languageofdocument_fr_fr': 'litLanguageOfDocument_fr',
    'languageofdocument_es_es': 'litLanguageOfDocument_es',

    'subject': 'litSubject_en',
    'subject_fr_fr': 'litSubject_fr',
    'subject_es_es': 'litSubject_es',

    'keyword': 'litKeyword_en',
    'keyword_fr_fr': 'litKeyword_fr',
    'keyword_es_es': 'litKeyword_es',

    'scope': 'litScope_en',
    'scope_fr_fr': 'litScope_fr',
    'scope_es_es': 'litScope_es',

    'intorg': 'litIntOrg_en',
    'intorg_fr_fr': 'litIntOrg_fr',
    'intorg_es_es': 'litIntOrg_es',

    'country': 'litCountry_en',
    'country_fr_fr': 'litCountry_fr',
    'country_es_es': 'litCountry_es',
    'displaytitle': 'litDisplayTitle',
    'displaydetails': 'litDisplayDetails',
    'displayregion': 'litDisplayRegion_en',
    'displayregion_fr_fr': 'litDisplayRegion_fr',
    'displayregion_es_es': 'litDisplayRegion_es',

    'languageoftranslation': 'litLanguageOfTranslation_en',
    'languageoftranslation_fr_fr': 'litLanguageOfTranslation_fr',
    'languageoftranslation_es_es': 'litLanguageOfTranslation_es',

    'region': 'litRegion_en',
    'region_fr_fr': 'litRegion_fr',
    'region_es_es': 'litRegion_es',

    'abstract': 'litAbstract_en',
    'abstractfr': 'litAbstract_fr',
    'abstractsp': 'litAbstract_es',
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

    'confname': 'litConfName_en',
    'confname_fr_fr': 'litConfName_fr',
    'confname_es_es': 'litConfName_es',
    'confnameOther': 'litConfName_other',
    'confno': 'litConfNo',
    'confplace': 'litConfPlace',
    'confdate': 'litConfDate',

    'dateoftextser': 'litDateOfTextSer',
    'territorialsubdivision': 'litTerritorialSubdivision_en',
    'territorialsubdivision_fr_fr': 'litTerritorialSubdivision_fr',
    'territorialsubdivision_es_es': 'litTerritorialSubdivision_es',
    'edition': 'litEdition',
    'callno': 'litCallNo',
    'relatedmonograph': 'litRelatedMonograph',

    'basin': 'litBasin_en',
    'basin_fr_fr': 'litBasin_fr',
    'basin_es_es': 'litBasin_es',

    'internetreference': 'litInternetReference',
    'referencetotreaties': 'litTreatyReference',
    'referencetocourtdecision': 'litCourtDecisionReference',
    'referencetoliterature': 'litLiteratureReference',
    'referencetofaolex': 'litFaolexReference',
    'referencetoeulegislation': 'litEULegislationReference',
    'referencetonationallegislation': 'litNationalLegislationReference',

}

URL_FIELD = 'litLinkToFullText'

DATE_FIELDS = [
    'litDateOfEntry', 'litDateOfModification'
]

TEXT_DATE_FIELDS = ['litDateOfText']
SOLR_DATE_FORMAT = '%Y-%m-%dT%H:%M:%SZ'

MULTIVALUED_FIELDS = [
    'litId2',
    'litAuthorM', 'litAuthorA', 'litCorpAuthorM', 'litCorpAuthorA',
    'litSubject_en', 'litSubject_fr', 'litSubject_es',
    'litKeyword_en', 'litKeyword_fr', 'litKeyword_es',
    'litContributor', 'litISBN',
    'litRegion_en', 'litRegion_fr', 'litRegion_es',
    'litBasin_en', 'litBasin_fr', 'litBasin_es',
    'litLanguageOfDocument_en', 'litLanguageOfDocument_fr',
    'litLanguageOfDocument_es',
    'litLinkToFullText',
    'litTypeOfText_en', 'litTypeOfText_fr', 'litTypeOfText_es',
    'litCountry_en', 'litCountry_fr', 'litCountry_es',
]

DOCUMENT_TYPE_MAP = {
    'MON': {
        'litDisplayType_en': 'Monography/book',
        'litDisplayType_fr': 'Monographie/livre',
        'litDisplayType_es': 'Monografía/libro',
    },
    'ANA': {
        'litDisplayType_en': 'Article in periodical',
        'litDisplayType_fr': 'Article en publication périodique',
        'litDisplayType_es': 'Artículo en publicación',
    }
}

URL_CHANGE_FROM = 'http://www.ecolex.org/server2.php/server2neu.php/'
URL_CHANGE_TO = 'http://www.ecolex.org/server2neu.php/'
replace_url = lambda text: (URL_CHANGE_TO + text.split(URL_CHANGE_FROM)[-1]) if text.startswith(URL_CHANGE_FROM) else text


class Literature(object):

    def __init__(self, data, solr):
        self.data = data
        self.solr = solr
        self.date_format = '%Y-%m-%dT%H:%M:%SZ'

        # TODO not properly used below
        self.elis_id = 'litId'

    def is_modified(self, old_record):
        if 'litDateOfModification' in old_record:
            update_field = 'litDateOfModification'
        elif 'litDateOfEntry' in old_record:
            update_field = 'litDateOfEntry'
        else:
            return True
        if not self.data.get(update_field):
            logger.error('No modification date for %s' %
                         (self.data[self.elis_id]))
            return False
        old_date = datetime.strptime(old_record[update_field], self.date_format)
        new_date = datetime.strptime(self.data[update_field], self.date_format)

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
        self.regions_json = config.get('regions_json')
        self.literature_url = config.get('literature_url')
        self.import_field = config.get('import_field')
        self.query_format = config.get('query_format')
        self.query_filter = config.get('query_filter')
        self.query_export = config.get('query_export')
        self.query_skip = config.get('query_skip')
        self.query_type = config.get('query_type')
        self.per_page = config.getint('per_page')
        now = datetime.now()
        self.start_year = config.getint('start_year', now.year)
        self.end_year = config.getint('end_year', now.year)
        self.start_month = config.getint('start_month', now.month)
        self.end_month = config.getint('end_month', now.month)
        self.solr = EcolexSolr(self.solr_timeout)
        self.regions = self._get_regions()
        self.force_import_all = config.getboolean('force_import_all', False)
        logger.info('Started literature importer')

    def harvest(self, batch_size):
        total = 0
        year = self.end_year
        while year >= self.start_year:
            raw_literatures = []

            for month in range(self.start_month, self.end_month + 1):
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

            try:
                literatures = self._parse(raw_literatures)
                new_literatures = list(filter(bool, [self._get_solr_lit(lit) for
                                                     lit in literatures]))
                # self._index_files(new_literatures)
                logger.debug('Adding literatures')
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
                    if (v in DATE_FIELDS and field_values and
                            valid_date(field_values[0].text)):
                        data[v] = format_date(
                            self._clean_text(field_values[0].text))
                    elif v in TEXT_DATE_FIELDS and field_values:
                        value = self._clean_text(field_values[0].text)
                        data[v], data['docDate'] = self._clean_text_date(value)
                    elif field_values:
                        clean_values = [self._clean_text(field.text) for field in field_values]
                        if v in data:
                            data[v].extend(clean_values)
                        else:
                            data[v] = clean_values
                        if v in data and v not in MULTIVALUED_FIELDS:
                            data[v] = data[v][0]

                # Region regularization
                if 'litRegion_en' in data:
                    regions_en = data.get('litRegion_en')
                    regions_es = data.get('litRegion_es')
                    regions_fr = data.get('litRegion_fr')
                    regions = zip(regions_en, regions_es, regions_fr)
                    new_regions = {'en': [], 'es': [], 'fr': []}
                    for reg_en, reg_es, reg_fr in regions:
                        values = self.regions.get(reg_en.lower())
                        if values:
                            new_regions['en'].append(reg_en)
                            value_es = values['es']
                            value_fr = values['fr']
                            new_regions['es'].append(value_es)
                            new_regions['fr'].append(value_fr)

                            if value_es != reg_es:
                                logger.error('Region name error: %s %s %s' %
                                             (data['litId'], value_es,
                                              reg_es))

                            if value_fr != reg_fr:
                                logger.error('Region name error: %s %s %s' %
                                             (data['litId'], value_fr,
                                              reg_fr))
                        else:
                            logger.error('New region name: %s %s %s %s' %
                                         (data['litId'], reg_en, reg_es,
                                          reg_fr))
                            new_regions['en'].append(reg_en)
                            new_regions['es'].append(reg_es)
                            new_regions['fr'].append(reg_fr)
                    data['litRegion_en'] = new_regions['en']
                    data['litRegion_es'] = new_regions['es']
                    data['litRegion_fr'] = new_regions['fr']

                # litDateOfText parsing error log
                if 'litDateOfText' in data and ('docDate' not in data or
                                                not data['docDate']):
                    logger.error('Invalid date format (dateoftext) %s: %s' %
                                 (data['litId'], data['litDateOfText']))

                # compute litDisplayType
                id = data.get('litId')
                if id and 'V;' in id:
                    # Ignore unfinished records in ELIS, e.g. V;K1MON-079640
                    continue
                if id and id[:3] in DOCUMENT_TYPE_MAP:
                    for k, v in DOCUMENT_TYPE_MAP[id[:3]].items():
                        data[k] = v

                literatures.append(data)
        return literatures

    def _index_files(self, literatures):
        for literature in literatures:
            url_list = literature.get(URL_FIELD, [])
            litId = literature['litId']
            lit_text = ''
            if not url_list:
                # Nothing to download
                doc, _ = DocumentText.objects.get_or_create(
                    doc_id=litId, doc_type=LITERATURE, url=None)
                doc.status = DocumentText.INDEXED
                doc.save()

            for url in url_list:
                doc, _ = DocumentText.objects.get_or_create(
                    doc_id=litId, doc_type=LITERATURE, url=url)
                if doc.status == DocumentText.FULL_INDEXED:
                    lit_text += doc.text
                    logger.info('Already indexed %s' % url)
                else:
                    logger.info('Downloading: %s' % url)
                    file_obj = get_file_from_url(url)
                    if file_obj:
                        logger.debug('Success downloading: %s' % url)
                        doc.text = self.solr.extract(file_obj)
                        lit_text += doc.text
                        doc.status = DocumentText.FULL_INDEXED
                        doc.doc_size = file_obj.getbuffer().nbytes
                        doc.save()
                        logger.info('Success extracting %s' % litId)
                    else:
                        # Download failed
                        logger.error('Error on file download %s' % litId)
                        doc.status = DocumentText.INDEXED
                        doc.save()

            literature['litText'] = lit_text

    def _clean_text_date(self, value):
        date_formats = ['%Y', '%Y-00-00', '%Y-%m', '%Y-%m-00', '%Y-%m-%d',
                        '%Y%m00', '%Y%m%d']

        def parse(value, date_format):
            date = datetime.strptime(value, date_format)
            return value, date.strftime(SOLR_DATE_FORMAT)

        for date_format in date_formats:
            try:
                return parse(value, date_format)
            except ValueError:
                continue

        # Year range check
        regex = "(\d{4})-(\d{4})"
        matches = re.search(regex, value)
        if matches:
            start_year, _ = matches.groups(0)
            return parse(start_year, date_formats[0])

        return value, None

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
        if URL_CHANGE_FROM in text:
            # fix server2.php/server2neu.php in ['litLinkToFullText', 'litLinkToAbstract']
            return replace_url(text)
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

    def _get_regions(self):
        with open(self.regions_json) as f:
            regions = json.load(f)
        return regions
