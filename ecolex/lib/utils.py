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
