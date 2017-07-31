"""Import module."""

from django.conf import settings
from optparse import make_option
import argparse
import logging

from django.core.management.base import BaseCommand

from ecolex.management.definitions import OBJ_TYPES
from ecolex.management.definitions import COURT_DECISION
from ecolex.management.definitions import TREATY
from ecolex.management.definitions import LITERATURE
from ecolex.management.definitions import COP_DECISION
from ecolex.management.definitions import LEGISLATION

from ecolex.management.commands.court_decision import CourtDecisionImporter
from ecolex.management.commands.treaty import TreatyImporter
from ecolex.management.commands.legislation import LegislationImporter
from ecolex.management.commands.literature import LiteratureImporter
from ecolex.management.commands import cop_decision
from ecolex.management.commands import cop_decision2
from ecolex.management.commands.logging import LOG_DICT

logging.config.dictConfig(LOG_DICT)
import_logger = logging.getLogger(__name__)

CLASS_MAPPING = {
    'decision_odata': cop_decision.CopDecisionImporter, # old implementation
    COP_DECISION: cop_decision2.CopDecisionImporter,
    COURT_DECISION: CourtDecisionImporter,
    TREATY: TreatyImporter,
    LITERATURE: LiteratureImporter,
    LEGISLATION: LegislationImporter,
}


class Command(BaseCommand):
    """Custom command for data indexing from different endpoints."""

    help = 'Import and index ecolex data'

    option_list = BaseCommand.option_list + (
        make_option('--obj-type', choices=OBJ_TYPES),
        make_option('--test', action='store_true', default=False),
        make_option('--batch-size', type=int, default=10),
        make_option('--update-status', action='store_true'),
        make_option('--update-text', action='store_true'),
        make_option('--reindex', action='store_true'),
        make_option('--force', action='store_true'),
        make_option('--decId', type=str),
        make_option('--treaty', type=str),
        make_option('--treaty_uuid', type=str),
        make_option('--start_page', type=int, default=1),
    )

    def handle(self, *args, **options):
        parser = argparse.ArgumentParser(description='Import data into Solr.')
        parser.add_argument('import')
        parser.add_argument('obj_type', choices=OBJ_TYPES)
        parser.add_argument('--test', action='store_true')
        parser.add_argument('--batch-size', type=int)
        parser.add_argument('--update-status', action='store_true')
        parser.add_argument('--update-text', action='store_true')
        parser.add_argument('--reindex', action='store_true')
        parser.add_argument('--force', action='store_true')
        parser.add_argument('--decId', type=str)
        parser.add_argument('--treaty', type=str)
        parser.add_argument('--treaty_uuid', type=str)
        parser.add_argument('--start_page', type=int)
        parser.set_defaults(test=False, batch_size=1, default=1)
        args = parser.parse_args()

        config = settings.SOLR_IMPORT
        importer_config = config['common']
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
        elif args.decId:
            importer.harvest_one(args.decId)
        elif args.treaty or args.treaty_uuid:
            importer.harvest_treaty(
                name=args.treaty,
                uuid=args.treaty_uuid,
                start=args.start_page,
                force=args.force,
            )
        elif args.obj_type == 'decision':
            importer.harvest(start=args.start_page, force=args.force)
        else:
            importer.harvest(args.batch_size)
