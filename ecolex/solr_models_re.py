"""
These models define the documents' behaviour that could not be included in the
schema. They will eventually replace actual solr_models.
"""
from django.core.urlresolvers import reverse

DEFAULT_TITLE = 'Unknown Document'


class BaseModel(object):
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    @property
    def details_url(self):
        return reverse(self.URL_NAME, kwargs={'id': self.id})


class Treaty(BaseModel):
    URL_NAME = 'treaty_details'

    @property
    def title(self):
        return self.paper_title_of_text or self.title_of_text or [DEFAULT_TITLE]

    @property
    def date(self):
        return (self.date_of_text or
                self.date_of_entry or
                self.date_of_modification)


class Decision(BaseModel):
    URL_NAME = 'decision_details'

    @property
    def title(self):
        return self.short_title

    @property
    def date(self):
        return self.publish_date or self.update_date


class Legislation(BaseModel):
    URL_NAME = 'legislation_details'

    @property
    def title(self):
        return self.short_title or self.long_title


class CourtDecision(BaseModel):
    URL_NAME = 'court_decision_details'

    @property
    def title(self):
        return self.title_of_text

    @property
    def date(self):
        return self.date_of_text


class Literature(BaseModel):
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
