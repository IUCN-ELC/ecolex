from datetime import date, datetime, timedelta
from django.conf import settings
import logging
import logging.config
import html
import json
import re
import requests

from django.template.defaultfilters import slugify

from ecolex.management.definitions import COP_DECISION, DEC_TREATY_FIELDS
from ecolex.management.utils import EcolexSolr, get_date, get_file_from_url
from ecolex.management.commands.logging import LOG_DICT
from ecolex.models import DocumentText

logging.config.dictConfig(LOG_DICT)
logger = logging.getLogger('cop_decision_import')
regex = re.compile(r'[\n\t\r]')

LANGUAGES = ['en', 'es', 'fr', 'ar', 'ru', 'zh']
DEFAULT_LANG = 'en'

BASE_FIELDS = [
    'id', 'link', 'type', 'status', 'number', 'treaty', 'published', 'updated',
    'meetingId', 'meetingTitle', 'meetingUrl', 'treatyUUID'
]
MULTILINGUAL_FIELDS = ['title', 'longTitle', 'summary', 'content']

# TODO Harvest French and Spanish translations for the following fields:
#   - decKeyword
#   - decLanguage

FIELD_MAP = {
    'id': 'decId',
    'link': 'decLink',

    'title': 'decShortTitle',
    'longTitle': 'decLongTitle',
    'keywords': 'decKeyword_en',
    'summary': 'decSummary',
    'content': 'decBody',
    'type': 'decType',
    'status': 'decStatus',
    'number': 'decNumber',

    'treaty': 'decTreaty',
    'treatyUUID': 'decTreatyId',

    'published': 'decPublishDate',
    'updated': 'decUpdateDate',

    'meetingId': 'decMeetingId',
    'meetingTitle': 'decMeetingTitle',
    'meetingUrl': 'decMeetingUrl',
}

TREATY_FIELDS_MAP = {
    'trTitleOfText_en': 'decTreatyName_en',
    'trTitleOfText_fr': 'decTreatyName_fr',
    'trTitleOfText_es': 'decTreatyName_es',
}


class CopDecision(object):

    def __init__(self, data, solr):
        self.data = data
        self.solr = solr
        self.date_format = '%Y-%m-%dT%H:%M:%SZ'
        self.update_field = 'decUpdateDate'
        self.informea_id = 'decId'

    def is_modified(self, old_treaty):
        old_date = datetime.strptime(old_treaty[self.update_field],
                                     self.date_format)
        new_date = datetime.strptime(self.data[self.update_field],
                                     self.date_format)
        if old_date < new_date:
            logger.info('Update on %s' % (self.data[self.informea_id]))
            return True
        logger.info('No update on %s' % (self.data[self.informea_id]))
        return False

    def get_solr_format(self, informea_id, solr_id):
        if informea_id:
            self.data['id'] = solr_id
        return self.data


