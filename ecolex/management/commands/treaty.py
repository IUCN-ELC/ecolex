from binascii import hexlify
from bs4 import BeautifulSoup
from datetime import datetime
import logging
import logging.config
import html
import json

from django.conf import settings
from django.template.defaultfilters import slugify
from pysolr import SolrError

from ecolex.management.commands.base import BaseImporter
from ecolex.management.commands.logging import LOG_DICT
from ecolex.management.definitions import TREATY
from ecolex.management.utils import format_date, cleanup_copyfields
from ecolex.management.utils import get_content_from_url, get_file_from_url
from ecolex.models import DocumentText
from ecolex.search import get_documents_by_field

logging.config.dictConfig(LOG_DICT)
logger = logging.getLogger('treaty_import')

DOCUMENT = 'document'
TOTAL_DOCS = 'numberresultsfound'
PRESENTED_DOCS = 'numberresultspresented'
NULL_DATE = format_date('0000-00-00')
REMOTE_ID_FIELD = 'Recid'
B7 = 'International Environmental Law – Multilateral Agreements'
URL_CHANGE_FROM = 'http://www.ecolex.org/server2.php/server2neu.php/'
URL_CHANGE_TO = 'http://www.ecolex.org/server2neu.php/'
replace_url = lambda text: (URL_CHANGE_TO + text.split(URL_CHANGE_FROM)[-1]) if text.startswith(URL_CHANGE_FROM) else text

FIELD_MAP = {
    REMOTE_ID_FIELD: 'trElisId',
    'informeauid': 'trInformeaId',
    'dateOfEntry': 'trDateOfEntry',
    'dateOfModification': 'trDateOfModification',
    'dateOfText': 'trDateOfText',
    'dateOfText': 'trSearchDate',

    'titleOfText': 'trTitleOfText_en',
    'titleOfTextSp': 'trTitleOfText_es',
    'titleOfTextFr': 'trTitleOfText_fr',
    'titleOfTextOther': 'trTitleOfText_other',

    'typeOfText': 'trTypeOfText_en',
    'typeOfText_es_ES': 'trTypeOfText_es',
    'typeOfText_fr_FR': 'trTypeOfText_fr',

    'jurisdiction': 'trJurisdiction_en',
    'jurisdiction_es_ES': 'trJurisdiction_es',
    'jurisdiction_fr_FR': 'trJurisdiction_fr',

    'fieldOfApplication': 'trFieldOfApplication_en',
    'fieldOfApplication_fr_FR': 'trFieldOfApplication_fr',
    'fieldOfApplication_es_ES': 'trFieldOfApplication_es',

    'subject': 'trSubject_en',
    'subject_es_ES': 'trSubject_es',
    'subject_fr_FR': 'trSubject_fr',

    'languageOfDocument': 'trLanguageOfDocument_en',
    'obsolete': 'trObsolete',
    'enabledByTreaty': 'trEnabledByTreaty',
    'placeOfAdoption': 'trPlaceOfAdoption',

    'depository': 'trDepository_en',
    'depository_fr_FR': 'trDepository_fr',
    'depository_es_ES': 'trDepository_es',

    'entryIntoForceDate': 'trEntryIntoForceDate',
    'keyword': 'trKeyword_en',
    'keyword_es_ES': 'trKeyword_es',
    'keyword_fr_FR': 'trKeyword_fr',

    'abstract': 'trAbstract_en',
    'abstractEs': 'trAbstract_es',
    'abstractFr': 'trAbstract_fr',

    'comment': 'trComment',
    'titleOfTextShort': 'trTitleOfTextShort',
    'titleAbbreviation': 'trTitleAbbreviation',

    'basin': 'trBasin_en',
    'basin_fr_FR': 'trBasin_fr',
    'basin_es_ES': 'trBasin_es',

    'confName': 'trConfName',
    'courtName': 'trCourtName',
    'dateOfLastLegalAction': 'trDateOfLastLegalAction',

    'linkToFullText': 'trLinkToFullText_en',
    'linkToFullTextSp': 'trLinkToFullText_es',
    'linkToFullTextFr': 'trLinkToFullText_fr',
    'linkToFullTextOther': 'trLinkToFullText_other',
    'relatedWebSite': 'trRelatedWebSite',
    'linkToAbstract': 'trLinkToAbstract',

    'region': 'trRegion_en',
    'region_fr_FR': 'trRegion_fr',
    'region_es_ES': 'trRegion_es',
    'relevantTextTreaty': 'trRelevantTextTreaty',
    'searchDate': 'trSearchDate',
    'seatOfCourt': 'trSeatOfCourt',

    'supersedesTreaty': 'trSupersedesTreaty',
    'amendsTreaty': 'trAmendsTreaty',
    'citesTreaty': 'trCitesTreaty',

    'availableIn': 'trAvailableIn',
    'languageOfTranslation': 'trLanguageOfTranslation',
    'numberOfPages': 'trNumberOfPages',
    'officialPublication': 'trOfficialPublication',
    'internetReference': 'trInternetReference_en',
    'internetReferenceFr': 'trInternetReference_fr',
    'internetReferenceEs': 'trInternetReference_es',
    'internetReferenceOther': 'trInternetReference_other',

    'dateOfConsolidation': 'trDateOfConsolidation',
}

