from django import forms
from django.utils.translation import ugettext as _
from ecolex.lib.schema import fields
from .schema import FILTER_FIELDS, STATS_FIELDS


class SearchForm(forms.Form):
    SORT_DEFAULT = ''
    SORT_FIRST = 'first'
    SORT_LAST = 'last'

    SORT_CHOICES = (
        (SORT_DEFAULT, _('relevance')),
        (SORT_FIRST, _('most recent')),
        (SORT_LAST, _('least recent')),
    )

    q = forms.CharField()
    sortby = forms.ChoiceField(choices=SORT_CHOICES)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # dynamically add all filterable fields
        new_fields = []
        and_fields = []
        for name, field in FILTER_FIELDS.items():
            if name in STATS_FIELDS:
                # fields with stats turn into 2 form fields: min and max
                for suffix in ('min', 'max'):
                    new_fields.append(("%s_%s" % (name, suffix),
                                       forms.IntegerField()))
            else:
                # this will be faceted upon. create a choice field
                # (multiple by default)
                if field.form_single_choice:
                    new_fields.append((name,
                                       forms.ChoiceField()))
                else:
                    new_fields.append((name,
                                       forms.MultipleChoiceField()))

                    # if this is a multi-valued field, support AND-ing choices
                    if field.multivalue:
                        and_name = "%s_and_" % name
                        new_fields.append((and_name,
                                           forms.BooleanField()))

                        # queue the fields to reference eachother
                        and_fields.append((name, and_name))

        for name, field in new_fields:
            # nothing is really required
            field.required = False
            self.fields[name] = field

        # reference the AND field from the "parent" field,
        # but do so on the bound field instances
        for name, and_name in and_fields:
            self[name].and_field = self[and_name]
            #self[and_name].parent_field = self[name]
