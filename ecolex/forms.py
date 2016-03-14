from django.forms import (
    Form,
    BooleanField, CharField, MultipleChoiceField,
    TextInput,
)

from ecolex import definitions as defs


class SearchForm(Form):
    q = CharField(initial='', widget=TextInput(
        attrs={'id': 'search', 'class': 'form-control', 'autofocus': True,
               'placeholder': "Search in record and full text"}))
    type = MultipleChoiceField(choices=defs.DOC_TYPE)

    tr_type = MultipleChoiceField()
    tr_field = MultipleChoiceField()
    tr_status = MultipleChoiceField()
    tr_place_of_adoption = MultipleChoiceField()
    tr_depository = MultipleChoiceField()

    dec_type = MultipleChoiceField()
    dec_status = MultipleChoiceField()
    dec_treaty = MultipleChoiceField()

    cd_type = MultipleChoiceField()
    cd_territorial_subdivision = MultipleChoiceField()

    lit_type = MultipleChoiceField()
    lit_type2 = MultipleChoiceField()
    lit_author = MultipleChoiceField()
    lit_serial = MultipleChoiceField()
    lit_publisher = MultipleChoiceField()

    leg_type = MultipleChoiceField()
    leg_territorial = MultipleChoiceField()
    leg_status = MultipleChoiceField()

    subject = MultipleChoiceField()
    keyword = MultipleChoiceField()
    country = MultipleChoiceField()
    region = MultipleChoiceField()
    language = MultipleChoiceField()
    yearmin = CharField()
    yearmax = CharField()

    sortby = CharField(initial='')


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # add AND-able fields
        for f in defs._AND_OP_FACETS:
            fname = defs._AND_OP_FIELD_PATTERN % f
            self.fields[fname] = BooleanField()

        # no field is required
        for field in self.fields.values():
            field.required = False

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
