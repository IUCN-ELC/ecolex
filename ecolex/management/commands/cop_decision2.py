import inspect
import collections
import functools
import itertools
from operator import methodcaller
from operator import itemgetter

from datetime import date, datetime, timedelta
from django.conf import settings
import logging
import logging.config
import html
import re
import requests

from django.template.defaultfilters import slugify

from ecolex.management.commands.base import BaseImporter
from ecolex.management.definitions import COP_DECISION
from ecolex.management.definitions import DEC_TREATY_FIELDS
from ecolex.management.utils import get_date
from ecolex.management.utils import get_file_from_url
from ecolex.management.commands.logging import LOG_DICT
from ecolex.models import DocumentText

DATE_FORMAT = '%Y-%m-%dT%H:%M:%SZ'

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


def request_page(url, per_page, page=1):
    params = dict(
        items_per_page=per_page,
        page=page,
    )
    logger.info('Fetching page %s.', page)
    return requests.get(url, params=params)


def request_decision(json_node):
    # TODO: proper error handling and logging
    url = json_node['data_url']
    logger.info('Requesting decision: %s', url)
    return requests.get(url).json()


def request_meeting(base_url, decision_json):
    meeting = decision_json.get('field_meeting')
    uuid = meeting[0]['uuid'] if meeting else None
    if uuid:
        url = '{}/{}/json'.format(base_url, uuid)
        logger.info('Requesting meeting: %s', url)
        return requests.get(url).json()


class Field(property):
    """ Marker decorator for solr fields """


__Decision = collections.namedtuple('Decision', ['dec', 'node', 'meeting'])
class Decision(__Decision):
    """ Immutable object """

    languages = None

    def fields(self):
        is_field = lambda member: isinstance(member, Field)
        properties = inspect.getmembers(Decision, is_field)
        fvalues = ((name, getattr(self, name)) for name, _ in properties)
        return { name: value for name, value in fvalues if value }

    @Field
    def type(self):
        return COP_DECISION

    @Field
    def id(self):
        """ set by _get_decisions, if the item exists in solr """
        return self.node.get('solr_id')

    @Field
    def decId(self):
        return self.dec['uuid']

    def _decBody(self, lang):
        body = self.dec.get('body')
        return body.get(lang, None) if body else None

    @Field
    def decBody_en(self): return self._decBody('en')

    @Field
    def decBody_es(self): return self._decBody('es')

    @Field
    def decBody_fr(self): return self._decBody('fr')

    @Field
    def decBody_ru(self): return self._decBody('ru')

    @Field
    def decBody_zh(self): return self._decBody('zh')

    def _file_data(self, name):
        files = self.dec.get('field_files')
        extractor = itemgetter(name)
        return [extractor(f[0]) for f in files.values()] if files else None

    @Field
    def decFileNames(self): return self._file_data('filename')

    @Field
    def decFileUrls(self): return self._file_data('url')

    @Field
    def decUpdateDate(self):
        node_update = datetime.fromtimestamp(
            int(self.node['last_update'])
        )
        return node_update.strftime(DATE_FORMAT)

    @Field
    def decKeyword_en(self):
        tags = self.dec.get('field_informea_tags')
        return [tag['url'] for tag in tags]

    def _decLanguage(self, lang):
        fields = ('title_field', 'body', 'field_files')
        fvalues = filter(bool, map(self.dec.get, fields))
        langs = set(itertools.chain(*map(methodcaller('keys'), fvalues)))
        return [self.languages[code][lang] for code in langs]

    @Field
    def decLanguage_en(self): return self._decLanguage('en')

    @Field
    def decLanguage_es(self): return self._decLanguage('es')

    @Field
    def decLanguage_fr(self): return self._decLanguage('fr')

    @Field
    def decLink(self):
        field_url = self.dec.get('field_url')
        if field_url:
            return field_url['en'][0]['url']
        else:
            return self.dec.get('url')['en']

    @Field
    def decMeetingId(self):
        meeting = self.dec.get('field_meeting')
        return meeting[0]['uuid'] if meeting else None

    @Field
    def decMeetingTitle(self):
        if self.meeting:
            return self.meeting['title_field']['en'][0]['value']

    @Field
    def decMeetingUrl(self):
        if self.meeting:
            field_url = self.meeting.get('field_url')
            if field_url:
                return field_url['en'][0]['url']
            else:
                return self.meeting.get('url')['en']

    @Field
    def decNumber(self):
        field = self.dec.get('field_decision_number')
        return field['und'][0]['value'] if field else None

    @Field
    def decPublishDate(self):
        field = self.dec.get('field_sorting_date')
        if field:
            date = field['und'][0]['value']
            formatted = datetime.strptime(date, '%Y-%m-%d %H:%M:%S')
            return formatted.strftime(DATE_FORMAT)

    def _decShortTitle(self, lang):
        title = self.dec.get('title_field')
        fvalue = title and title.get(lang)
        return fvalue[0]['value'] if fvalue else None

    @Field
    def decShortTitle_ar(self): return self._decShortTitle('ar')

    @Field
    def decShortTitle_en(self): return self._decShortTitle('en')

    @Field
    def decShortTitle_es(self): return self._decShortTitle('es')

    @Field
    def decShortTitle_fr(self): return self._decShortTitle('fr')

    @Field
    def decShortTitle_ru(self): return self._decShortTitle('ru')

    @Field
    def decShortTitle_zh(self): return self._decShortTitle('zh')

    @Field
    def decStatus(self):
        status = self.dec.get('field_decision_status')
        return status[0]['label'] if status else None

    def _decSummary(self, lang):
        body = self.dec.get('body')
        fvalue = body and body.get(lang)
        return fvalue[0]['summary'] if fvalue else None

    @Field
    def decSummary_en(self): return self._decSummary('en')

    @Field
    def decSummary_es(self): return self._decSummary('es')

    @Field
    def decSummary_fr(self): return self._decSummary('fr')



