from functools import partialmethod
from itertools import islice
from types import MethodType
from django import forms
from django.forms.boundfield import BoundField
from django.conf import settings
from django.utils.functional import cached_property
from django.utils.translation import ugettext as _
from ecolex.lib.forms import UrlencodingMixin
from ecolex.lib.schema import fields
from .schema import FIELD_MAP, FILTER_FIELDS, STATS_FIELDS, SCHEMA_MAP


class FacetBoundField(BoundField):
    def set_facet_data(self, data):
        self._facet_data = data

    @cached_property
    def facet(self):
        """
        Returns a dictionary of truncated facet data, and a boolean
        providing for more data.
        """
        facet_data = self._facet_data
        data = facet_data[:settings.FACETS_PAGE_SIZE]

        def _find(what, where):
            # TODO: this is really inefficient
            try:
                return next(x for x in where if x['text'] == what)
            except StopIteration:
                return None

        requested = self.form.cleaned_data.get(self.name, [])
        additional = 0
        for r in requested:
            item = _find(r, data)

            if item is None:
                item = _find(r, facet_data)

                if item is None:
                    item = {"text": r, "count": 0}
                else:
                    additional += 1

                data.append(item)

            item['selected'] = True

        return {
            'data': data,
            'more': len(facet_data) - additional > settings.FACETS_PAGE_SIZE,
        }

class FacetFieldMixin(object):
    def valid_value(self, v):
        """
        Considers any given value as valid.
        """
        return True

    def get_bound_field(self, form, field_name):
        """
        Return a BoundField instance that will be used when accessing the form
        field in a template.
        """
        return FacetBoundField(form, self, field_name)


class FacetChoiceField(FacetFieldMixin, forms.ChoiceField):
    pass


class FacetMultipleChoiceField(FacetFieldMixin, forms.MultipleChoiceField):
    pass


class SearchForm(UrlencodingMixin, forms.Form):
    SORT_DEFAULT = ''
    SORT_ASC = 'oldest'
    SORT_DESC = 'newest'

    SORT_CHOICES = (
        (SORT_DESC, _('most recent')),
        (SORT_ASC, _('least recent')),
        (SORT_DEFAULT, _('relevance')),
    )

    q = forms.CharField(required=False)
    page = forms.IntegerField(min_value=1, required=False, initial=1)
    sortby = forms.ChoiceField(choices=SORT_CHOICES, required=False,
                               initial=SORT_DEFAULT)

    def __clean_field_with_initial(self, fname):
        if fname not in self.data or self.cleaned_data[fname] is None:
            return self.fields[fname].initial
        return self.cleaned_data[fname]

    clean_page = partialmethod(__clean_field_with_initial, 'page')
    clean_sortby = partialmethod(__clean_field_with_initial, 'sortby')

    def clean(self):
        # don't return any empty choice sets
        return {
            k: v
            for k, v in self.cleaned_data.items()
            if not (v == [] and
                    isinstance(self.fields[k], FacetMultipleChoiceField))
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._alter_sortby()
        self._add_filter_fields()

    def _alter_sortby(self):
        """
        If `q` is empty, sortby defaults to newest first.
        """
        if self.data.get('q', '').strip():
            return

        field = self.fields['sortby']

        # the old default key is assigned to SORT_DESC,
        # while the old default entry goes away
        default_default = self.SORT_DEFAULT
        new_default = self.SORT_DESC

        field.initial = new_default
        field.choices = tuple(
            (default_default if k is new_default else k, v)
            for k, v in self.SORT_CHOICES
            if k != default_default
        )

        def _clean(self, value):
            # we need to massage the data so that both the old and new
            # defaults are treated the same
            if value == new_default:
                value = default_default

            value = super(type(field), self).clean(value)

            # while we pass the expected value to the code downstream
            if value == default_default:
                value = new_default

            return value

        field.clean = MethodType(_clean, field)

    def _add_filter_fields(self):
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
                field = forms.MultipleChoiceField(choices=zip(choices, choices))
                new_fields.append(('type', field))
            else:
                # this will be faceted upon. create a choice field
                # (multiple by default)
                if field.form_single_choice:
                    new_fields.append((name,
                                       FacetChoiceField()))
                else:
                    new_fields.append((name,
                                       FacetMultipleChoiceField()))

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

    def set_facet_data(self, data):
        for k, v in data.items():
            # type is special-cased
            if k == 'type':
                continue
            try:
                field = self[k]
            except KeyError:
                # warn?
                pass
            else:
                field.set_facet_data(v)

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

    def urlencoded(self, skip=('page',), only=None, **kwargs):
        return super().urlencoded(skip=skip, only=only, **kwargs)

    def get_base_qs(self):
        """
        Returns the form's basic fields in querystring format.
        """
        return self.urlencoded(only=('q', 'type', 'sortby',
                                     'xdate_min', 'xdate_max'))
