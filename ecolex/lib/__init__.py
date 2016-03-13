import re
import unicodedata


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
