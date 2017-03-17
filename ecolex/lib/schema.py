import warnings
from collections import OrderedDict
from ecolex.lib.utils import MutableLookupDict, DefaultOrderedDict
from django.conf import settings
from django.utils.functional import cached_property
from marshmallow import Schema as _Schema, SchemaOpts, fields, pre_load


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
        self.solr_facets = getattr(meta, 'solr_facets', self.solr_filters)
        self.solr_fetch = getattr(meta, 'solr_fetch', [])
        self.solr_boost = getattr(meta, 'solr_boost', {})
        self.solr_highlight = getattr(meta, 'solr_highlight', [])
        self.form_single_choice = getattr(meta, 'form_single_choice', [])

        diff = set(self.solr_highlight).difference(self.solr_fetch)
        if diff:
            raise ValueError("`%s.solr_highlight` contains non-fetched fields: "
                             "'%s'." % (meta.__qualname__, "', '".join(diff)))

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

            lookups.extend(['{item}_%s' % lang
                            for lang in settings.LANGUAGE_MAP])

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

    def load(self, data, language=None, *args, **kwargs):
        if language:
            self.context['language'] = language
        return super().load(data, *args, **kwargs)

    def loads(self, json_data, language=None, *args, **kwargs):
        if language:
            self.context['language'] = language
        return super().loads(json_data, *args, **kwargs)


class __FieldProperties(object):
    __slots__ = (
        'type', 'name', 'load_from', 'multilingual', 'multivalue', 'datatype',
        'solr_filter', 'solr_facet', 'solr_fetch', 'solr_boost',
        'solr_highlight', 'form_single_choice',
        '_field',
    )

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    def get_source_field(self, lang=None):
        if not self.multilingual:
            return self.load_from

        if not lang:
            raise ValueError("Trying to get source field for multilingual "
                             "field, but no language specified.")

        return "%s_%s" % (self.load_from, lang)

    def get_source_fields(self):
        if not self.multilingual:
            return [self.load_from]
        else:
            return ['{}_{}'.format(self.load_from, lang)
                    for lang in settings.LANGUAGE_MAP]

    def __repr__(self):
        props = []
        for prop in 'multilingual', 'multivalue':
            if getattr(self, prop):
                props.append(prop)
        return "< {}.{} ({}) : {} >".format(
            self.type, self.name, self.load_from, ', '.join(props))


def get_field_properties(base_schema, schemas):
    props = DefaultOrderedDict(OrderedDict)

    for schema in (base_schema, ) + schemas:
        if schema is base_schema:
            typ = '_'
        else:
            typ = schema.opts.type

        for name, field in schema().declared_fields.items():
            # don't duplicate inherited fields
            if (schema != base_schema and
                name in props['_'] and
                (base_schema._declared_fields.get(name) is
                 schema._declared_fields.get(name))
            ):
                continue

            fp = __FieldProperties()
            fp._field = field
            fp.type = typ
            fp.name = name
            fp.load_from = field.load_from
            fp.multilingual = field.multilingual
            multivalue = isinstance(field, fields.List)
            fp.multivalue = multivalue
            if multivalue:
                inst = field.container
            else:
                inst = field
            fp.datatype = inst.__class__.__name__.lower()

            fp.solr_filter = name in schema.opts.solr_filters
            fp.solr_facet = name in schema.opts.solr_facets
            for prop in ('solr_fetch', 'solr_highlight', 'form_single_choice'):
                setattr(fp, prop,
                        name in getattr(schema.opts, prop))
            try:
                fp.solr_boost = schema.opts.solr_boost[name]
            except KeyError:
                fp.solr_boost = None

            props[typ][field.canonical_name] = fp

    return props
