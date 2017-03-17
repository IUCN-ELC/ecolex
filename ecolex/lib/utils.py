import re
import unicodedata
from collections import Iterable, OrderedDict


def unaccent(txt):
    # NOTE: non-latin scripts should be handled by something more capable,
    # e.g. Unidecode / Unihandecode

    # decompose characters and return only non-combining ones
    return ''.join(map(
        lambda c: '' if unicodedata.category(c).startswith('M') else c,
        unicodedata.normalize('NFD', txt)
    ))


def camel_case_to__(txt):
    """
    converts underscoreCase to underscore_case
    """
    try:
        cc_re = camel_case_to__._cc_re
    except AttributeError:
        cc_re = camel_case_to__._cc_re = re.compile(
            '((?<=.)[A-Z](?=[a-z0-9])|(?<=[a-z0-9])[A-Z])')

    return re.sub(cc_re, r'_\1', txt).lower()


def is_iterable(v):
    return not isinstance(v, str) and isinstance(v, Iterable)


def any_match(a, b):
    """
    Returns true if any item in `a` is matched by any item in `b`,
    handling the case when only one / neither is an iterable.
    (basically testing for set intersection in the most efficient manner).
    """
    return (
        (is_iterable(a)
         and (is_iterable(b) and set(b).intersection(a)
              or b in a)
        ) or
        (is_iterable(b) and a in b
         or b == a)
    )


class MutableLookupDict(dict):
    """
    Dictionary that can mutate the lookup of keys specified in `mutables`,
    according to the lookups specified in `lookups`.


    `mutables` must be a dictionary of <key name>: <bool fallback>.
    `lookups` should be a tuple of strings containing "{item}", e.g.:
    >>> ('{item}_mutated', '{item}', 'hard_fallback', 'another_{item}')
    """

    def __init__(self, *args, **kwargs):
        self._mutables = kwargs.pop('mutables', {})
        self._lookups = kwargs.pop('lookups', ())
        super().__init__(*args, **kwargs)

    def __getitem__(self, item):
        if item not in self._mutables:
            return super().__getitem__(item)

        fallback = self._mutables[item]
        if fallback:
            exc = None
            for lookup in self._lookups:
                key = lookup.format(item=item)
                try:
                    return super().__getitem__(key)
                except KeyError as e:
                    exc = e
                    continue

            # if we got this far without returning,
            raise exc

        else:
            key = self._lookups[0].format(item=item)
            return super().__getitem__(key)

    def __repr__(self):
        return "{cls}({data}, mutables={mutables}, lookups={lookups})".format(
            cls=type(self).__name__,
            data=super().__repr__(),
            mutables=self._mutables,
            lookups=self._lookups)

    def get(self, k, d=None):
        # because dict.get() doesn't call __getitem__ o.O
        # TODO: report python bug?
        try:
            return self[k]
        except KeyError:
            return d


# since python 3.6 both OrderedDict and defaultdict come with their own __slots__
# this makes inheriting from both impossible "TypeError: multiple bases have instance lay-out conflict"
# Thus we implement our own defaultdict and inherit only from OrderedDict.
# Note that in python3.6 all dicts are ordered, but this is an implementation detail and we don't have methods
# like move_to_end on bare dict and defaultdict
class DefaultOrderedDict(OrderedDict):
    # Source: http://stackoverflow.com/a/6190500/562769
    # with own modifications to make all methods actually work
    def __init__(self, default_factory=None, *a, **kw):
        if (default_factory is not None and
                not callable(default_factory)):
            raise TypeError('first argument must be callable')
        super().__init__(*a, **kw)
        self.default_factory = default_factory

    def __getitem__(self, key):
        try:
            return super().__getitem__(key)
        except KeyError:
            return self.__missing__(key)

    def __missing__(self, key):
        if self.default_factory is None:
            raise KeyError(key)
        self[key] = value = self.default_factory()
        return value

    def __reduce__(self):
        if self.default_factory is None:
            args = tuple()
        else:
            args = self.default_factory,
        return self.__class__, args, None, None, iter(self.items())

    def copy(self):
        return self.__copy__()

    def __copy__(self):
        return self.__class__(self.default_factory, self)

    def __deepcopy__(self, memo):
        import copy
        return self.__class__(self.default_factory,
                              copy.deepcopy(iter(self.items())))

    def __repr__(self):
        return 'DefaultOrderedDict(%s, %s)' % (self.default_factory,
                                               OrderedDict.__repr__(self))
