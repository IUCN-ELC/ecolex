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

    tr_type_of_document = MultipleChoiceField()
    tr_field_of_application = MultipleChoiceField()
    tr_status = MultipleChoiceField()
    tr_place_of_adoption = MultipleChoiceField()
    tr_depository = MultipleChoiceField()

    dec_type_of_document = MultipleChoiceField()
    dec_status = MultipleChoiceField()
    dec_treaty_name = MultipleChoiceField()

    cd_type_of_document = MultipleChoiceField()
    cd_territorial_subdivision = MultipleChoiceField()

    lit_type_of_text = MultipleChoiceField()
    lit_author = MultipleChoiceField()
    lit_orig_serial_title = MultipleChoiceField()
    lit_publisher = MultipleChoiceField()

    leg_type_of_document = MultipleChoiceField()
    leg_territorial_subdivision = MultipleChoiceField()
    leg_status = MultipleChoiceField()

    xsubjects = MultipleChoiceField()
    xkeywords = MultipleChoiceField()
    xcountry = MultipleChoiceField()
    xregion = MultipleChoiceField()
    xlanguage = MultipleChoiceField()
    yearmin = CharField()
    yearmax = CharField()

    sortby = CharField(initial='')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # add AND-able fields
        for f in defs._AND_OP_FACETS:
            fname = self.get_and_field_name_for(f)
            self.fields[fname] = BooleanField()

        # no field is required
        for field in self.fields.values():
            field.required = False

    @staticmethod
    def get_and_field_name_for(field):
        return defs._AND_OP_FIELD_PATTERN % field

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
