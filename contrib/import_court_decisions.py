from datetime import datetime, timedelta
import json
import requests

from utils import EcolexSolr

COURT_DECISIONS_URL = 'http://leo.informea.org/ws/court-decisions'
COURT_DECISION_DETAILS_URL = 'http://leo.informea.org/export/node/{nid}'
UPDATE_INTERVAL = 1  # expressed in hours
DATE_FORMAT = '%Y-%m-%d %H:%M:%S'


def get_decisions(node_id=None):
    url = COURT_DECISION_DETAILS_URL.format(nid=node_id) if node_id \
        else COURT_DECISIONS_URL
    resp = requests.get(url)
    if not resp.status_code == 200:
        raise RuntimeError('Unexpected request status code')

    decisions = json.loads(resp.text)
    return decisions


def is_recent(decision):
    # TODO use timezone info (pytz library)
    date_str = decision['field_date_of_modification']['und'][0]['value']
    date_of_modification = datetime.strptime(date_str, DATE_FORMAT)
    last_update = datetime.now() - timedelta(hours=UPDATE_INTERVAL)
    return date_of_modification > last_update


def update_decision(solr, decision):
    node_id = decision['nid']
    new_decision = get_decisions(node_id)
    existing_decision = solr.search(solr.COURT_DECISION, node_id)

    if not existing_decision:
        # TODO must actually update schema and format decision accordingly
        solr.add(new_decision)
    if existing_decision and is_recent(new_decision):
        # By using the same ID, Solr will know this is an update operation
        new_decision['id'] = existing_decision['id']
        solr.add(new_decision)


if __name__ == '__main__':
    solr = EcolexSolr()
    decisions = get_decisions()

    for decision in decisions:
        update_decision(solr, decision)
