from django.forms import Form, CharField, MultipleChoiceField, TextInput

from ecolex.definitions import DOC_TYPE, DOC_TYPE_FILTER_MAPPING


class SearchForm(Form):
    OPERATION_OPTIONS = (
        ('AND', 'AND'),
    )
    q = CharField(initial='', widget=TextInput(
        attrs={'id': 'search', 'class': 'form-control', 'autofocus': True,
               'placeholder': "Search for Treaties, Legislation, Court "
                              "decisions, Literature, COP decisions"}))
    type = MultipleChoiceField(choices=DOC_TYPE)

    tr_type = MultipleChoiceField()
    tr_field = MultipleChoiceField()
    tr_status = MultipleChoiceField()
    tr_place_of_adoption = MultipleChoiceField()
    tr_depository = MultipleChoiceField()
    tr_depository_op = MultipleChoiceField(choices=OPERATION_OPTIONS)

    dec_type = MultipleChoiceField()
    dec_status = MultipleChoiceField()
    dec_treaty = MultipleChoiceField()

    cd_type = MultipleChoiceField()
    cd_territorial_subdivision = MultipleChoiceField()

    lit_type = MultipleChoiceField()
    lit_author = MultipleChoiceField()
    lit_author_op = MultipleChoiceField(choices=OPERATION_OPTIONS)
    lit_serial = MultipleChoiceField()
    lit_publisher = MultipleChoiceField()

    leg_type = MultipleChoiceField()
    leg_territorial = MultipleChoiceField()
    leg_status = MultipleChoiceField()

    subject = MultipleChoiceField()
    subject_op = MultipleChoiceField(choices=OPERATION_OPTIONS)
    keyword = MultipleChoiceField()
    keyword_op = MultipleChoiceField(choices=OPERATION_OPTIONS)
    country = MultipleChoiceField()
    country_op = MultipleChoiceField(choices=OPERATION_OPTIONS)
    region = MultipleChoiceField()
    region_op = MultipleChoiceField(choices=OPERATION_OPTIONS)
    language = MultipleChoiceField()
    language_op = MultipleChoiceField(choices=OPERATION_OPTIONS)
    yearmin = CharField()
    yearmax = CharField()

    sortby = CharField(initial='')

    def _has_document_type(self, doctype):
        return (not self.data.get('type') and any(
            self.data.get(f) for f in DOC_TYPE_FILTER_MAPPING[doctype].values()
        )) or (doctype in self.data.get('type', []))

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
