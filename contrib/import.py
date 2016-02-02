import argparse
import configparser
import logging
import logging.config

from utils import OBJ_TYPES, COURT_DECISION, TREATY, LITERATURE, COP_DECISION
from utils import LEGISLATION
from court_decision import CourtDecisionImporter
from treaty import TreatyImporter
from literature import LiteratureImporter
from cop_decision import CopDecisionImporter
from legislation import update_legislation_full_text
from config.logging import LOG_DICT

logging.config.dictConfig(LOG_DICT)
logger = logging.getLogger(__name__)

CLASS_MAPPING = {
    COURT_DECISION: CourtDecisionImporter,
    TREATY: TreatyImporter,
    LITERATURE: LiteratureImporter,
    COP_DECISION: CopDecisionImporter,
    LEGISLATION: CopDecisionImporter,
}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Import data into Solr.')
    parser.add_argument('obj_type', choices=OBJ_TYPES)
    parser.add_argument('--config', required=True)
    parser.add_argument('--test', action='store_true')
    parser.add_argument('--batch-size', type=int)
    parser.add_argument('--update-status', action='store_true')
    parser.add_argument('--update-text', action='store_true')
    parser.set_defaults(test=False, batch_size=1)
    args = parser.parse_args()

    config = configparser.RawConfigParser()
    config.read(args.config)

    importer_config = config['default']
    importer_config.update(config[args.obj_type])
    importer = CLASS_MAPPING[args.obj_type](importer_config)

    if args.test:
        if importer.test():
            logger.info('Test for {} passed.'.format(args.obj_type))
        else:
            logger.warn('Test for {} failed.'.format(args.obj_type))
    elif args.update_status:
        importer.update_status()
    elif args.update_text:
        update_legislation_full_text()
    else:
        importer.harvest(args.batch_size)
