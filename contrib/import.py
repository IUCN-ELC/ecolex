import argparse
import configparser

from utils import OBJ_TYPES, COURT_DECISION, TREATY
from court_decision import CourtDecisionImporter
from treaty import TreatyImporter

CLASS_MAPPING = {
    COURT_DECISION: CourtDecisionImporter,
    TREATY: TreatyImporter,
}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Import data into Solr.')
    parser.add_argument('obj_type', choices=OBJ_TYPES)
    parser.add_argument('--config', required=True)
    parser.add_argument('--test', action='store_true')
    parser.add_argument('--batch-size', type=int)
    parser.add_argument('--update-status', action='store_true')
    parser.set_defaults(test=False, batch_size=1)
    args = parser.parse_args()

    config = configparser.RawConfigParser()
    config.read(args.config)

    importer_config = config['default']
    importer_config.update(config[args.obj_type])
    importer = CLASS_MAPPING[args.obj_type](importer_config)

    if args.test:
        if importer.test():
            print('Text passed')
        else:
            print('Text failed')
    elif args.update_status:
        importer.update_status()
    else:
        importer.harvest(args.batch_size)
