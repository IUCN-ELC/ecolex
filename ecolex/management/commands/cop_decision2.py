import inspect
import collections
import functools
import itertools
import json

from operator import methodcaller
from operator import itemgetter
from operator import attrgetter

from datetime import date, datetime
from django.conf import settings

from django.db import IntegrityError
from django.db import OperationalError
from django.core.exceptions import ObjectDoesNotExist
from django.core.exceptions import MultipleObjectsReturned

import logging
import logging.config
import requests
import django.db

from requests.adapters import HTTPAdapter

from django.template.defaultfilters import slugify

from ecolex.management.commands.base import BaseImporter
from ecolex.management.definitions import COP_DECISION, TREATY
from ecolex.management.utils import get_file_from_url
from ecolex.management.utils import keywords_informea_to_ecolex
from ecolex.management.utils import keywords_ecolex
from ecolex.management.commands.logging import LOG_DICT
from ecolex.models import DocumentText

DATE_FORMAT = '%Y-%m-%dT%H:%M:%SZ'

logging.config.dictConfig(LOG_DICT)
logger = logging.getLogger('cop_decision_import')


def uniq_on_key(key, acc, item):
    """ Unique items from a list of dicts, based on `key` value. """
    values = [item[key] for item in acc]
    if item[key] not in values:
        acc.append(item)
    return acc


def reset_db_connection():
    for conn in django.db.connections.all():
        conn.close()


class Report(object):

    def __init__(self):
        self.added = []
        self.updated = []
        self.failed = []
        self.missing_treaties = []


class Field(property):
    """ Marker decorator for solr fields """


class Decision(object):

    # set in CopDecisionImporter.__init__
    languages = None # languages.json
    treaties = None # treaties.json

    def __init__(self, dec, meeting, treaty, solr_id):
        self.dec = dec
        self.meeting = meeting
        self.treaty = treaty
        self.solr_id = solr_id

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
        return self.solr_id

    @Field
    def decId(self):
        return self.dec['uuid']

    def _decBody(self, lang):
        body = self.dec.get('body', {}).get(lang)
        if not body:
            # Can be empty list or None
            return None
        return body[0]['value']

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

        if files:
            uniq_on_url = functools.partial(uniq_on_key, 'url')
            values = [
                f for flist in files.values() for f in flist
            ]
            unique_files = functools.reduce(uniq_on_url, values, [])
            return [f[name] for f in unique_files]

    @Field
    def decFileNames(self): return self._file_data('filename')

    @Field
    def decFileUrls(self): return self._file_data('url')

    @Field
    def decUpdateDate(self):
        node_update = datetime.fromtimestamp(int(self.dec['changed']))
        return node_update.strftime(DATE_FORMAT)

    def _decKeyword(self, lang):
        to_ecolex = keywords_informea_to_ecolex(
            self.informea_keywords,
            self.keywords,
            self.dec.get('field_informea_tags', [])
        )
        return keywords_ecolex(to_ecolex, lang)

    @Field
    def decKeyword_en(self):
        return self._decKeyword('en')

    @Field
    def decKeyword_es(self):
        return self._decKeyword('es')

    @Field
    def decKeyword_fr(self):
        return self._decKeyword('fr')

    def _decLanguage(self, lang):
        fields = ('title_field', 'body', 'field_files')
        fvalues = filter(bool, map(self.dec.get, fields))
        langs = set(itertools.chain(*map(methodcaller('keys'), fvalues)))
        return [self.languages[code][lang] for code in langs if code in self.languages]

    @Field
    def decLanguage_en(self): return self._decLanguage('en')

    @Field
    def decLanguage_es(self): return self._decLanguage('es')

    @Field
    def decLanguage_fr(self): return self._decLanguage('fr')

    @Field
    def decLink(self):
        field_url = self.dec.get('field_external_url')
        if field_url:
            return field_url['und'][0]['uri']
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
            formatted = datetime.strptime(field, '%Y-%m-%d')
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
        return status['und'][0]['value'] if status else None

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
        return field['und'][0]['value'] if field else None

    @Field
    def decTreaty(self):
        # treaty_slug, used for Google Analytics
        field = self.dec.get('field_treaty')
        if field:
            uuid = field[0].get('uuid')
            identifier = field[0].get('odata_identifier')
            if not identifier:
                identifier = next(
                    (key for key,item in self.treaties.items() if item["uuid"] == uuid),
                    None
                )
            return identifier

    @Field
    def decTreatyId(self):
        if self.treaty:
            return self.treaty.get('trInformeaId')

    def _partyCountry(self, lang):
        if self.treaty:
            return self.treaty.get('partyCountry_{}'.format(lang))

    @Field
    def partyCountry_en(self): return self._partyCountry('en')

    @Field
    def partyCountry_es(self): return self._partyCountry('es')

    @Field
    def partyCountry_fr(self): return self._partyCountry('fr')

    def _trSubject(self, lang):
        if self.treaty:
            return self.treaty.get('trSubject_{}'.format(lang))

    @Field
    def trSubject_en(self): return self._trSubject('en')

    @Field
    def trSubject_es(self): return self._trSubject('es')

    @Field
    def trSubject_fr(self): return self._trSubject('fr')

    def _decTreatyName(self, lang):
        if self.treaty:
            return self.treaty.get('trTitleOfText_{}'.format(lang))

    @Field
    def decTreatyName_en(self): return self._decTreatyName('en')

    @Field
    def decTreatyName_es(self): return self._decTreatyName('es')

    @Field
    def decTreatyName_fr(self): return self._decTreatyName('fr')

    @Field
    def slug(self):
        langs = ('en', 'es', 'fr', 'ru', 'ar', 'zh')
        fields = map('decShortTitle_{}'.format, langs)
        titles = (attrgetter(field)(self) for field in fields)

        # grab the first title that hase a truthy value
        title = next(filter(bool, titles))
        slug = '{} {}'.format(title, self.decId)
        return slugify(slug)