class CopDecisionImporter(object):

    def __init__(self, config):
        self.solr_timeout = config.getint('solr_timeout')
        self.languages_json = settings.LANGUAGES_JSON
        self.decision_url = config.get('cop_decision_url')
        self.query_skip = config.get('query_skip')
        self.query_filter = config.get('query_filter')
        self.query_format = config.get('query_format')
        self.query_expand = config.get('query_expand')
        self.query_order = config.get('query_order')
        self.days_ago = config.getint('days_ago')
        self.per_page = config.getint('per_page')
        self.solr = EcolexSolr(self.solr_timeout)
        self.languages = self._get_languages()
        logger.info('Started COP Decision importer')

    def harvest(self, batch_size=500):
        today = date.today()
        last_update = today - timedelta(self.days_ago)
        date_filter = self.query_filter % (
            last_update.strftime('%Y-%m-%dT00:00:00'))

        raw_decisions = []
        skip = 0
        while True:
            skip_filter = self.query_skip % (self.per_page, skip)
            url = self._create_url(date_filter, skip_filter)
            logger.debug(url)
            try:
                response = requests.get(url)
                if response.status_code != 200:
                    logger.error('Invalid return code HTTP %d, retrying.' % response.status_code)
                    # Retry forever
                    continue
            except requests.exceptions.RequestException as e:
                logger.error('Connection error, retrying')
                if settings.DEBUG:
                    logger.exception(e)
                continue

            results = response.json()['d']['results']
            if not results:
                break
            else:
                raw_decisions.extend(results)
            skip += self.per_page

            if skip > batch_size:
                self._index_decisions(raw_decisions)
                raw_decisions = []

        self._index_decisions(raw_decisions)
        logger.info('Finished harvesting COP Decisions')

    def _index_decisions(self, raw_decisions):
        decisions = self._parse(raw_decisions)
        new_decisions = list(filter(bool, [self._get_solr_decision(d) for
                                    d in decisions]))
        self._index_files(new_decisions)
        self.solr.add_bulk(new_decisions)

    def _parse(self, raw_decisions):
        decisions = []

        for decision in raw_decisions:
            data = {'type': COP_DECISION}
            logger.info('Parsing decision %s' % (decision['id'],))
            for field in BASE_FIELDS:
                data[FIELD_MAP[field]] = self._clean(decision.get(field))

            if data['decPublishDate']:
                data['decPublishDate'] = get_date(data['decPublishDate'])
            if data['decUpdateDate']:
                data['decUpdateDate'] = get_date(data['decUpdateDate'])
                if not data['decPublishDate']:
                    data['decPublishDate'] = data['decUpdateDate']

            data['decKeyword_en'] = self._parse_keywords(decision['keywords'])
            languages = set()
            for multi_field in MULTILINGUAL_FIELDS:
                multi_values = self._parse_multilingual(decision[multi_field])
                field = FIELD_MAP[multi_field]
                languages.update(multi_values.keys())
                for k, v in multi_values.items():
                    field_name = field + '_' + k
                    data[field_name] = v
            languages = list(languages) or ['en']
            data['decLanguage_en'] = []
            data['decLanguage_fr'] = []
            data['decLanguage_es'] = []
            for lang in languages:
                data['decLanguage_en'].append(self.languages[lang]['en'])
                data['decLanguage_es'].append(self.languages[lang]['es'])
                data['decLanguage_fr'].append(self.languages[lang]['fr'])

            files = decision['files']['results']
            if files:
                urls, file_names = self._parse_files(files)
                data['decFileUrls'] = urls
                data['decFileNames'] = file_names

            if data['decTreatyId']:
                treaties = self.solr.search_all('trInformeaId',
                                                data['decTreatyId'])
                if treaties:
                    for field in DEC_TREATY_FIELDS:
                        data[field] = [x for tr in treaties for x in tr[field]]
                    for k, v in TREATY_FIELDS_MAP.items():
                        if k in treaties[0]:
                            data[v] = treaties[0][k]

            title = (data.get('decShortTitle_en') or
                     data.get('decShortTitle_es') or
                     data.get('decShortTitle_fr') or
                     data.get('decShortTitle_ru') or
                     data.get('decShortTitle_ar') or
                     data.get('decShortTitle_zh'))
            slug = title + ' ' + data.get('decId')
            data['slug'] = slugify(slug)
            decisions.append(data)
        return decisions

    def _get_solr_decision(self, dec_data):
        new_dec = CopDecision(dec_data, self.solr)
        existing_dec = self.solr.search(COP_DECISION, dec_data['decId'])
        if not existing_dec:
            logger.info('Insert on decision %s' % (dec_data['decId'],))
        if existing_dec and not new_dec.is_modified(existing_dec):
            return None
        solr_id = existing_dec['id'] if existing_dec else None
        return new_dec.get_solr_format(dec_data['decId'], solr_id)

    def _parse_keywords(self, info):
        keywords = {}
        for result in info['results']:
            term = result['term']
            if term not in keywords:
                keywords[term] = True
        return list(keywords.keys()) or None

    def _parse_multilingual(self, info):
        values = {}
        if 'results' in info:
            for result in info['results']:
                language = result['language']
                if language not in LANGUAGES:
                    continue
                value = regex.sub('', result['value'])
                values[language] = value.strip()
        return values

    def _parse_files(self, files):
        urls = []
        filenames = []

        for file_dict in files:
            url = file_dict['url']
            filename = file_dict['filename']
            if url and filename:
                urls.append(url)
                filenames.append(filename)
        return urls, filenames

    def _index_files(self, decisions):
        for decision in decisions:
            url_list = decision.get('decFileUrls', [])
            decId = decision['decId']
            dec_text = ''
            if not url_list:
                # Nothing to download
                doc, _ = DocumentText.objects.get_or_create(
                    doc_id=decId, doc_type=COP_DECISION, url=None)
                doc.status = DocumentText.INDEXED
                doc.save()

            for url in url_list:
                doc, _ = DocumentText.objects.get_or_create(
                    doc_id=decId, doc_type=COP_DECISION, url=url)
                if doc.status == DocumentText.FULL_INDEXED:
                    dec_text += doc.text
                    logger.info('Already indexed %s' % url)
                else:
                    logger.info('Downloading: %s' % url)
                    file_obj = get_file_from_url(url)
                    if file_obj:
                        logger.debug('Success downloading %s' % url)
                        doc.text = self.solr.extract(file_obj)
                        dec_text += doc.text
                        doc.status = DocumentText.FULL_INDEXED
                        doc.doc_size = file_obj.getbuffer().nbytes
                        doc.save()
                        logger.info('Success extracting %s' % decId)
                    else:
                        logger.error('Error on file download %s' % decId)
                        doc.status = DocumentText.INDEXED
                        doc.save()

            decision['decText'] = dec_text

    def _get_languages(self):
        with open(self.languages_json) as f:
            languages_codes = json.load(f)
        return languages_codes

    def _clean(self, text):
        try:
            text = html.unescape(text.strip())
        except:
            pass
        return text

    def _create_url(self, date_filter, skip_filter):
        url = '%s?%s&%s&%s&%s&%s' % (self.decision_url, skip_filter,
                                     self.query_format, self.query_expand,
                                     date_filter, self.query_order)
        return url
