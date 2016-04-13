from functools import partialmethod
from types import MethodType
from django import forms
from django.utils.functional import cached_property
from django.utils.translation import ugettext as _
from ecolex.lib.schema import fields
from .schema import FIELD_MAP, FILTER_FIELDS, STATS_FIELDS, SCHEMA_MAP


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

    @cached_property
    def _FIELD_TYPE_MAP(self):
        return {
            f: t
            for t, fs in FIELD_MAP.items() if t != '_'
            for f in fs
        }

    def __has_document_type(self, doctype):
        # the form "has" the doctype, when either:
        # - no type-specific field is in use, and
        # - either: - no types are specified, or
        #           - it's listed in the requested types
        # or:
        # - a specific field of this type is in use, and
        # - either: (-, -, the same as above)
        #
        # (TODO: conflicting type + specific field is an error, so are
        # different type-specific fields)

        if not self.data:
            return True

        types = self.data.getlist('type')

        if types and len(types) == 1:
            return types[0] == doctype

        try:
            current = next(self._FIELD_TYPE_MAP[f]
                           for f in self.data.keys()
                           if f in self._FIELD_TYPE_MAP)
        except StopIteration:
            pass
        else:
            return doctype == current

        # if we got here, it's all-inclusive
        # (for the given types)
        return not types or doctype in types

    has_treaty = partialmethod(__has_document_type, 'treaty')
    has_decision = partialmethod(__has_document_type, 'decision')
    has_literature = partialmethod(__has_document_type, 'literature')
    has_legislation = partialmethod(__has_document_type, 'legislation')
    has_court_decision = partialmethod(__has_document_type, 'court_decision')
