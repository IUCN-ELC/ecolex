#from pathlib import Path
from os import path
from ecolex.settings import BASE_DIR

#BASE_DIR = (Path(__file__).parent.parent / 'logs').absolute()

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
        'import_file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': path.join(BASE_DIR, 'import.log'),
            'formatter': 'verbose',
        },
        'legislation_import': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': path.join(BASE_DIR, 'legislation_import.log'),
            'formatter': 'verbose',
        },
        'cop_decision_import': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': path.join(BASE_DIR, 'cop_decision_import.log'),
            'formatter': 'verbose',
        },
        'court_decision_import': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': path.join(BASE_DIR, 'court_decision_import.log'),
            'formatter': 'verbose',
        },
        'literature_import': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': path.join(BASE_DIR, 'literature_import.log'),
            'formatter': 'verbose',
        },
        'treaty_import': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': path.join(BASE_DIR, 'treaty_import.log'),
            'formatter': 'verbose',
        },
        'solr': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': path.join(BASE_DIR, 'solr.log'),
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
            'handlers': ['import_file', 'console'],
            'level': 'DEBUG',
        },
        'legislation_import': {
            'handlers': ['legislation_import', 'console'],
            'level': 'DEBUG',
        },
        'cop_decision_import': {
            'handlers': ['cop_decision_import', 'console'],
            'level': 'DEBUG',
        },
        'court_decision_import': {
            'handlers': ['court_decision_import', 'console'],
            'level': 'DEBUG',
        },
        'literature_import': {
            'handlers': ['literature_import', 'console'],
            'level': 'DEBUG',
        },
        'treaty_import': {
            'handlers': ['treaty_import', 'console'],
            'level': 'DEBUG',
        },
        'solr': {
            'handlers': ['solr', 'console'],
            'level': 'DEBUG',
        },
    }
}
