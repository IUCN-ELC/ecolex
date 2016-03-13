from django.forms import (
    Form,
    BooleanField, CharField, MultipleChoiceField,
    TextInput,
)

from ecolex.definitions import DOC_TYPE


class SearchForm(Form):
    q = CharField(initial='', widget=TextInput(
        attrs={'id': 'search', 'class': 'form-control', 'autofocus': True,
               'placeholder': "Search in record and full text"}))
    type = MultipleChoiceField(choices=DOC_TYPE)

    tr_type = MultipleChoiceField()
    tr_field = MultipleChoiceField()
    tr_status = MultipleChoiceField()
    tr_place_of_adoption = MultipleChoiceField()
    tr_depository = MultipleChoiceField()
    tr_depository_and_ = BooleanField()

    dec_type = MultipleChoiceField()
    dec_status = MultipleChoiceField()
    dec_treaty = MultipleChoiceField()

    cd_type = MultipleChoiceField()
    cd_territorial_subdivision = MultipleChoiceField()

    lit_type = MultipleChoiceField()
    lit_type2 = MultipleChoiceField()
    lit_author = MultipleChoiceField()
    lit_author_and_ = BooleanField()
    lit_serial = MultipleChoiceField()
    lit_publisher = MultipleChoiceField()

    leg_type = MultipleChoiceField()
    leg_territorial = MultipleChoiceField()
    leg_status = MultipleChoiceField()

    subject = MultipleChoiceField()
    subject_and_ = BooleanField()
    keyword = MultipleChoiceField()
    keyword_and_ = BooleanField()
    country = MultipleChoiceField()
    country_and_ = BooleanField()
    region = MultipleChoiceField()
    region_and_ = BooleanField()
    language = MultipleChoiceField()
    language_and_ = BooleanField()
    yearmin = CharField()
    yearmax = CharField()

    sortby = CharField(initial='')

    def _has_document_type(self, doctype):
        return doctype in self.data.get('type', [])

    def has_treaty(self):
        return self._has_document_type('treaty')

    def has_decision(self):
        return self._has_document_type('decision')

    def has_literature(self):
        return self._has_document_type('literature')

    def has_legislation(self):
        return self._has_document_type('legislation')

    def has_court_decision(self):
        return self._has_document_type('court_decision')
