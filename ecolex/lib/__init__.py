import unicodedata


def unaccent(txt):
    # NOTE: non-latin scripts should be handled by something more capable,
    # e.g. Unidecode / Unihandecode

    # decompose characters and return only non-combining ones
    return ''.join(map(
        lambda c: '' if unicodedata.category(c).startswith('M') else c,
        unicodedata.normalize('NFD', txt)
    ))
