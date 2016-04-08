import warnings
from django.utils.functional import cached_property
from marshmallow import Schema as _Schema, SchemaOpts, fields, pre_load
from ecolex.lib.utils import MutableLookupDict


# monkey patch default Field implementation, it's simpler
class __Field(object):
    def __init__(self, *args, **kwargs):
        self.multilingual = kwargs.pop('multilingual', False)
        self.fallback = kwargs.pop('fallback', True)
        self.load_from_attribute = kwargs.pop('load_from_attribute', None)

        if self.load_from_attribute and kwargs.get('load_from'):
            raise ValueError(
                "`load_from` and `load_from_attribute` "
                "are mutually exclusive.")

        self._orig___init__(*args, **kwargs)

    def _add_to_schema(self, field_name, schema):
        self._orig__add_to_schema(field_name, schema)

        # now we have access to the parent schema
        if self.load_from_attribute:
            self.load_from = getattr(self.parent, self.load_from_attribute)

    @property
    def load_from(self):
        return self._load_from or self.name

    @load_from.setter
    def load_from(self, value):
        self._load_from = value

    @property
    def canonical_name(self):
        abbr = self.parent.opts.abbr
        prefix = '%s_' % abbr if abbr else ''
        return '%s%s' % (prefix, self.name)

if not getattr(fields.Field, '_patched', False):
    for name, attr in __Field.__dict__.items():
        if name.startswith('__') and name != '__init__':
            continue

        try:
            orig_attr = getattr(fields.Field, name)
        except AttributeError:
            pass
        else:
            setattr(fields.Field, '_orig_%s' % name, orig_attr)

        setattr(fields.Field, name, attr)

    fields.Field._patched = True


class _CustomOptions(SchemaOpts):
    """
    Custom Meta options class.
    """
    def __init__(self, meta):
        super().__init__(meta)
        self.model = getattr(meta, 'model', None)
        self.abbr = getattr(meta, 'abbr', None)
        self.type = getattr(meta, 'type', None)
        self.solr_filters = getattr(meta, 'solr_filters', [])
        self.solr_fetch = getattr(meta, 'solr_fetch', [])
        self.solr_boost = getattr(meta, 'solr_boost', {})
        self.solr_highlight = getattr(meta, 'solr_highlight', [])
        self.form_single_choice = getattr(meta, 'form_single_choice', [])


class Schema(_Schema):
    """
    A schema that:
    - allows fields' `load_from` to be set from a schema attribute, and
    - handles multilingual fields on data load.

    Usage:

    >>> class MySchema(Schema):
    ...     ATTR1 = 'attr1_in'
    ...     ATTR3 = 'attr3_in'
    ...     attr1 = fields.String(load_from_attribute='ATTR1')
    ...     attr2 = fields.String(multilingual=True,
    ...                           load_from="other_attr")
    ...     attr3 = fields.String(multilingual=True,
    ...                           load_from_attribute='ATTR3')
    ...     attr4 = fields.String(multilingual=True,
    ...                           fallback=False,
    ...                           load_from='another_attr')
    ...
    >>> schema = MySchema()
    >>> result = schema.load({
    ...    'attr1_in': 'one',
    ...    'other_attr_abcd': 'two',
    ...    'attr3_in': 'three',
    ...    'another_attr': 'nope',
    ... }, language='abcd')
    >>> result.data
    {'attr1': 'one', 'attr2': 'two', 'attr3': 'three'}
    >>>

    """

    OPTIONS_CLASS = _CustomOptions
    _FALLBACK_LANGUAGE = 'en'

    @pre_load
    def _handle_multilingual_input(self, data):
        """
        Converts the input data to a mutable lookup dict.
        WARNING: this only works when the input is a dictionary.
        """

        multilinguals = self._multilingual_fields
        if multilinguals:
            # lookup for {key}_{language},
            # and fallback to {key}, {key}_{fallback_language}

            lookups = []
            language = self.context.get('language')
            if language:
                lookups.append('{item}_%s' % language)
            else:
                warnings.warn(
                    "Schema %s has multilingual fields, but no language "
                    "was made available in context." % type(self).__name__,
                    stacklevel=2)

            lookups.extend(['{item}',
                            '{item}_%s' % self._FALLBACK_LANGUAGE])

            data = MutableLookupDict(data,
                                     mutables=multilinguals,
                                     lookups=tuple(lookups))

        return data

    @cached_property
    def _multilingual_fields(self):
        """
        Returns this schema's multilingual fields as a dict of
        {<field load_from>: <fallback (bool)>}
        """
        return {
            field.load_from: field.fallback
            for name, field in self.fields.items()
            if field.multilingual
        }

    # because our system hard-depends on a language being set
    def load(self, data, language, *args, **kwargs):
        self.context['language'] = language
        return super().load(data, *args, **kwargs)

    def loads(self, json_data, language, *args, **kwargs):
        self.context['language'] = language
        return super().loads(json_data, *args, **kwargs)
