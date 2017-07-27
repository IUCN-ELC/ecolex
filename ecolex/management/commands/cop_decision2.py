import inspect
import collections
import functools
import itertools

from operator import methodcaller
from operator import itemgetter
from operator import attrgetter

from datetime import date, datetime
from django.conf import settings

from django.db import IntegrityError
from django.core.exceptions import ObjectDoesNotExist
from django.core.exceptions import MultipleObjectsReturned

import logging
import logging.config
import requests

from django.template.defaultfilters import slugify

from ecolex.management.commands.base import BaseImporter
from ecolex.management.definitions import COP_DECISION
from ecolex.management.utils import get_file_from_url
from ecolex.management.commands.logging import LOG_DICT
from ecolex.models import DocumentText

DATE_FORMAT = '%Y-%m-%dT%H:%M:%SZ'

logging.config.dictConfig(LOG_DICT)
logger = logging.getLogger('cop_decision_import')


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


def request_meeting(base_url, cache, decision_json):
    meeting = decision_json.get('field_meeting')
    uuid = meeting[0]['uuid'] if meeting else None
    if uuid:
        cached = cache.get(uuid)
        if cached:
            logger.info('Meeting from cache: %s', uuid)
            return cached
        else:
            url = '{}/{}/json'.format(base_url, uuid)
            logger.info('Requesting meeting: %s', url)
            resp = requests.get(url).json()
            cache[uuid] = resp
            logger.info('Cached meeting: %s', url)
            return cache[uuid]


def request_treaty(solr, treaties, decision_json):
    field = decision_json.get('field_treaty')
    dec_uuid = decision_json['uuid']
    if field:
        uuid = field[0].get('uuid')
        identifer = field[0].get('odata_identifier')
        treaty_id = uuid or treaties.get(identifer)
        if treaty_id:
            logger.info('Requesting treaty from solr: %s', treaty_id)
            treaty = solr.search('trInformeaId', treaty_id)
            if treaty:
                logger.info('Found treaty: %s!', treaty_id)
                return treaty
            else:
                logger.info('Cannot find treaty: %s!', treaty_id)
        else:
            logger.info('Cannot find a treaty id for %s!', dec_uuid)
    else:
        logger.info('Decision has no "field_treaty": %s', dec_uuid)


def extract_text(solr, dec_id, urls):
    get_doc = functools.partial(
        DocumentText.objects.get,
        doc_id=dec_id,
        doc_type=COP_DECISION
    )
    texts = []
    for url in urls:
        try:
            doc = get_doc(url=url)
        except ObjectDoesNotExist:
            logger.info('DocumentText missing for: %s', url)
            with get_file_from_url(url) as file_obj:
                if file_obj:
                    logger.debug('Got file: %s', url)
                    # TODO: handle extract errors!?
                    text = solr.extract(file_obj)
                    size = file_obj.getbuffer().nbytes
                    texts.append((url, text, size))
                    logger.info('Extracted file: %s', url)
        except MultipleObjectsReturned:
            logger.info('DocumentText multiple values for: %s', url)

    create_doc = functools.partial(
        DocumentText.objects.create,
        doc_id=dec_id,
        doc_type=COP_DECISION,
        status=DocumentText.FULL_INDEXED,
    )

    for url, text, size in texts:
        try:
            create_doc(url=url, text=text, doc_size=size)
            logger.info('Created DocumentText for: %s', url)
        except IntegrityError:
            logger.exception('Error creating DocumentText for: %s', url)

    return ''.join((text for url, text, size in texts))


class Field(property):
    """ Marker decorator for solr fields """


class Decision(object):
    """ Immutable object """

    # set in CopDecisionImporter.__init__
    languages = None # languages.json
    treaties = None # treaties.json

    def __init__(self, dec, node, meeting, treaty):
        self.dec = dec
        self.node = node
        self.meeting = meeting
        self.treaty = treaty

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
        # TODO: reduce to unique values based on url, e.g:
        # https://www.informea.org/node/a3c4c801-464a-407e-b07b-288fd2a7c1a0/json
        # which has the same filename and file url for all languages
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

    @Field
    def decType(self):
        field = self.dec.get('field_decision_type')
        return field[0]['label'] if field else None

    @Field
    def decTreaty(self):
        field = self.dec.get('field_treaty')
        return field[0].get('odata_identifier') if field else None

    @Field
    def decTreatyId(self):
        field = self.dec.get('field_treaty')
        if field:
            uuid = field[0].get('uuid')
            identifer = field[0].get('odata_identifier')
            return uuid or self.treaties.get(identifer)

    def _partyCountry(self, lang):
        if self.treaty:
            return self.treaty.get('partyCountry_{}'.format(lang))

    @Field
    def partyCountry_en(self): self._partyCountry('en')

    @Field
    def partyCountry_es(self): self._partyCountry('es')

    @Field
    def partyCountry_fr(self): self._partyCountry('fr')

    def _trSubject(self, lang):
        if self.treaty:
            return self.treaty.get('trSubject_{}'.format(lang))

    @Field
    def trSubject_en(self): self._trSubject('en')

    @Field
    def trSubject_es(self): self._trSubject('es')

    @Field
    def trSubject_fr(self): self._trSubject('fr')

    def _decTreatyName(self, lang):
        if self.treaty:
            return self.treaty.get('trTitleOfText_{}'.format(lang))

    @Field
    def decTreatyName_en(self): self._decTreatyName('en')

    @Field
    def decTreatyName_es(self): self._decTreatyName('es')

    @Field
    def decTreatyName_fr(self): self._decTreatyName('fr')

    @Field
    def slug(self):
        langs = ('en', 'es', 'fr', 'ru', 'ar', 'zh')
        fields = map('decShortTitle_{}'.format, langs)
        titles = (attrgetter(field)(self) for field in fields)

        # grab the first title that hase a truthy value
        title = next(filter(bool, titles))
        slug = '{} {}'.format(title, self.decId)
        return slugify(slug)


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
        Decision.treaties = self.treaties

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
        len_existing = len([node for node in updateable if node.get('solr_id')])
        len_new = len_updateable - len_existing
        logger.info(
            'Found %s decisions needing update. %s new, %s existing!',
            len_updateable,
            len_new,
            len_existing,
        )

        fetch_meeting = functools.partial(request_meeting, self.node_url, {})
        fetch_treaty = functools.partial(
            request_treaty,
            self.solr,
            self.treaties
        )

        json_decisions = tuple(map(request_decision, updateable))
        json_meetings = map(fetch_meeting, json_decisions)
        json_treaties = map(fetch_treaty, json_decisions)

        decisions = (
           Decision(*args) for args
           in zip(json_decisions, updateable, json_meetings, json_treaties)
        )

        for idx, decision in enumerate(decisions, start=1):
            action = 'Updating' if decision.id else 'Inserting'
            logger.info(
                '[%s/%s] %s %s.',
                idx, len_updateable, action, decision.decId
            )
            fields = decision.fields()

            dec_text = extract_text(
                self.solr,
                fields['decId'],
                fields.get('decFileUrls', []),
            )

            if dec_text:
                fields['decText'] = dec_text

            # XXX: How does this update missing fields?
            self.solr.add(fields)
