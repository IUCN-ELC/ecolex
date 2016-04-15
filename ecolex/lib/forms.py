from django import forms
from django.http import QueryDict
from django.utils.functional import cached_property


class UrlencodingMixin(object):
    # cache things, we might use this in a tight loop
    @cached_property
    def _normalized_data(self):
        valid = False
        if self.is_valid():
            valid = True

        # we'll build a dictionary formed from:
        # - self.cleaned_data key/values if keys were available in self.data,
        # - and remaining self.data key/values if form is not valid.

        cdks = set(self.cleaned_data.keys())
        dks = set(self.data.keys())

        cdks.intersection_update(dks)

        sources = ((cdks, self.cleaned_data), )
        if not valid:
            dks.difference_update(cdks)
            sources += ((dks, self.data), )

        out = QueryDict()
        # QueryDict is very unfriendly to already-clean data,
        # so we'll use its parent MultiValueDict directly
        parent = super(QueryDict, out)

        for keys, dataset in sources:
            for k in keys:
                v = dataset[k]

                # we skip any empty stuff (TODO: is this always ok?),
                # as well as default data
                if (v in forms.Field.empty_values
                    or v == self.fields[k].initial):
                    continue

                # note that MultiValueDict transforms items to lists internally
                if isinstance(v, list):
                    parent.setlist(k, v)
                else:
                    parent.__setitem__(k, v)

        return out

    def urlencoded(self, only=None, **kwargs):
        data = self._normalized_data.copy()
        parent = super(QueryDict, data)


        for k, v in kwargs.items():
            # skip default / empty things
            if (v in forms.Field.empty_values
                or v == self.fields[k].initial):
                continue

            if isinstance(v, list):
                parent.setlist(k, v)
            else:
                parent.__setitem__(k, v)

        if only:
            drop = [k for k in data.keys() if k not in only]
            for k in drop:
                del data[k]

        return data.urlencode()
