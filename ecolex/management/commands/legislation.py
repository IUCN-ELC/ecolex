import json
import logging
import logging.config

from django.conf import settings
from pysolr import SolrError

from ecolex.management.commands.logging import LOG_DICT
from ecolex.management.definitions import LEGISLATION
from ecolex.management.utils import EcolexSolr, get_file_from_url, cleanup_copyfields

from ecolex.management.utils import get_content_length_from_url
from ecolex.models import DocumentText


logging.config.dictConfig(LOG_DICT)
logger = logging.getLogger('legislation_import')


class LegislationImporter(object):

    def __init__(self, config):
        self.solr_timeout = config.get('solr_timeout')
        self.solr = EcolexSolr(self.solr_timeout)
        logger.info('Started legislation manager')

    def update_full_text(self):
        while True:
            count = (DocumentText.objects.filter(
                     status=DocumentText.INDEXED, doc_type=LEGISLATION)
                     .exclude(url__isnull=True)).count()
            objs = (DocumentText.objects.filter(
                    status=DocumentText.INDEXED, doc_type=LEGISLATION)
                    .exclude(url__isnull=True))[:100]
            logger.info('%s records remaining' % (count,))
            if count == 0:
                break
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
                    legislation = self.solr.search(LEGISLATION, obj.doc_id)
                    if legislation:
                        legislation = cleanup_copyfields(legislation)
                except SolrError as e:
                    logger.error('Error reading legislation %s' % (obj.doc_id,))
                    if settings.DEBUG:
                        logging.getLogger('solr').exception(e)
                    continue

                if not legislation:
                    logger.error('Failed to find legislation %s' % (obj.doc_id))
                    continue

                legislation['legText'] = text
                result = self.solr.add(legislation)
                if result:
                    logger.info('Success download & indexed: %s' % (obj.doc_id,))
                    obj.status = DocumentText.FULL_INDEXED
                    obj.doc_size = doc_size
                    obj.text = text
                    obj.save()
                else:
                    logger.error('Failed doc extract %s %s' % (obj.url,
                                                               legislation['id']))

    def reindex_failed(self):
        objs = DocumentText.objects.filter(
            status=DocumentText.INDEX_FAIL, doc_type=LEGISLATION)
        if objs.count() > 0:
            for obj in objs:
                legislation = json.loads(obj.parsed_data)
                # Check if already present in Solr
                if 'id' not in legislation:
                    try:
                        old_legislation = self.solr.search(LEGISLATION, obj.doc_id)
                        legislation['id'] = old_legislation['id']
                        legislation = cleanup_copyfields(legislation)
                    except SolrError as e:
                        logger.error('Error reading legislation %s' % (obj.doc_id,))
                        if settings.DEBUG:
                            logging.getLogger('solr').exception(e)
                        continue
                result = self.solr.add(legislation)
                if result:
                    obj.status = DocumentText.INDEXED
                    obj.parsed_data = ''
                    obj.save()
                    logger.info('Success indexing: %s' % (obj.doc_id,))
                else:
                    logger.error('Failed to index: %s' % (obj.doc_id,))
