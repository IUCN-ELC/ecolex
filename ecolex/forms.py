from django.forms import Form, CharField, MultipleChoiceField, TextInput

from ecolex.definitions import DOC_TYPE


class SearchForm(Form):
    q = CharField(initial='', widget=TextInput(
        attrs={'id': 'search', 'class': 'form-control', 'autofocus': True,
               'placeholder': "Search for Treaties, Legislation, Court decisions, Literature, COP decisions"}))
    type = MultipleChoiceField(choices=DOC_TYPE)

    tr_type = MultipleChoiceField()
    tr_field = MultipleChoiceField()
    tr_party = MultipleChoiceField()
    tr_region = MultipleChoiceField()
    tr_basin = MultipleChoiceField()
    tr_subject = MultipleChoiceField()
    tr_language = MultipleChoiceField()

    keyword = MultipleChoiceField()
    yearmin = CharField()
    yearmax = CharField()

    dec_type = MultipleChoiceField()
    dec_status = MultipleChoiceField()
    dec_treaty = MultipleChoiceField()

    lit_type = MultipleChoiceField()

    sortby = CharField(initial='')

    def has_treaty(self):
        TREATY_FACETS = (
            'tr_type', 'tr_field', 'tr_party', 'tr_subject',
            'tr_basin', 'tr_region', 'tr_language'
        )

        return (not self.data.get('type') and any(
            self.data.get(f) for f in TREATY_FACETS
        )) or ('treaty' in self.data.get('type', []))

    def has_decision(self):
        DECISION_FACETS = (
            'dec_type', 'dec_status', 'dec_treaty'
        )

        return (not self.data.get('type') and any(
            self.data.get(f) for f in DECISION_FACETS
        )) or ('decision' in self.data.get('type', []))
