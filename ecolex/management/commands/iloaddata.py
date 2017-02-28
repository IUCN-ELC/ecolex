import sys

import ijson.backends.yajl2_cffi as ijson

from django.core.management.commands import loaddata
from django.core import serializers
from django.core.serializers.base import DeserializationError
from django.core.serializers.python import Deserializer as PythonDeserializer
from django.utils import six


# monkey patch the django core deserializer for json so we can use ijson iterative deserializer
orig_get_deserializer = serializers.get_deserializer


def get_deserializer(fmt):
    if fmt == 'json':
        return Deserializer
    return orig_get_deserializer(fmt)

serializers.get_deserializer = get_deserializer


class Command(loaddata.Command):
    pass


def Deserializer(stream, **options):
    """
    Deserialize a stream of JSON data using iterative ijson so we may not load the whole string into memory.
    """
    if isinstance(stream, (bytes, six.string_types)):
        raise TypeError('Use iloaddata/ijson with streams only. For strings use plain loaddata/json.loads')

    try:
        objects = ijson.items(stream, 'item')
        for obj in PythonDeserializer(objects, **options):
            yield obj
    except GeneratorExit:
        raise
    except Exception as e:
        # Map to deserializer error
        six.reraise(DeserializationError, DeserializationError(e), sys.exc_info()[2])


