"""
These models define the documents' behaviour that could not be included in the
schema. They will eventually replace actual solr_models.
"""
from datetime import date
from django.core.urlresolvers import reverse

DEFAULT_TITLE = 'Unknown Document'
INVALID_DATE = date(2, 11, 30)


class BaseModel(object):
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class DocumentModel(BaseModel):
    @property
    def details_url(self):
        return reverse(self.URL_NAME, kwargs={'id': self.id})


class Treaty(DocumentModel):
    URL_NAME = 'treaty_details'
    EVENTS_NAMES = {
        'acceptance_approval': 'Acceptance/approval',
        'accession_approbation': 'Accession/approbation',
        'consent_to_be_bound': 'Consent to be bound',
        'definite_signature': 'Definite signature',
        'entry_into_force': 'Entry into force',
        'participation': 'Participation',
        'provisional_application': 'Provisional application',
        'ratification': 'Ratification',
        'ratification_group': 'Ratification *',
        'reservation': 'Reservation',
        'simple_signature': 'Simple signature',
        'succession': 'Succession',
        'withdrawal': 'Withdrawal',
    }
    EVENTS_ORDER = [
        'entry_into_force',
        'ratification_group',
        'simple_signature',
        'provisional_application',
        'participation',
        'reservation',
        'withdrawal',
    ]

    @property
    def title(self):
        return (self.paper_title_of_text or
                self.paper_title_of_text_other or
                self.title_of_text_short or
                [DEFAULT_TITLE])

    @property
    def date(self):
        return (self.date_of_text or
                self.date_of_entry or
                self.date_of_modification)

    @property
    def parties_events(self):
        events = set().union(*[party.events for party in self.parties])
        return sorted(events, key=lambda x: self.EVENTS_ORDER.index(x))


class TreatyParty(BaseModel):
    FIELD_GROUPS = {
        'ratification_group': [
            'ratification',
            'accession_approbation',
            'acceptance_approval',
            'succession',
            'consent_to_be_bound',
            'definite_signature',
        ]
    }
    GROUPED_FIELDS = {field: group
                      for group, fields in FIELD_GROUPS.items()
                      for field in fields}

    def __init__(self, **kwargs):
        self.country = kwargs.pop('country')
        self.events = []

        # This could be prettier
        for k, v in kwargs.items():
            key = k
            v = v if v != INVALID_DATE else None
            value = {'date': v, 'details': k}
            if k in self.GROUPED_FIELDS:
                key = self.GROUPED_FIELDS[k]
                value['details'] = k
                value['index'] = self.FIELD_GROUPS[key].index(k) + 1
            setattr(self, key, value)
            self.events.append(key)


class Decision(DocumentModel):
    URL_NAME = 'decision_details'

    @property
    def title(self):
        return self.short_title

    @property
    def date(self):
        return self.publish_date or self.update_date


class Legislation(DocumentModel):
    URL_NAME = 'legislation_details'

    @property
    def title(self):
        return self.short_title or self.long_title


class CourtDecision(DocumentModel):
    URL_NAME = 'court_decision_details'

    @property
    def title(self):
        return self.title_of_text

    @property
    def date(self):
        return self.date_of_text


class Literature(DocumentModel):
    URL_NAME = 'literature_details'

    @property
    def title(self):
        return (self.paper_title_of_text or
                self.long_title or
                self.title_of_text_transl or
                self.title_of_text_short)

    @property
    def authors(self):
        return (self.author_article or
                self.author or
                self.corp_author_article or
                self.corp_author)

    @property
    def parent_title(self):
        parent_title = self.long_title or self.serial_title
        if parent_title != self.title:
            return parent_title

    def publication_date(self):
        return self.date_of_text_ser or self.date_of_text