def request_json(url, *args, **kwargs):
    # needed to for retry
    s = requests.Session()
    s.mount(url, HTTPAdapter(max_retries=3))

    try:
        return s.get(url, *args, **kwargs).json()
    except Exception:
        logger.exception('Error fetching url: %s.', url)
        raise


def request_page(url, per_page, page_num=0, max_pages=False, treaty_uuid=None):
    params = dict(
        items_per_page=per_page,
        page=page_num,
        treaty_uuid=treaty_uuid,
    )
    logger.info('Fetching page %s.', page_num)
    if max_pages and page_num == max_pages:
        logger.info('Forced stop at max_page %s.', page_num)
        return None
    return request_json(url, params=params)


def request_uuid(base_url, uuid):
    url = '{}/{}/json'.format(base_url, uuid)
    logger.info('Fetching uuid: %s from %s!', uuid, url)
    return request_json(url)


def request_meeting(base_url, cache, json_decision):
    meeting = json_decision.get('field_meeting')
    uuid = meeting[0]['uuid'] if meeting else None
    if uuid:
        cached = cache.get(uuid)
        if cached:
            logger.info('Meeting from cache: %s', uuid)
            return cached
        else:
            logger.info('Requesting meeting: %s', uuid)
            resp = request_uuid(base_url, uuid)
            cache[uuid] = resp
            logger.info('Cached meeting: %s', uuid)
            return cache[uuid]


def request_treaty(solr, treaties, cache, json_decision):
    treaty_uuid = json_decision.get(
        'field_treaty',
        [{"uuid": None}]
    )[0]["uuid"]
    if not treaty_uuid:
        logger.warn('Decision has no "field_treaty": %s', json_decision['uuid'])
        return None, None

    cached = cache.get(treaty_uuid)
    if cached:
        logger.info('Treaty from cache: %s', treaty_uuid)
        return cached

    json_treaty = next(
        (x for x in treaties.values() if x["uuid"] == treaty_uuid),
        None
    )
    if not json_treaty:
        logger.warn('Unknown treaty %s', treaty_uuid)
        return None, None

    ecolex_id = json_treaty.get('docId')
    treaty = None
    if ecolex_id:
        logger.info(f'Loading treaty {treaty_uuid} from solr: {ecolex_id}')
        treaty = solr.search(TREATY, ecolex_id)
        if treaty:
            logger.info('Found treaty: %s!', treaty.get("trInformeaId"))
    if not treaty:
        # return mock data, useful for faceted search
        logger.info('Treaty %s not in ECOLEX', treaty_uuid)
        treaty = {
            'trTitleOfText_en': json_treaty.get('short_name'),
            'trTitleOfText_fr': json_treaty.get('short_name'),
            'trTitleOfText_es': json_treaty.get('short_name'),
            'trInformeaId': treaty_uuid,
        }
    logger.info('Cached treaty %s', treaty_uuid)
    cache[treaty_uuid] = (treaty, treaty_uuid)
    return treaty, treaty_uuid


