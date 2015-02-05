from django.forms import Form, CharField, MultipleChoiceField, TextInput

DOC_TYPE = (
    ('treaty', "Treaty"),
    ('decision', "Decision"),
)


class SearchForm(Form):
    q = CharField(initial='', widget=TextInput(
        attrs={'id': 'search', 'class': 'form-control', 'autofocus': True,
               'placeholder': "Treaties, Legislation, Court decisions, Literature, COP decisions"}))
    type = MultipleChoiceField(choices=DOC_TYPE)

    tr_type = MultipleChoiceField()
    tr_field = MultipleChoiceField()
    tr_party = MultipleChoiceField()
    tr_subject = MultipleChoiceField()

    keyword = MultipleChoiceField()
