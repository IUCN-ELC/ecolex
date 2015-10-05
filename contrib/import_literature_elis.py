from bs4 import BeautifulSoup

from import_elis import valid_date, format_date


DOCUMENT = 'document'

AUTHOR_START = '^a'
AUTHOR_SPACE = '^b'

FIELD_MAP = {
    'id': 'litId',
    'authora': 'litAuthor',
    'authorm': 'litAuthor',
    'titleoftext': 'litLongTitle_en',
    # TODO: Long title for other languages
    'papertitleoftext': 'litTitleOfText_en',
    'papertitleoftextfr': 'litTitleOfText_fr',
    'papertitleoftextfr': 'litTitleOfText_fr',
    # TODO: Short title for all langauges
    'dateofentry': 'litDateOfEntry',
    'dateofmodification': 'litDateOfModification',
}

DATE_FIELDS = [
    'litDateOfEntry', 'litDateOfModification'
]


def fetch_literature():
    literatures = []
    bs = BeautifulSoup(open('literature.xml', 'r', encoding='utf-8'))

    documents = bs.findAll(DOCUMENT)
    literatures.extend(documents)
    return literatures


def clean_text(text):
    if AUTHOR_START in text:
        text = text.replace(AUTHOR_START, '').replace(AUTHOR_SPACE, ' ')
    return text.strip()


def parse_literatures(raw_literatures):
    literatures = []

    for raw_literature in raw_literatures:
        data = {}

        for k, v in FIELD_MAP.items():
            field_values = raw_literature.findAll(k)
            if (v in DATE_FIELDS and field_values
                    and valid_date(field_values[0].text)):
                assert len(field_values) == 1
                data[v] = format_date(clean_text(field_values[0].text))
            elif field_values:
                if v in data:
                    data[v].extend([clean_text(field.text) for field in field_values])
                else:
                    data[v] = [clean_text(field.text) for field in field_values]

        literatures.append(data)
    return literatures


if __name__ == '__main__':
    raw_literatures = fetch_literature()
    literatures = parse_literatures(raw_literatures)
