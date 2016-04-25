from datetime import datetime
from django.conf import settings
from io import BytesIO
import json
import logging
import pysolr
import os
import re
import requests
import hashlib
import random

from ecolex.management.commands.logging import LOG_DICT
from ecolex.management.definitions import (
    COP_DECISION, COURT_DECISION, LEGISLATION, LITERATURE, TREATY, COPY_FIELDS,
)


logging.config.dictConfig(LOG_DICT)
logger = logging.getLogger('import')


def get_content_length_from_url(url):
    if 'http' not in url:
        url = 'http://' + url
    try:
        response = requests.head(url, timeout=10)
        return int(response.headers['Content-Length'])
    except:
        if settings.DEBUG:
            logger.exception('Error checking file {}'.format(url))
        return None


def get_file_from_url(url):
    if 'http' not in url:
        url = 'http://' + url
    try:
        response = requests.get(url, timeout=60)
    except:
        if settings.DEBUG:
            logger.exception('Error downloading file {}'.format(url))
        return None
    if response.status_code != 200:
        logger.error('Invalid return code {} for {}'.format(
            response.status_code, url))
        return None

    if (response.headers.get('Content-Length') == '675' and
            '404' in response.content.decode('UTF-8')):
        logger.error('Potential soft 404 for {}'.format(url))
        return None

    doc_content_bytes = response.content
    file_obj = BytesIO()
    file_obj.write(doc_content_bytes)
    setattr(file_obj, 'name', url)
    if response.headers.get('Content-Type'):
        content_type = response.headers.get('Content-Type').split(';')[0]
        setattr(file_obj, 'content_type', content_type)
    file_obj.seek(0)
    return file_obj


def get_date(text):
    datestr = re.findall("Date\((.*)\)", text)[0][:-3]
    dt = datetime.fromtimestamp(int(datestr))
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def valid_date(date):
    date_info = date.split('-')
    if len(date_info) != 3:
        return False
    if date_info[0] == '0000' or date_info[1] == '00' or date_info[2] == '00':
        return False
    return True


def format_date(date):
    return date + "T00:00:00Z"


def generate_fao_api_key():
    seed = str(random.getrandbits(256)).encode('utf-8')
    return hashlib.sha256(seed).hexdigest()


def get_json_from_url(url, headers={}):
    resp = requests.get(url, headers=headers)
    if not resp.status_code == 200:
        raise RuntimeError('Unexpected request status code')

    try:
        return json.loads(resp.text)
    except ValueError as ex:
        # TODO: replace this with logging
        print(url, ex)


def get_content_from_url(url):
    resp = requests.get(url)
    if not resp.status_code == 200:
        raise RuntimeError('Unexpected request status code')
    return resp.content


def cleanup_copyfields(doc):
    for field in COPY_FIELDS:
        doc[field] = None
    return doc


class EcolexSolr(object):

    # This is just an idea, might not be accurate
    ID_MAPPING = {
        COP_DECISION: 'decId',
        COURT_DECISION: 'cdLeoId',
        TREATY: 'trElisId',
        LITERATURE: 'litId',
        LEGISLATION: 'legId',
    }

    def __init__(self, timeout=60):
        solr_uri = os.environ.get('SOLR_URI')
        if not solr_uri:
            raise RuntimeError('SOLR_URI environment variable not set.')

        self.solr = pysolr.Solr(solr_uri, timeout=timeout)

    def search(self, obj_type, id_value):
        id_field = self.ID_MAPPING.get(obj_type)
        result = self.search_all(id_field, id_value)
        return result[0] if result else None

    def search_all(self, key, value='*', **kwargs):
        query = '{}:{}'.format(key, value)
        result = self.solr.search(query, **kwargs)
        if result.hits:
            return result.docs

    def add(self, obj):
        try:
            self.solr.add([obj])
            # self.solr.optimize()
        except pysolr.SolrError as e:
            if settings.DEBUG:
                logging.getLogger('solr').exception(e)
            return False
        return True

    def add_bulk(self, bulk_obj):
        try:
            self.solr.add(bulk_obj)
            # self.solr.optimize()
        except pysolr.SolrError as e:
            if settings.DEBUG:
                logging.getLogger('solr').exception(e)
            return False
        return True

    def extract(self, file):
        args = {}
        if getattr(file, 'content_type', None):
            args.update({'stream.type': getattr(file, 'content_type', None)})
        try:
            response = self.solr.extract(file, **args)
        except pysolr.SolrError as e:
            logger.error('Error extracting text from file %s' % (file.name,))
            if settings.DEBUG:
                logging.getLogger('solr').exception(e)
            return ''
        return response['contents']