def create_document(dec_id, url, text, size, retry=True):
    create = functools.partial(
        DocumentText.objects.create,
        doc_id=dec_id,
        doc_type=COP_DECISION,
        status=DocumentText.FULL_INDEXED,
    )
    try:
        create(url=url, text=text, doc_size=size)
        logger.info('Created DocumentText for: %s.', url)
    except IntegrityError:
        logger.exception('Error creating DocumentText for: %s!', url)
    except OperationalError:
        if retry:
            # retry once, resetting the db connection beforehand
            logger.warning(
                'Error creating DocumentText for: %s, retrying!', url)
            reset_db_connection()
            create_document(dec_id, url, text, size, retry=False)
        else:
            logger.exception(
                'Error creating DocumentText for: %s! No more retries!', url)


def has_document(dec_id, url, retry=True):
    try:
        return DocumentText.objects.get(
            doc_id=dec_id, doc_type=COP_DECISION, url=url)
        logger.info('DocumentText exists for: %s.', url)
    except ObjectDoesNotExist:
        logger.info('DocumentText missing for: %s.', url)
    except MultipleObjectsReturned:
        logger.warning('DocumentText multiple values for: %s!', url)
    except OperationalError as err:
        if retry:
            logger.warning('Database error: %s! Retrying!', err)
            reset_db_connection()
            has_document(dec_id, url, retry=False)
        else:
            logger.error('Database error: %s! No more retries!', err)


def extract_text(solr, dec_id, urls):
    # Tuples consisting of: url, text, size and an "exists" flag
    # will be appended to this list. The entries will be used to
    # create missing entries in the sql database if the flag is False;
    # and to finally return the full concatenated text of all file content
    # for solr insertion.
    texts = []

    uniq_urls = set(urls)
    if not uniq_urls:
        logger.info('Decision %s has no files!', dec_id)

    # gather information about files
    for url in uniq_urls:
        logger.info('Extracting text from %s', url)
        document = has_document(dec_id, url)
        if document:
            # text exists, grab it from sql
            logger.info('Using existing text.')
            texts.append((url, document.text, document.doc_size, True))
        else:
            logger.info('Downloading file: %s', url)
            # text doesn't exist in sql, extract with solr
            try:
                file_obj = get_file_from_url(url)
                if file_obj:
                    logger.debug('Downloaded file: %s', url)
                    text = solr.extract(file_obj)
                    size = file_obj.getbuffer().nbytes
                    texts.append((url, text, size, False))
                    logger.info('Extracted file: %s', url)
            except Exception:
                logger.exception('Error extracting file: %s', url)

    for url, text, size, exists in texts:
        if not exists:
            create_document(dec_id, url, text, size)

    return ''.join((text or '' for _, text, _, _ in texts))


def get_node(base_url, per_page, start=0, max_pages=False, treaty_uuid=None):
    for page_num in itertools.count(start=start, step=1):
        nodes = request_page(base_url, per_page, page_num, max_pages, treaty_uuid)
        yield from nodes if nodes else [None]


def needs_update(solr, node, force):
    uuid = node['uuid']
    solr_decision = solr.search(COP_DECISION, uuid)
    if solr_decision:
        logger.debug('%s found in solr!', uuid)
        solr_date = solr_decision['decUpdateDate']
        node_date = int(node['last_update'])

        solr_update = datetime.strptime(solr_date, DATE_FORMAT)
        node_update = datetime.fromtimestamp(node_date)

        if force:
            logger.info('Forced update: %s', uuid)
            return {**node, **dict(solr_id=solr_decision['id'])}

        elif node_update > solr_update:
            logger.info('%s outdated, queuing.', uuid)
            return {**node, **dict(solr_id=solr_decision['id'])}

        else:
            logger.debug('%s is up to date.', uuid)

    else:
        logger.info('%s not in solr, queuing.', uuid)
        return node


def count_nodes(acc, node):
    acc[0] += 1 # increment total

    if node.get('solr_id'):
        acc[1] += 1 # increment existing
    else:
        acc[2] += 1 # increment new

    return acc


def find_solr_id(solr, uuid):
    solr_decision = solr.search(COP_DECISION, uuid)
    if solr_decision:
        solr_id = solr_decision.get('id')
        logger.info('Found solr id: %s for %s', solr_id, uuid)
        return solr_id
    else:
        logger.info('Not found in solr. New entry will be created.')


