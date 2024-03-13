from binascii import hexlify
from bs4 import BeautifulSoup
from datetime import datetime
import json
import html
import logging
import logging.config

from django.conf import settings
from django.db.utils import OperationalError
from django.template.defaultfilters import slugify
from pysolr import SolrError

from ecolex.management.commands.base import BaseImporter
from ecolex.management.commands.logging import LOG_DICT
from ecolex.management.definitions import LITERATURE
from ecolex.management.utils import format_date, valid_date, cleanup_copyfields
from ecolex.management.utils import (
    get_content_from_url,
    get_file_from_url,
    get_content_length_from_url,
    clean_text_date,
)
from ecolex.models import DocumentText

logging.config.dictConfig(LOG_DICT)
logger = logging.getLogger('literature_import')

TOTAL_DOCS = 'numberresultsfound'
PRESENTED_DOCS = 'numberresultspresented'
DOCUMENT = 'document'
AUTHOR_START = '^a'
AUTHOR_SPACE = '^b'

FIELD_MAP = {
    'id': 'litId',
    'id2': 'litId2',
    'otherDocId': 'litOtherDocId',
    'authorA': 'litAuthorA',
    'authorM': 'litAuthorM',
    'corpAuthorA': 'litCorpAuthorA',
    'corpAuthorM': 'litCorpAuthorM',
    'dateOfEntry': 'litDateOfEntry',
    'dateOfModification': 'litDateOfModification',

    'titleAbbreviation': 'litTitleAbbreviation',
    'titleOfText': 'litLongTitle_en',
    'titleOfTextFr': 'litLongTitle_fr',
    'titleOfTextSp': 'litLongTitle_es',
    'titleOfTextOther': 'litLongTitle_other',

    'paperTitleOfText': 'litPaperTitleOfText_en',
    'paperTitleOfTextFr': 'litPaperTitleOfText_fr',
    'paperTitleOfTextSp': 'litPaperTitleOfText_es',
    'paperTitleOfTextOther': 'litPaperTitleOfText_other',

    'titleOfTextShort': 'litTitleOfTextShort_en',
    'titleOfTextShortFr': 'litTitleOfTextShort_fr',
    'titleOfTextShortSp': 'litTitleOfTextShort_es',
    'titleOfTextShortOther': 'litTitleOfTextShort_other',

    'titleOfTextTransl': 'litTitleOfTextTransl_en',
    'titleOfTextTranslFr': 'litTitleOfTextTransl_fr',
    'titleOfTextTranslSp': 'litTitleOfTextTransl_es',

    'serialTitle': 'litSerialTitle',
    'isbn': 'litISBN',

    'publisher': 'litPublisher',
    'publPlace': 'litPublPlace',
    'volumeNo': 'litVolumeNo',
    'collation': 'litCollation',
    'dateOfText': 'litDateOfText',
    'yearOfText': 'litYearOfText',
    'linkToFullText': 'litLinkToFullText',
    'doi': 'litLinkDOI',
    'typeOfText': 'litTypeOfText_en',
    'typeOfText_fr_FR': 'litTypeOfText_fr',
    'typeOfText_es_ES': 'litTypeOfText_es',

    'languageOfDocument': 'litLanguageOfDocument_en',
    'subject': 'litSubject_en',
    'subject_fr_FR': 'litSubject_fr',
    'subject_es_ES': 'litSubject_es',

    'keyword': 'litKeyword_en',
    'keyword_fr_FR': 'litKeyword_fr',
    'keyword_es_ES': 'litKeyword_es',

    'scope': 'litScope_en',
    'scope_fr_FR': 'litScope_fr',
    'scope_es_ES': 'litScope_es',

    'intOrg': 'litIntOrg_en',
    'intOrg_fr_FR': 'litIntOrg_fr',
    'intOrg_es_ES': 'litIntOrg_es',

    'country': 'litCountry_en',
    'country_fr_FR': 'litCountry_fr',
    'country_es_ES': 'litCountry_es',
    'displayTitle': 'litDisplayTitle',
    'displayDetails': 'litDisplayDetails',
    'displayRegion': 'litDisplayRegion_en',
    'displayRegion_fr_FR': 'litDisplayRegion_fr',
    'displayRegion_es_ES': 'litDisplayRegion_es',

    'languageOfTranslation': 'litLanguageOfTranslation_en',
    'languageOfTranslation_fr_FR': 'litLanguageOfTranslation_fr',
    'languageOfTranslation_es_ES': 'litLanguageOfTranslation_es',

    'region': 'litRegion_en',
    'region_fr_FR': 'litRegion_fr',
    'region_es_ES': 'litRegion_es',

    'abstract': 'litAbstract_en',
    'abstractFr': 'litAbstract_fr',
    'abstractSp': 'litAbstract_es',
    'abstractOther': 'litAbstract_other',
    'linkToAbstract': 'litLinkToAbstract',

    'location': 'litLocation',
    'availableIn': 'litAvailableIn',
    'seriesFlag': 'litSeriesFlag',
    'serialStatus': 'litSerialStatus',
    'formerTitle': 'litFormerTitle',
    'modeOfAcquisition': 'litModeOfAcquisition',
    'frequency': 'litFrequency',
    'holdings': 'litHoldings',
    'searchDate': 'litSearchDate',

    'relatedWebSite': 'litRelatedWebSite',
    'contributor': 'litContributor',
    'issn': 'litISSN',

    'confName': 'litConfName_en',
    'confName_fr_FR': 'litConfName_fr',
    'confName_es_ES': 'litConfName_es',
    'confNameOther': 'litConfName_other',
    'confNo': 'litConfNo',
    'confPlace': 'litConfPlace',
    'confDate': 'litConfDate',

    'dateOfTextSer': 'litDateOfTextSer',
    'territorialSubdivision': 'litTerritorialSubdivision_en',
    'territorialSubdivision_fr_FR': 'litTerritorialSubdivision_fr',
    'territorialSubdivision_es_ES': 'litTerritorialSubdivision_es',
    'edition': 'litEdition',
    'callNo': 'litCallNo',
    'relatedMonograph': 'litRelatedMonograph',

    'basin': 'litBasin_en',
    'basin_fr_FR': 'litBasin_fr',
    'basin_es_ES': 'litBasin_es',

    'internetReference': 'litInternetReference',
    'referenceToTreaties': 'litTreatyReference',
    'referenceToCourtDecision': 'litCourtDecisionReference',
    'referenceToCourtDecisionInformea': 'litCourtDecisionReference2',
    'referenceToLiterature': 'litLiteratureReference',
    'referenceToFaolex': 'litFaolexReference',
    'referenceToEULegislation': 'litEULegislationReference',
    'referenceToNationalLegislation': 'litNationalLegislationReference',
    'informeaCOP': 'litCopDecisionReference',
    'chapter': 'litChapterReference',
    # Remember: all keys should be lowercase when using the html.parser
}