PARTICIPANT_FIELDS = {
    'country': 'partyCountry_en',
    'countryFr': 'partyCountry_fr',
    'countrySp': 'partyCountry_es',
    'entryIntoForce': 'partyEntryIntoForce',
    'dateofratification': 'partyDateOfRatification',
    'dateOfAccessionApprobation': 'partyDateOfAccessionApprobation',
    'dateOfAcceptanceApproval': 'partyDateOfAcceptanceApproval',
    'dateOfConsentToBeBound': 'partyDateOfConsentToBeBound',
    'dateOfSuccession': 'partyDateOfSuccession',
    'dateOfDefiniteSignature': 'partyDateOfDefiniteSignature',
    'dateOfSimpleSignature': 'partyDateOfSimpleSignature',
    'dateOfProvisionalApplication': 'partyDateOfProvisionalApplication',
    'dateOfParticipation': 'partyDateOfParticipation',
    'dateOfDeclaration': 'partyDateOfDeclaration',
    'dateOfReservation': 'partyDateOfReservation',
    'dateOfWithdrawal': 'partyDateOfWithdrawal',
}

LANGUAGE_FIELDS = [
    'trLanguageOfDocument_en',
]

DATE_FIELDS = [
    'trDateOfEntry',
    'trDateOfModification',
    'trDateOfText',
    'trSearchDate',
    'trEntryIntoForceDate',
    'trDateOfLastLegalAction',
    'trSearchDate',
    'trDateOfConsolidation',
    'partyEntryIntoForce',
    'partyDateOfRatification',
    'partyDateOfAccessionApprobation',
    'partyDateOfAcceptanceApproval',
    'partyDateOfConsentToBeBound',
    'partyDateOfSuccession',
    'partyDateOfDefiniteSignature',
    'partyDateOfSimpleSignature',
    'partyDateOfProvisionalApplication',
    'partyDateOfParticipation',
    'partyDateOfDeclaration',
    'partyDateOfReservation',
    'partyDateOfWithdrawal',
]

URL_FIELDS = [
    'linkToFullText', 'linkToFullTextSp', 'linkToFullTextFr',
    'linkToFullTextOther'
]

FALSE_LIST_FIELDS = [
    'trTypeOfText_en',
    'trTypeOfText_es',
    'trTypeOfText_fr',
    'trAvailableIn',
    'trPlaceOfAdoption',
    'trTitleOfTextShort',
    'trTitleOfText_en',
    'trTitleOfText_es',
    'trTitleOfText_fr',
    'trTitleOfText_other',
]


class Treaty(object):

    def __init__(self, data, solr):
        self.data = data
        self.solr = solr
        self.update_field = 'trDateOfModification'
        self.date_format = '%Y-%m-%dT%H:%M:%SZ'
        self.elis_id = 'trElisId'

    def is_modified(self, old_treaty):
        old_date = datetime.strptime(
            old_treaty[self.update_field],
            self.date_format
        ) if self.update_field in old_treaty else None

        new_date = datetime.strptime(self.data[self.update_field][0],
                                     self.date_format)
        if old_date and old_date < new_date:
            logger.info('Update on %s' % (self.data[self.elis_id]))
            return True
        logger.info('No update on %s' % (self.data[self.elis_id]))
        return False

    def get_solr_format(self, elis_id, solr_id):
        if solr_id:
            self.data['id'] = solr_id
        return self.data


