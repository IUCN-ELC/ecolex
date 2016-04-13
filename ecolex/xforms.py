from functools import partialmethod
from types import MethodType
from django import forms
from django.utils.translation import ugettext as _
from ecolex.lib.schema import fields
from .schema import FIELD_MAP, FILTER_FIELDS, STATS_FIELDS


def _urlencoded(self, value):
    """
    Returns a form field "as a url querystring", with the given value
    replacing the current one.
    """
    form_data = self.form.data.copy()
    if not form_data:
        return ""

    if value == self.field.initial:
        try:
            del form_data[self.name]
        except KeyError:
            pass
    else:
        form_data[self.name] = value

    return form_data.urlencode()

def patched(field):
    """
    Patch the field so that its bound field instance gets a `urlencoded` method.
    """
    _orig_gbf = field.get_bound_field
    def _new_gbf(self, *args, **kwargs):
        bfield = _orig_gbf(*args, **kwargs)
        bfield.urlencoded = MethodType(_urlencoded, bfield)
        return bfield

    field.get_bound_field = MethodType(_new_gbf, field)
    return field


class SearchForm(forms.Form):
    SORT_DEFAULT = ''
    SORT_FIRST = 'first'
    SORT_LAST = 'last'

    SORT_CHOICES = (
        (SORT_DEFAULT, _('relevance')),
        (SORT_FIRST, _('most recent')),
        (SORT_LAST, _('least recent')),
    )

    q = forms.CharField(required=False)
    page = patched(forms.IntegerField(min_value=1, required=False, initial=1))
    sortby = patched(forms.ChoiceField(choices=SORT_CHOICES,
                                       required=False, initial=SORT_DEFAULT))

    def __clean_field_with_initial(self, fname):
        if fname not in self.data or self.cleaned_data[fname] is None:
            return self.fields[fname].initial
        return self.cleaned_data[fname]

    clean_page = partialmethod(__clean_field_with_initial, 'page')
    clean_sortby = partialmethod(__clean_field_with_initial, 'sortby')

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
            elif name == 'type':
                # special-case type to set available choices
                choices = list(FIELD_MAP.keys())
                choices.remove('_')
                field = patched(
                    forms.MultipleChoiceField(choices=zip(choices, choices)))
                new_fields.append(('type', field))
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