URL_FIELD = 'litLinkToFullText'

DATE_FIELDS = [
    'litDateOfEntry', 'litDateOfModification'
]

TEXT_DATE_FIELDS = ['litDateOfTextSer', 'litYearOfText', 'litDateOfText']

MULTIVALUED_FIELDS = [
    'litId2',
    'litAuthorM', 'litAuthorA', 'litCorpAuthorM', 'litCorpAuthorA',
    'litSubject_en', 'litSubject_fr', 'litSubject_es',
    'litKeyword_en', 'litKeyword_fr', 'litKeyword_es',
    'litContributor', 'litISBN',
    'litRegion_en', 'litRegion_fr', 'litRegion_es',
    'litBasin_en', 'litBasin_fr', 'litBasin_es',
    'litLanguageOfDocument_en',
    'litLinkToFullText',
    'litTypeOfText_en', 'litTypeOfText_fr', 'litTypeOfText_es',
    'litCountry_en', 'litCountry_fr', 'litCountry_es',
    'litTreatyReference', 'litCourtDecisionReference', 'litCourtDecisionReference2',
    'litLiteratureReference', 'litFaolexReference',
    'litNationalLegislationReference', 'litEULegislationReference',
    'litCopDecisionReference',
    'litChapterReference',
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

LANGUAGE_FIELD = 'litLanguageOfDocument_en'

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
        fields = ['litDateOfModification', 'litDateOfEntry']
        try:
            old_date = datetime.strptime(next(
                old_record[f] for f in fields if old_record.get(f)),
                self.date_format)
            new_date = datetime.strptime(next(
                self.data[f] for f in fields if self.data.get(f)),
                self.date_format)
        except (StopIteration, ValueError):
            logger.info('Update on %s' % (self.data[self.elis_id]))
            return True
        if old_date < new_date:
            logger.info('Update on %s' % (self.data[self.elis_id]))
            return True
        logger.info('No update on %s' % (self.data[self.elis_id]))
        return False

    def get_solr_format(self, elis_id, solr_id):
        if solr_id:
            self.data['id'] = solr_id
        return self.data


class LiteratureImporter(BaseImporter):

    id_field = 'litId'

    def __init__(self, config):
        super().__init__(config, logger, LITERATURE)

        self.literature_url = config.get('literature_url')
        self.query_format = config.get('query_format')
        self.query_filter = config.get('query_filter')
        self.query_export = config.get('query_export')
        self.query_skip = config.get('query_skip')
        self.query_type = config.get('query_type')
        self.per_page = config.get('per_page')
        now = datetime.now()
        self.start_year = config.get('start_year', now.year)
        self.end_year = config.get('end_year', now.year)
        self.start_month = config.get('start_month', now.month)
        self.end_month = config.get('end_month', now.month)
        if self.start_month == self.end_month and now.day == 1:
            self.start_month -= 1
        self.force_import_all = config.get('force_import_all', False)

    def harvest(self, batch_size):
        logger.info('[literature] Harvesting started.')
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
                presented_docs = int(bs.find('result').attrs[PRESENTED_DOCS])
                if (presented_docs < total_docs):
                    logger.error('Incomplete results for %d/%d (%d out of %d)' % (
                        month, year, presented_docs, total_docs)
                    )
                    total_docs = presented_docs
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
                        logger.debug('Getting next page (%s/%s)' %
                                     (skip, total_docs,))
                        content = get_content_from_url(url)
                        bs = BeautifulSoup(content)
                        if bs.find('error'):
                            logger.error(url)
                        raw_literatures.append(content)

            try:
                literatures = self._parse(raw_literatures)
                new_literatures = list(filter(bool, [self._get_solr_lit(lit) for
                                                     lit in literatures]))
                self._index_files(new_literatures)
                logger.debug('Adding literatures')
                self.solr.add_bulk(new_literatures)
                year -= 1
            except:
                logger.exception('Error updating records, retrying')

        logger.info('[Literature] Harvesting started.')

    def _parse(self, raw_literatures):
        literatures = []
        unique_ids = set([])
        for raw_lit in raw_literatures:
            bs = BeautifulSoup(raw_lit, 'xml')
            for doc in bs.findAll(DOCUMENT):
                data = {
                    'type': LITERATURE,
                    'litLanguageOfDocument_es': [],
                    'litLanguageOfDocument_fr': [],
                }

                for k, v in FIELD_MAP.items():
                    field_values = doc.findAll(k)
                    if (v in DATE_FIELDS and field_values and
                            valid_date(field_values[0].text)):
                        data[v] = format_date(
                            self._clean_text(field_values[0].text))
                    elif field_values:
                        clean_values = [self._clean_text(field.text)
                                        for field in field_values]
                        if v in data:
                            data[v].extend(clean_values)
                        else:
                            data[v] = clean_values
                        if v in data and v not in MULTIVALUED_FIELDS:
                            data[v] = data[v][0]

                id = data.get('litId')
                if id in unique_ids:
                    logger.warn('Skipping duplicate record id %s' % (id,))
                    continue
                unique_ids.add(id)

                if LANGUAGE_FIELD in data:
                    langs = data[LANGUAGE_FIELD]
                    data[LANGUAGE_FIELD] = []
                    for lang in langs:
                        key = lang.lower()
                        if key in self.languages:
                            data['litLanguageOfDocument_en'].append(self.languages[key]['en'])
                            data['litLanguageOfDocument_es'].append(self.languages[key]['es'])
                            data['litLanguageOfDocument_fr'].append(self.languages[key]['fr'])
                        else:
                            data['litLanguageOfDocument_en'].append(lang)
                            data['litLanguageOfDocument_es'].append(lang)
                            data['litLanguageOfDocument_fr'].append(lang)
                            logger.error('Language not found %s' % (lang))

                for field in TEXT_DATE_FIELDS:
                    if field in data:
                        data[field], temp_doc_date = clean_text_date(data[field])
                        if temp_doc_date and 'litDate' not in data:
                            data['litDate'] = temp_doc_date
                # litDateOfText parsing error log
                if 'litDateOfText' in data and ('litDate' not in data or
                                                not data['litDate']):
                    logger.error('Invalid date format (dateoftext) %s: %s' %
                                 (data['litId'], data['litDateOfText']))

                # Region, keyword, subject regularization from local dict
                self._set_values_from_dict(data, 'litRegion', self.regions)
                self._set_values_from_dict(data, 'litKeyword', self.keywords)
                self._set_values_from_dict(data, 'litSubject', self.subjects)

                # compute litDisplayType
                if id and 'V;' in id:
                    # Ignore unfinished records in ELIS, e.g. V;K1MON-079640
                    continue
                if id and id[:3] in DOCUMENT_TYPE_MAP:
                    for k, v in DOCUMENT_TYPE_MAP[id[:3]].items():
                        data[k] = v

                    if id[:3] == 'MON':
                        title = (data.get('litLongTitle_en') or
                                 data.get('litLongTitle_es') or
                                 data.get('litLongTitle_fr') or
                                 data.get('litLongTitle_other'))
                    else:
                        title = (data.get('litPaperTitleOfText_en') or
                                 data.get('litPaperTitleOfText_es') or
                                 data.get('litPaperTitleOfText_fr') or
                                 data.get('litPaperTitleOfText_other'))
                    if not title:
                        title = data.get('litId')
                    slug = title + ' ' + data.get('litId')
                    data['slug'] = slugify(slug)
                    data['updatedDate'] = (datetime.now()
                                           .strftime('%Y-%m-%dT%H:%M:%SZ'))

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
                        doc.text = self.solr.extract(file_obj) or ''
                        lit_text += doc.text
                        doc.status = DocumentText.FULL_INDEXED
                        doc.doc_size = file_obj.getbuffer().nbytes
                        try:
                            doc.save()
                            logger.info('Success extracting %s' % litId)
                        except OperationalError as e:
                            logger.error("DB insert error %s %s" % (litId, e))
                            doc.status = DocumentText.FULL_INDEX_FAIL
                            doc.text = None
                            doc.save()
                    else:
                        # Download failed
                        logger.error('Error on file download %s' % litId)
                        doc.status = DocumentText.INDEXED
                        doc.save()

            literature['litText'] = lit_text

    def update_full_text(self):
        logger.info('[Literature] Update full text started.')
        old_objs = []
        while True:
            count = (DocumentText.objects.filter(
                     status=DocumentText.INDEXED, doc_type=LITERATURE)
                     .exclude(url__isnull=True)).count()
            objs = (DocumentText.objects.filter(
                    status=DocumentText.INDEXED, doc_type=LITERATURE)
                    .exclude(url__isnull=True))[:100]
            if count == 0 or list(old_objs) == list(objs):
                break
            logger.info('%s records remaining' % (count,))
            for obj in objs:
                # Check if already parsed
                text = None
                if obj.doc_size and obj.text:
                    logger.info('Checking content length of %s (%s)' %
                                (obj.doc_id, obj.url,))
                    doc_size = get_content_length_from_url(obj.url)
                    if doc_size == obj.doc_size:
                        # File not changed, reuse obj.text
                        logger.debug('Not changed: %s' % (obj.url,))
                        text = obj.text
                # Download file
                if not text:
                    logger.info('Downloading: %s (%s)' % (obj.doc_id, obj.url,))
                    file_obj = get_file_from_url(obj.url)
                    if not file_obj:
                        logger.error('Failed downloading: %s' % (obj.url,))
                        continue
                    doc_size = file_obj.getbuffer().nbytes

                    # Extract text
                    logger.debug('Indexing: %s' % (obj.url,))
                    text = self.solr.extract(file_obj)
                    if not text:
                        logger.warn('Nothing to index for %s' % (obj.url,))
                # Load record and store text
                try:
                    literature = self.solr.search(LITERATURE, obj.doc_id)
                    if literature:
                        literature = cleanup_copyfields(literature)
                except SolrError as e:
                    logger.error('Error reading literature %s' % (obj.doc_id,))
                    if settings.DEBUG:
                        logging.getLogger('solr').exception(e)
                    continue

                if not literature:
                    logger.error('Failed to find literature %s' % (obj.doc_id))
                    continue

                literature['legText'] = text
                result = self.solr.add(literature)
                if result:
                    logger.info('Success download & indexed: %s' % (obj.doc_id,))
                    obj.status = DocumentText.FULL_INDEXED
                    obj.doc_size = doc_size
                    obj.text = text
                    try:
                        obj.save()
                    except OperationalError as e:
                        logger.error("DB insert error %s %s" % (obj.doc_id, e))
                        obj.status = DocumentText.FULL_INDEX_FAIL
                        obj.text = None
                        obj.save()
                else:
                    logger.error('Failed doc extract %s %s' % (obj.url,
                                                               literature['id']))
            old_objs = objs
        logger.info('[Literature] Update full text finished.')

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
        query_year = self.query_format % (year, month, year, month)
        query_hex = hexlify(str.encode(query_year)).decode()
        query = self.query_filter % (query_hex)
        page = self.query_skip % (skip)

        url = '%s%s%s%s%s' % (self.literature_url, self.query_export, query,
                              self.query_type, page)
        logger.info(url)
        return url

    def _get_languages(self):
        with open(self.languages_json, encoding='utf-8') as f:
            languages_codes = json.load(f)
        langs = {}
        for k, v in languages_codes.items():
            key = v['en'].lower()
            langs[key] = v
            if 'en2' in v:
                key = v['en2'].lower()
                langs[key] = v
        return langs
