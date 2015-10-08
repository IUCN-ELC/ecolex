from datetime import datetime, timedelta
import json
import requests

from utils import EcolexSolr

COURT_DECISIONS_URL = 'http://leo.informea.org/ws/court-decisions'
COURT_DECISION_DETAILS_URL = 'http://leo.informea.org/export/node/{uuid}'
UPDATE_INTERVAL = 1  # expressed in hours
DATE_FORMAT = '%Y-%m-%d %H:%M:%S'


def get_content(url):
    resp = requests.get(url)
    if not resp.status_code == 200:
        raise RuntimeError('Unexpected request status code')

    return json.loads(resp.text)


def get_decision(uuid):
    url = COURT_DECISION_DETAILS_URL.format(uuid=uuid)
    return get_content(url)


def get_decisions():
    return get_content(COURT_DECISIONS_URL)


def _is_recent(decision):
    # TODO see if this function is still useful; if not, erase it
    # TODO use timezone info (pytz library)
    date_str = decision['field_date_of_modification']['und'][0]['value']
    date_of_modification = datetime.strptime(date_str, DATE_FORMAT)
    last_update = datetime.now() - timedelta(hours=UPDATE_INTERVAL)
    return date_of_modification > last_update


def is_recent(decision):
    changed = datetime.fromtimestamp(float(decision['changed'] or '0'))
    last_update = datetime.now() - timedelta(hours=UPDATE_INTERVAL)
    return changed > last_update


def update_decision(solr, decision):
    uuid = decision['uuid']
    new_decision = get_decision(uuid)
    existing_decision = solr.search(solr.COURT_DECISION, new_decision['nid'])

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
