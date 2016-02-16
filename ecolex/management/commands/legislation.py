import json
import logging
import logging.config

from django.db import transaction

from ecolex.management.commands.logging import LOG_DICT
from ecolex.management.utils import EcolexSolr, get_file_from_url
from ecolex.management.utils import LEGISLATION
from ecolex.models import DocumentText

logging.config.dictConfig(LOG_DICT)
logger = logging.getLogger('import')


class LegislationImporter(object):

    def __init__(self, *args):
        self.solr = EcolexSolr()

        logger.info('Started legislation manager')


    def update_legislation_full_text(self):
        objs = (DocumentText.objects.filter(status=DocumentText.INDEXED)
                .exclude(url__isnull=True))
        for obj in objs:
            logger.info('Downloading: %s' % (obj.url,))
            file_obj = get_file_from_url(obj.url)
            if not file_obj:
                obj.status = DocumentText.INDEXED
                obj.save()
                logger.info('Failed downloading: %s' % (obj.url,))
                continue
            doc_size = file_obj.getbuffer().nbytes
            text = self.solr.extract(file_obj)
            legislation = self.solr.search(LEGISLATION, obj.doc_id)
            legislation['legText'] = text
            result = self.solr.add(legislation)
            logger.info('Success download & indexing: %s' % (obj.url,))
            if result:
                obj.status = DocumentText.FULL_INDEXED
                obj.parsed_data = ''
                obj.doc_size = doc_size
                obj.text = text
                obj.save()
            else:
                logger.info('Failed doc extract %s %s' % (obj.url,
                                                          legislation['id']))


    def reindex_failed_legislations(self):
        objs = DocumentText.objects.filter(status=DocumentText.INDEX_FAIL)
        if objs.count() > 0:
            for obj in objs:
                legislation = json.loads(obj.parsed_data)
                result = self.solr.add(legislation)
                if result:
                    obj.status = DocumentText.INDEXED
                    obj.parsed_data = ''
                    obj.save()
                    logger.info('Success indexing: %s' % (obj))
                else:
                    logger.info('Failed to index: %s' % (obj))