class TreatyImporter(BaseImporter):
    id_field = 'trElisId'

    CUSTOM_RULES = [
        {
            'condition_field': 'trElisId',
            'condition_value': 'TRE-149349',
            'action_field': 'trDateOfText',
            'action_value': format_date('2009-10-02'),
        },
    ]

    def __init__(self, config):
        super().__init__(config, logger, TREATY)

        self.treaties_url = config.get('treaties_url')
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
            # TODO: When year changes (self.start_month == now.day == 1)

    def harvest(self, batch_size):
        logger.info('[Treaty] Harvesting started.')
        year = self.end_year
        while year >= self.start_year:
            raw_treaties = []

            for month in range(self.start_month, self.end_month + 1):
                skip = 0
                url = self._create_url(year, month, skip)
                content = get_content_from_url(url)
                bs = BeautifulSoup(content)
                if bs.find('error'):
                    logger.info('For %d/%d found 0 treaties' % (month, year))
                    continue

                result = bs.find('result')
                if result is None:
                    total_docs = 0
                else:
                    total_docs = int(result.attrs[TOTAL_DOCS])
                    presented_docs = int(result.attrs[PRESENTED_DOCS])
                    if (presented_docs < total_docs):
                        logger.error('Incomplete results for %d/%d (%d out of %d)' % (
                            month, year, presented_docs, total_docs))
                        total_docs = presented_docs
                found_docs = len(bs.findAll(DOCUMENT))
                raw_treaties.append(content)
                logger.info(url)
                logger.info('For: %d/%d found: %d treaties' %
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
                        raw_treaties.append(content)

            logger.debug('Parsing %d pages' % (len(raw_treaties)))
            treaties = self._parse(raw_treaties)
            logger.debug('Pre-processing %d treaties' % (len(treaties)))
            self._clean_referred_treaties(treaties)
            new_treaties = list(filter(bool, [self._get_solr_treaty(treaty) for
                                       treaty in treaties.values()]))
            self._index_files(new_treaties)
            logger.debug('Adding treaties')
            try:
                self.solr.add_bulk(new_treaties)
                year -= 1
            except:
                logger.exception('Error updating records, retrying')

        logger.info('[Treaty] Harvesting finished.')

    def _parse(self, raw_treaties):
        treaties = {}
        for raw_treaty in raw_treaties:
            bs = BeautifulSoup(raw_treaty, 'xml')
            for document in bs.findAll(DOCUMENT):
                data = {
                    'type': TREATY,
                    'trLanguageOfDocument_es': [],
                    'trLanguageOfDocument_fr': [],
                }
                elis_id = document.find(REMOTE_ID_FIELD).text
                for k, v in FIELD_MAP.items():
                    field_values = document.findAll(k)
                    if field_values:
                        data[v] = [self._clean_text(f.text) for
                                   f in field_values]
                        if v in DATE_FIELDS:
                            data[v] = [self._repair_date(x) for x in data[v]]
                            data[v] = [format_date(date) for date in data[v]
                                       if self._valid_date(date)]
                        elif v in LANGUAGE_FIELDS:
                            langs = data[v]
                            data[v] = []
                            for lang in langs:
                                key = lang.lower()
                                if key in self.languages:
                                    data['trLanguageOfDocument_en'].append(self.languages[key]['en'])
                                    data['trLanguageOfDocument_es'].append(self.languages[key]['es'])
                                    data['trLanguageOfDocument_fr'].append(self.languages[key]['fr'])
                                else:
                                    data['trLanguageOfDocument_en'].append(lang)
                                    data['trLanguageOfDocument_es'].append(lang)
                                    data['trLanguageOfDocument_fr'].append(lang)
                                    logger.error('Language not found %s' % (lang))
                        elif v in FALSE_LIST_FIELDS:
                            data[v] = self._clean_text(field_values[0].text)
                            if len(field_values) > 1:
                                logger.error('Treaty:{} Field {} has a value'
                                             'with more '
                                             'than 1 elements: {}. Should '
                                             'convert its type back to list.'
                                             .format(elis_id, v, field_values))

                self._set_values_from_dict(data, 'trRegion', self.regions)
                self._set_values_from_dict(data, 'trKeyword', self.keywords)
                self._set_values_from_dict(data, 'trSubject', self.subjects)

                for party in document.findAll('party'):
                    if not getattr(party, 'country'):
                        continue
                    for k, v in PARTICIPANT_FIELDS.items():
                        field = getattr(party, k)
                        if v not in data:
                            data[v] = []
                        if not field and k in ('countryFr', 'countrySp'):
                            field = getattr(party, 'country')
                        if field:
                            clean_field = self._clean_text(field.text)
                            data[v].append(self._party_format_date(clean_field)
                                           if v in DATE_FIELDS
                                           else clean_field)
                        else:
                            data[v].append(NULL_DATE)

                for party_field in PARTICIPANT_FIELDS.values():
                    if party_field not in data:
                        continue
                    if all([d == NULL_DATE for d in data[party_field]]):
                        data[party_field] = None

                elis_id = data['trElisId'][0]
                data['trElisId'] = elis_id
                data = self._apply_custom_rules(data)
                treaties[elis_id] = data

                title = (data.get('trTitleOfText_en') or
                         data.get('trTitleOfText_fr') or
                         data.get('trTitleOfText_es') or
                         data.get('trTitleOfText_other') or
                         data.get('trTitleOfTextShort') or
                         data.get('trTitleAbbreviation') or
                         '')
                slug = title + ' ' + elis_id
                data['slug'] = slugify(slug)
                data['updatedDate'] = (datetime.now()
                                       .strftime('%Y-%m-%dT%H:%M:%SZ'))
        return treaties

    def _apply_custom_rules(self, data):
        for rule in self.CUSTOM_RULES:
            value = data.get(rule['condition_field'], '')
            if value == rule['condition_value']:
                data[rule['action_field']] = rule['action_value']

        available_in = data.get('trAvailableIn', '')
        if available_in and available_in.startswith('B7'):
            data['trAvailableIn'] = available_in.replace('B7', B7)

        # fix server2.php/server2neu.php in full text links
        field_names = ['trLinkToFullText_en', 'trLinkToFullText_es',
                       'trLinkToFullText_fr', 'trLinkToFullText_other',
                       'trLinkToAbstract']
        for key, value in data.items():
            if key in field_names:
                data[key] = list(map(replace_url, data[key]))
        return data

    def _index_files(self, treaties):
        for treaty in treaties:
            full_index = True
            treaty['trText'] = ''

            for field in URL_FIELDS:
                urls = treaty.get(FIELD_MAP[field], [])
                for url in urls:
                    logger.info('Downloading: %s' % url)
                    file_obj = get_file_from_url(url)
                    if file_obj:
                        # Download successful
                        try:
                            treaty['trText'] += self.solr.extract(file_obj)
                        except:
                            # SOLR error at pdf extraction
                            full_index = False
                            self._document_text_pdf_error(treaty, url)
                            logger.error('Error extracting from doc %s' %
                                         treaty['trElisId'])
                    else:
                        # Download failed
                        full_index = False
                        self._document_text_pdf_error(treaty, url)

            if full_index:
                logger.info('Success on file download %s' % treaty['trElisId'])
                self._document_text_pdf_success(treaty)

    def _document_text_pdf_error(self, treaty, url):
        doc, _ = DocumentText.objects.get_or_create(
            doc_id=treaty['trElisId'], doc_type=TREATY)
        doc.url = url
        doc.parsed_data = json.dumps(treaty)
        doc.status = DocumentText.INDEXED
        doc.save()

    def _document_text_pdf_success(self, treaty):
        doc, _ = DocumentText.objects.get_or_create(
            doc_id=treaty['trElisId'], doc_type=TREATY)
        doc.status = DocumentText.FULL_INDEXED
        doc.save()

    def _get_solr_treaty(self, treaty_data):
        new_treaty = Treaty(treaty_data, self.solr)
        existing_treaty = self.solr.search(TREATY, treaty_data['trElisId'])
        if not existing_treaty:
            logger.info('Insert on %s' % (treaty_data['trElisId']))
        elif not new_treaty.is_modified(existing_treaty):
            return None
        solr_id = existing_treaty['id'] if existing_treaty else None
        return new_treaty.get_solr_format(treaty_data['trElisId'], solr_id)

    def _clean_text(self, text):
        return html.unescape(text.strip())

    def _repair_date(self, date):
        date_info = date.split('-')
        if len(date_info) != 3:
            return date
        if date_info[1] == '00':
            date_info[1] = '01'
        if date_info[2] == '00':
            date_info[2] = '01'
        if date_info[0] == '0000':
            return date
        return '-'.join(date_info)

    def _valid_date(self, date):
        date_info = date.split('-')
        if len(date_info) != 3:
            return False
        if (date_info[0] == '0000' or date_info[1] == '00' or
                date_info[2] == '00'):
            return False
        return True

    def _party_format_date(self, date):
        if date == '':
            return date
        date_fields = date.split('-')
        for i in range(3 - len(date_fields)):
            date += "-01"
        return format_date(date)

    def _clean_referred_treaties(self, solr_docs):
        for elis_id, doc in solr_docs.items():
            solr_docs[elis_id] = dict((k, v)
                                      for k, v in solr_docs[elis_id].items()
                                      if not isinstance(v, list) or any(v))

    def _create_url(self, year, month, skip):
        query_year = self.query_format.format(year, month, year, month)
        query_hex = hexlify(str.encode(query_year)).decode()
        query = self.query_filter.format(query_hex)
        page = self.query_skip.format(skip)

        url = '%s%s%s%s%s' % (self.treaties_url, self.query_export, query,
                              self.query_type, page)
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

    def update_status(self):
        logger.info('[Treaty] Update status started.')
        rows = 50
        index = 0
        treaties = []
        while True:
            docs = self.solr.solr.search('type:treaty', rows=rows, start=index)
            for treaty in docs:
                treaty = cleanup_copyfields(treaty)
                treaty.pop('_version_')
                if treaty.get('trTypeOfText_en', '') == 'Bilateral':
                    treaty['trStatus'] = 'In force'
                else:
                    treaty_id = treaty.get('trElisId')
                    results = get_documents_by_field('trSupersedesTreaty',
                                                     [treaty_id], rows=100)
                    if len(results):
                        treaty['trStatus'] = 'Superseded'
                    else:
                        if 'trEntryIntoForceDate' in treaty:
                            treaty['trStatus'] = 'In force'
                        else:
                            treaty['trStatus'] = 'Not in force'

                treaties.append(treaty)

            if len(docs) < rows:
                break
            index += rows
        self.solr.add_bulk(treaties)
        logger.info('[Treaty] Update status finished.')

    def update_full_text(self):
        logger.info('[Treaty] Update full text started.')
        objs = DocumentText.objects.filter(status=DocumentText.INDEXED,
                                           doc_type=TREATY)
        for obj in objs:
            treaty_data = json.loads(obj.parsed_data)
            treaty_data['trText'] = ''
            full_index = True

            for field in URL_FIELDS:
                urls = treaty_data.get(FIELD_MAP[field], [])
                for url in urls:
                    logger.info('Downloading: %s' % url)
                    file_obj = get_file_from_url(url)
                    if file_obj:
                        # Download successful
                        try:
                            treaty_data['trText'] += self.solr.extract(file_obj)
                        except:
                            # SOLR error at pdf extraction
                            full_index = False
                            obj.save()
                            logger.error('Error extracting from doc %s' %
                                         obj.doc_id)
                    else:
                        # Download failed
                        full_index = False
                        obj.save()
                        logger.error('Error downloading url from doc %s' %
                                     obj.doc_id)
            try:
                treaty = self.solr.search(TREATY, obj.doc_id)
                if treaty:
                    treaty_data['id'] = treaty['id']
            except SolrError as e:
                logger.error('Error reading treaty %s' % obj.doc_id)
                if settings.DEBUG:
                    logging.getLogger('solr').exception(e)
                continue

            if full_index:
                resp = self.solr.add(treaty_data)
                logger.info('Insert on %s' % (treaty_data['trElisId']))
                if resp:
                    obj.status = DocumentText.FULL_INDEXED
                    obj.parsed_data = ''
                    obj.save()
        logger.info('[Treaty] Update full text finished.')

    def test(self):
        pass
