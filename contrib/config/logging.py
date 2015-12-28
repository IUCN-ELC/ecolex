from pathlib import Path

BASE_DIR = (Path(__file__).parent.parent / 'logs').absolute()

LOG_DICT = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': "[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s",
            'datefmt': "%d/%b/%Y %H:%M:%S"
        },
    },
    'handlers': {
        'elis_file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': str(BASE_DIR / 'elis_import.log'),
            'formatter': 'verbose',
        },
        'informea_file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': str(BASE_DIR / 'informea_import.log'),
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'treaty': {
            'handlers': ['elis_file'],
            'level': 'INFO',
        },
        'literature': {
            'handlers': ['elis_file'],
            'level': 'INFO',
        },
        'decision': {
            'handlers': ['informea_file'],
            'level': 'INFO',
        }
    }
}
