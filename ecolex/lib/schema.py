import warnings
from django.utils.functional import cached_property
from marshmallow import Schema as _Schema, fields, pre_load
from ecolex.lib.utils import MutableLookupDict


# monkey patch default Field implementation, it's simpler
if not getattr(fields.Field, '_patched', False):
    def _new__init__(self, *args, **kwargs):
        self.multilingual = kwargs.pop('multilingual', False)
        self.fallback = kwargs.pop('fallback', True)
        self.load_from_attribute = kwargs.pop('load_from_attribute', None)

        if self.load_from_attribute and kwargs.get('load_from'):
            raise ValueError(
                "`load_from` and `load_from_attribute` "
                "are mutually exclusive.")

        self._orig__init__(**kwargs)

    def _new_add_to_schema(self, field_name, schema):
        self._orig_add_to_schema(field_name, schema)

        # now we have access to the parent schema
        if self.load_from_attribute:
            self.load_from = getattr(self.parent, self.load_from_attribute)

    fields.Field._orig__init__ = fields.Field.__init__
    fields.Field._orig_add_to_schema = fields.Field._add_to_schema

    fields.Field.__init__ = _new__init__
    fields.Field._add_to_schema = _new_add_to_schema

    fields.Field._patched = True


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
    >>> schema = MySchema(context={'language': 'abcd'})
    >>> result = schema.load({
    ...    'attr1_in': 'one',
    ...    'other_attr_abcd': 'two',
    ...    'attr3_in': 'three',
    ...    'another_attr': 'nope',
    ... })
    >>> result.data
    {'attr1': 'one', 'attr2': 'two', 'attr3': 'three'}
    >>>

    """

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
        {<field name / load_from >: <fallback (bool)>}
        """
        return {
            field.load_from or name: field.fallback
            for name, field in self.fields.items()
            if field.multilingual
        }
