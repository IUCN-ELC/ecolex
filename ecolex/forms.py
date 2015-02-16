from django.forms import Form, CharField, MultipleChoiceField, TextInput

DOC_TYPE = (
    ('treaty', "Treaty"),
    ('decision', "Decision"),
)


class SearchForm(Form):
    q = CharField(initial='', widget=TextInput(
        attrs={'id': 'search', 'class': 'form-control', 'autofocus': True,
               'placeholder': "Search for Treaties, Legislation, Court decisions, Literature, COP decisions"}))
    type = MultipleChoiceField(choices=DOC_TYPE)

    tr_type = MultipleChoiceField()
    tr_field = MultipleChoiceField()
    tr_party = MultipleChoiceField()
    tr_subject = MultipleChoiceField()

    keyword = MultipleChoiceField()
    yearmin = CharField()
    yearmax = CharField()

    dec_type = MultipleChoiceField()
    dec_status = MultipleChoiceField()
    dec_treaty = MultipleChoiceField()

    sortby = CharField(initial='')

    def has_treaty(self):
        return 'treaty' in self.data.get('type', []) or any(
            self.data.get(f) for f in
            ('tr_type', 'tr_field', 'tr_party', 'tr_subject')
        )

    def has_decision(self):
        return 'decision' in self.data.get('type', []) or any(
            self.data.get(f) for f in
            ('dec_type', 'dec_status', 'dec_treaty')
        )