class CopDecisionImporter(BaseImporter):

    id_field = 'decId'

    def __init__(self, config):
        super().__init__(config, logger, COP_DECISION)

        self.decision_url = config.get('decision_url')
        self.per_page = config.get('items_per_page')
        self.max_pages = config.get('max_pages', False)
        self.node_url = config.get('node_url')

        self.report = Report()

        # Set these at class level as they don't change
        Decision.languages = self.languages
        Decision.treaties = self.treaties
        Decision.keywords = self.keywords
        Decision.informea_keywords = self.informea_keywords


        # wrap request_meeting in order to provide a caching dict
        # also pass the base_url, since it's the same at all times
        self.fetch_meeting = functools.partial(
            request_meeting, self.node_url, {})

        self.fetch_treaty = functools.partial(
            request_treaty, self.solr, self.treaties, {})

    def harvest_one(self, uuid, solr_id='check', force=True):
        logger.info('Harvesting: %s', uuid)

        if solr_id == 'check':
            logger.info('Solr id not specified, finding!')
            solr_id = find_solr_id(self.solr, uuid)

        try:
            json_decision = request_uuid(self.node_url, uuid)
            json_meeting = self.fetch_meeting(json_decision)
            json_treaty, treaty_id = self.fetch_treaty(json_decision)

            if treaty_id and 'id' not in json_treaty:
                self.report.missing_treaties += [treaty_id]

        except Exception:
            logger.error('Cannot request URLs for: %s. Skipping!', uuid)
            raise

        decision = Decision(json_decision, json_meeting, json_treaty, solr_id)

        fields = decision.fields()

        try:
            dec_text = extract_text(
                self.solr,
                fields['decId'],
                fields.get('decFileUrls', []),
            )

            if dec_text:
                fields['decText'] = dec_text

        except Exception:
            self.report.failed += [uuid]
            logger.exception('Failed text extraction for: %s.', uuid)

        try:
            if self.solr.add(fields):
                logger.info('Solr succesfully updated!')
            else:
                logger.error('Error updating solr!')
        except Exception:
            logger.exception('Error updating solr!')
            raise

    def harvest_list(self, items, force):
        total, existing, new = functools.reduce(count_nodes, items, [0, 0, 0])
        seen = set()

        logger.info(
            'Found %s decisions needing update. %s new, %s existing!',
            total, new, existing)

        for idx, json_node in enumerate(items, start=0):
            uuid = json_node['uuid']
            if uuid in seen:
                continue
            solr_id = json_node.get('solr_id')

            action = 'Updating' if solr_id else 'Inserting'
            logger.info('[%s/%s] %s %s.', idx, total, action, uuid)

            try:
                self.harvest_one(uuid, solr_id, force=force)
                seen.add(uuid)

                if solr_id:
                    self.report.updated += [uuid]
                else:
                    self.report.added += [uuid]

            except Exception:
                self.report.failed += [uuid]
                logger.exception('Error occured for: %s', uuid)

        added = set(self.report.added)
        updated = set(self.report.updated)
        failed = set(self.report.failed)
        missing_treaties = set(self.report.missing_treaties)

        logger.info(
            'Harvest complete! '
            'Added: %s. Updated: %s. Failed: %s. Missing treaties: %s',
            len(added), len(updated), len(failed), len(missing_treaties)
        )

        logger.info('Added: %s', added)
        logger.info('Updated: %s', updated)
        logger.info('Failed: %s', failed)
        logger.info('Missing treaties: %s', missing_treaties)

    def harvest_treaty(self, name=None, uuid=None, force=False, start=0):
        if force:
            logger.warning('Forcing update of all treaty decisions!')

        logger.info('Harvesting decisions for treaty: %s', name or uuid)

        # will fetch nodes until the remote server returns no results
        json_nodes = itertools.takewhile(
            bool, get_node(self.decision_url, self.per_page, start=start, treaty_uuid=uuid)
        )
        matched = [
            node for node in json_nodes if
            (name and node.get('treaty') == name) or
            (uuid and node.get('treaty_uuid') == uuid)
        ]

        updateable = list(filter(bool, [
            needs_update(self.solr, node, force=force)
            for node in matched
        ]))

        self.harvest_list(updateable, force=force)

    def harvest(self, start=0, force=False):
        logger.info('[COP decision] Harvesting started.')
        # will fetch nodes until the remote server returns no results
        json_nodes = itertools.takewhile(
            bool, get_node(self.decision_url, self.per_page, start=start, max_pages=self.max_pages))

        if force:
            logger.warning('Forcing update of all decisions!')

        updateable = list(filter(bool, [
            needs_update(self.solr, node, force=force)
            for node in json_nodes
        ]))

        self.harvest_list(updateable, force=force)
        logger.info('[COP decision] Harvesting finished.')
