from pathlib import Path

BASE_DIR = (Path(__file__).parent.parent / 'logs').absolute()

LOG_DICT = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': "[%(asctime)s] %(levelname)s "
                      "[%(filename)s:%(lineno)s] %(message)s",
            'datefmt': "%d/%b/%Y %H:%M:%S"
        },
        'simple': {
            'format': "[%(asctime)s] %(levelname)s %(message)s",
            'datefmt': "%H:%M:%S"
        },
    },
    'handlers': {
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': str(BASE_DIR / 'import.log'),
            'formatter': 'verbose',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'loggers': {
        'import': {
            'handlers': ['file', 'console'],
            'level': 'DEBUG',
        },
    }
}