class CopDecisionImporter(BaseImporter):

    id_field = 'decId'

    def __init__(self, config):
        super().__init__(config, logger, COP_DECISION)

        self.decision_url = config.get('decision_url')
        self.per_page = config.get('items_per_page')
        self.node_url = config.get('node_url')

        self.request_page = functools.partial(
            request_page,
            self.decision_url,
            self.per_page
        )

        Decision.languages = self.languages

        logger.info('Started COP Decision importer')

    def _get_decisions(self):
        for page_num in itertools.count(start=231, step=1):
            nodes = self.request_page(page_num).json()

            # signal for takewhile to stop requesting items
            if not nodes:
                yield None

            for node in nodes:
                solr_decision = self.solr.search(COP_DECISION, node['uuid'])

                if not solr_decision:
                    logger.info('%s not in solr, queuing.', node['uuid'])
                    yield node

                elif solr_decision:
                    logger.info('%s found in solr!', node['uuid'])
                    solr_update = datetime.strptime(
                        solr_decision['decUpdateDate'],
                        DATE_FORMAT
                    )
                    node_update = datetime.fromtimestamp(
                        int(node['last_update'])
                    )

                    if node_update > solr_update:
                        logger.info('%s outdated, queuing.', node['uuid'])
                        yield {**node, **dict(solr_id=solr_decision['id'])}
                    else:
                        logger.info('%s is up to date.', node['uuid'])


    def harvest(self, batch_size=500):
        updateable = tuple(itertools.takewhile(bool, self._get_decisions()))
        len_updateable = len(updateable)
        logger.info('Found %s decision needing update!', len_updateable)

        fetch_meeting = functools.partial(request_meeting, self.node_url)

        json_decisions = tuple(map(request_decision, updateable))
        json_meetings = map(fetch_meeting, json_decisions)

        decisions = (
           Decision(*args) for args
           in zip(json_decisions, updateable, json_meetings)
        )

        for idx, decision in enumerate(decisions, start=1):
            logger.info('[%s/%s] Adding %s.', idx, len_updateable, decision.decId)
            self.solr.add(decision.fields())


        # today = date.today()
        # last_update = today - timedelta(self.days_ago)
        # date_filter = self.query_filter % (
        #     last_update.strftime('%Y-%m-%dT00:00:00'))

        # raw_decisions = []
        # skip = 0
        # while True:
        #     skip_filter = self.query_skip % (self.per_page, skip)
        #     url = self._create_url(date_filter, skip_filter)
        #     logger.debug(url)
        #     try:
        #         response = requests.get(url)
        #         if response.status_code != 200:
        #             logger.error('Invalid return code HTTP %d, retrying.'
        #                          % response.status_code)
        #             # Retry forever
        #             continue
        #     except requests.exceptions.RequestException as e:
        #         logger.error('Connection error, retrying')
        #         if settings.DEBUG:
        #             logger.exception(e)
        #         continue

        #     results = response.json()['d']['results']
        #     if not results:
        #         break
        #     else:
        #         raw_decisions.extend(results)
        #     skip += self.per_page

        #     if skip > batch_size:
        #         self._index_decisions(raw_decisions)
        #         raw_decisions = []

        # self._index_decisions(raw_decisions)
        # logger.info('Finished harvesting COP Decisions')

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
            if data['decKeyword_en']:
                self._set_values_from_dict(data, 'decKeyword', self.keywords)

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

            if not data['decTreatyId'] and data['decTreaty'] and data['decTreaty'] in self.treaties:
                # Try to get the UUID from our local json file
                data['decTreatyId'] = self.treaties[data['decTreaty']]['uuid']

            if data['decTreatyId']:
                treaties = self.solr.search_all('trInformeaId',
                                                data['decTreatyId'])
                if treaties:
                    for field in DEC_TREATY_FIELDS:
                        data[field] = [x for tr in treaties for x in tr[field]]
                    for k, v in TREATY_FIELDS_MAP.items():
                        if k in treaties[0]:
                            data[v] = treaties[0][k]
                else:
                    logger.warning('Treaty %s was not found for decision %s' %
                                   (data['decTreatyId'], data['decId']))

            title = (data.get('decShortTitle_en') or
                     data.get('decShortTitle_es') or
                     data.get('decShortTitle_fr') or
                     data.get('decShortTitle_ru') or
                     data.get('decShortTitle_ar') or
                     data.get('decShortTitle_zh'))
            slug = title + ' ' + data.get('decId')
            data['slug'] = slugify(slug)
            data['updatedDate'] = (datetime.now()
                                   .strftime('%Y-%m-%dT%H:%M:%SZ'))
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
                if language not in LANGUAGES or not result.get('value'):
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
            if url and url not in urls and filename:
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
