import json
import logging
from datetime import datetime

from django.conf import settings
from pysolr import SolrError

from ecolex.management.utils import EcolexSolr, cleanup_copyfields
from ecolex.management.utils import get_dict_from_json
from ecolex.models import DocumentText


class BaseImporter(object):

    def __init__(self, config, logger, doc_type):
        self.doc_type = doc_type
        self.solr_timeout = config.get('solr_timeout')
        self.regions_json = config.get('regions_json')
        self.languages_json = config.get('languages_json')
        self.keywords_json = config.get('keywords_json')
        self.subjects_json = config.get('subjects_json')

        self.regions = self._get_regions()
        self.languages = self._get_languages()
        self.keywords = self._get_keywords()
        self.subjects = self._get_subjects()
        self.treaties = get_dict_from_json(config.get('treaties_json'))
        self.solr = EcolexSolr(self.solr_timeout)
        self.logger = logger


    def _get_regions(self):
        with open(self.regions_json, encoding='utf-8') as f:
            regions = json.load(f)
        return regions

    def _get_languages(self):
        with open(self.languages_json, encoding='utf-8') as f:
            languages_codes = json.load(f)
        return languages_codes

    def _get_keywords(self):
        with open(self.keywords_json, encoding='utf-8') as f:
            keywords = json.load(f)
        return keywords

    def _get_subjects(self):
        with open(self.subjects_json, encoding='utf-8') as f:
            subjects = json.load(f)
        return subjects

    def _set_values_from_dict(self, data, field, local_dict):
        langs = ['en', 'fr', 'es']
        fields = ['{}_{}'.format(field, lang_code) for lang_code in langs]
        new_values = {x: [] for x in langs}
        if all(map((lambda x: x in data), fields)):
            values = zip(*[data[x] for x in fields])
            for val_en, val_fr, val_es in values:
                dict_values = local_dict.get(val_en.lower())
                if dict_values:
                    new_values['en'].append(dict_values['en'])
                    dict_value_fr = dict_values['fr']
                    dict_value_es = dict_values['es']
                    if val_fr != dict_value_fr:
                        self.logger.debug(
                            '{}_fr name different: {} {} {}'.format(
                                field,
                                data[self.id_field], val_fr,
                                dict_value_fr
                            ).encode('utf-8')
                        )
                    new_values['fr'].append(dict_value_fr)

                    if val_es != dict_value_es:
                        self.logger.debug(
                            '{}_es name different: {} {} {}'.format(
                                field,
                                data[self.id_field],
                                val_es,
                                dict_value_es
                            ).encode('utf-8')
                        )
                    new_values['es'].append(dict_value_es)
                else:
                    self.logger.warning(
                        'New {} name: {} {} {} {}'.format(
                            field,
                            data[self.id_field],
                            val_en,
                            val_fr,
                            val_es
                        ).encode('utf-8')
                    )
                    new_values['en'].append(val_en)
                    new_values['fr'].append(val_fr)
                    new_values['es'].append(val_es)
        elif fields[0] in data:
            values_en = data.get(fields[0], []) or []
            for val_en in values_en:
                dict_values = local_dict.get(val_en.lower())
                if dict_values:
                    for lang in langs:
                        new_values[lang].append(dict_values[lang])
                else:
                    self.logger.warning('New {}_en name: {} {}'.format(
                                        field, data[self.id_field], val_en))
                    new_values['en'].append(val_en)

        for k, v in new_values.items():
            new_values[k] = list(set(v))

        for field in fields:
            data[field] = new_values[field[-2:]]

    def reindex_failed(self):
        objs = DocumentText.objects.filter(
            status=DocumentText.INDEX_FAIL, doc_type=self.doc_type)
        if objs.count() > 0:
            for obj in objs:
                if not obj.parsed_data:
                    continue
                record = json.loads(obj.parsed_data)
                record['updatedDate'] = (datetime.now()
                                         .strftime('%Y-%m-%dT%H:%M:%SZ'))
                # Check if already present in Solr
                if 'id' not in record:
                    try:
                        old_record = self.solr.search(self.doc_type, obj.doc_id)
                        if old_record:
                            record['id'] = old_record['id']
                            record = cleanup_copyfields(record)
                    except SolrError as e:
                        self.logger.error('Error reading %s %s' % (self.doc_type, obj.doc_id,))
                        if settings.DEBUG:
                            logging.getLogger('solr').exception(e)
                        continue
                result = self.solr.add(record)
                if result:
                    obj.status = DocumentText.INDEXED
                    obj.parsed_data = ''
                    obj.save()
                    self.logger.info('Success indexing: %s' % (obj.doc_id,))
                else:
                    self.logger.error('Failed to index: %s' % (obj.doc_id,))
