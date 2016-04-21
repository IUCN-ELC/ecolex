"""Import module."""

from optparse import make_option
import argparse
import configparser
import logging

from django.core.management.base import BaseCommand

from ecolex.management.definitions import OBJ_TYPES, COURT_DECISION, TREATY
from ecolex.management.definitions import LITERATURE, COP_DECISION, LEGISLATION
from ecolex.management.commands.court_decision import CourtDecisionImporter
from ecolex.management.commands.treaty import TreatyImporter
from ecolex.management.commands.legislation import LegislationImporter
from ecolex.management.commands.literature import LiteratureImporter
from ecolex.management.commands.cop_decision import CopDecisionImporter
from ecolex.management.commands.logging import LOG_DICT

logging.config.dictConfig(LOG_DICT)
import_logger = logging.getLogger(__name__)

CLASS_MAPPING = {
    COURT_DECISION: CourtDecisionImporter,
    TREATY: TreatyImporter,
    LITERATURE: LiteratureImporter,
    COP_DECISION: CopDecisionImporter,
    LEGISLATION: LegislationImporter,
}


class Command(BaseCommand):
    """Custom command for data indexing from different endpoints."""

    help = 'Import and index ecolex data'

    option_list = BaseCommand.option_list + (
        make_option('--obj-type', choices=OBJ_TYPES),
        make_option('--config'),
        make_option('--test', action='store_true', default=False),
        make_option('--batch-size', type=int, default=10),
        make_option('--update-status', action='store_true'),
        make_option('--update-text', action='store_true'),
        make_option('--reindex', action='store_true'),
    )

    def handle(self, *args, **options):
        parser = argparse.ArgumentParser(description='Import data into Solr.')
        parser.add_argument('import')
        parser.add_argument('obj_type', choices=OBJ_TYPES)
        parser.add_argument('--config', required=True)
        parser.add_argument('--test', action='store_true')
        parser.add_argument('--batch-size', type=int)
        parser.add_argument('--update-status', action='store_true')
        parser.add_argument('--update-text', action='store_true')
        parser.add_argument('--reindex', action='store_true')
        parser.set_defaults(test=False, batch_size=1)
        args = parser.parse_args()

        config = configparser.RawConfigParser()
        config.read(args.config)

        importer_config = config['default']
        importer_config.update(config[args.obj_type])
        importer = CLASS_MAPPING[args.obj_type](importer_config)

        if args.test:
            if importer.test():
                import_logger.info('Test for {} passed.'.format(args.obj_type))
            else:
                import_logger.warn('Test for {} failed.'.format(args.obj_type))
        elif args.update_status:
            importer.update_status()
        elif args.update_text:
            importer.update_full_text()
        elif args.reindex:
            importer.reindex_failed()
        else:
            importer.harvest(args.batch_size)
