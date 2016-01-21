from datetime import date, datetime, timedelta
import logging
import logging.config
import re
import requests

from utils import EcolexSolr, get_date, get_file_from_url
from utils import COP_DECISION, DEC_TREATY_FIELDS
from config.logging import LOG_DICT

logging.config.dictConfig(LOG_DICT)
logger = logging.getLogger('import')
regex = re.compile(r'[\n\t\r]')

LANGUAGES = ['en', 'es', 'fr', 'ar', 'ru', 'zh']
DEFAULT_LANG = 'en'

BASE_FIELDS = [
    'id', 'link', 'type', 'status', 'number', 'treaty', 'published', 'updated',
    'meetingId', 'meetingTitle', 'meetingUrl', 'treatyUUID'
]
MULTILANGUAL_FIELDS = ['title', 'longTitle']

FIELD_MAP = {
    'id': 'decId',
    'link': 'decLink',

    'title': 'decShortTitle',
    'longTitle': 'decLongTitle',
    'keywords': 'decKeyword',
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
        self.decision_url = config.get('cop_decision_url')
        self.query_skip = config.get('query_skip')
        self.query_filter = config.get('query_filter')
        self.query_format = config.get('query_format')
        self.query_expand = config.get('query_expand')
        self.query_order = config.get('query_order')
        self.days_ago = config.getint('days_ago')
        self.per_page = config.getint('per_page')
        self.solr = EcolexSolr(self.solr_timeout)
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
            response = requests.get(url)
            if response.status_code != 200:
                logger.error('Invalid return code %d' % response.status_code)

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
        new_decisions = filter(bool, [self._get_solr_decision(d) for
                               d in decisions])
        self.solr.add_bulk(new_decisions)

    def _parse(self, raw_decisions):
        decisions = []

        for decision in raw_decisions:
            data = {'type': COP_DECISION}

            for field in BASE_FIELDS:
                data[FIELD_MAP[field]] = self._clean(decision[field])

            if data['decPublishDate']:
                date = get_date(data['decPublishDate'])
                data['decPublishDate'] = date.strftime("%Y-%m-%dT%H:%M:%SZ")
            if data['decUpdateDate']:
                date = get_date(data['decUpdateDate'])
                data['decUpdateDate'] = date.strftime("%Y-%m-%dT%H:%M:%SZ")

            data['decKeyword'] = self._parse_keywords(decision['keywords'])
            for multi_field in MULTILANGUAL_FIELDS:
                multi_values = self._parse_multilingual(decision[multi_field])
                field = FIELD_MAP[multi_field]
                for k, v in multi_values.items():
                    field_name = field + '_' + k
                    data[field_name] = v

            dec_body = self._parse_multilingual(decision['content'])
            data['decBody'] = list(dec_body.values())
            files = decision['files']['results']
            if files:
                data['text'], data['decLanguage'] = self._parse_files(files)

            if data['decTreatyId']:
                treaties = self.solr.search_all('trInformeaId',
                                                data['decTreatyId'])
                if treaties:
                    for field in DEC_TREATY_FIELDS:
                        data[field] = [tr[field] for tr in treaties]
            decisions.append(data)
        return decisions

    def _get_solr_decision(self, dec_data):
        new_dec = CopDecision(dec_data, self.solr)
        exisiting_dec = self.solr.search(COP_DECISION, dec_data['decId'])
        if exisiting_dec and not new_dec.is_modified(exisiting_dec):
            return None
        solr_id = exisiting_dec['id'] if exisiting_dec else None
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
        for result in info['results']:
            language = result['language']
            if language not in LANGUAGES:
                continue
            value = regex.sub('', result['value'])
            values[language] = value.strip()
        return values

    def _parse_files(self, files):
        languages = set()
        text = ''
        for file_dict in files:
            lang = file_dict.get('language')
            languages.add(lang if lang not in (None, 'und') else DEFAULT_LANG)
            file_obj = get_file_from_url(file_dict['url'])
            text += self.solr.extract(file_obj)
        return text, languages

    def _clean(self, text):
        try:
            text = text.strip()
        except:
            pass
        return text

    def _create_url(self, date_filter, skip_filter):
        url = '%s?%s&%s&%s&%s&%s' % (self.decision_url, skip_filter,
                                     self.query_format, self.query_expand,
                                     date_filter, self.query_order)
        return url
