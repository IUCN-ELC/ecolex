"""
Django settings for ecolex_site project.

For more information on this file, see
https://docs.djangoproject.com/en/1.7/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.7/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
from collections import OrderedDict
from django.utils.translation import ugettext_lazy as _

BASE_DIR = os.path.dirname(os.path.dirname(__file__))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.7/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get("EDW_RUN_WEB_SECRET_KEY")
FAOLEX_API_KEY = ''

# sentry dsn
SENTRY_DSN = os.environ.get('EDW_RUN_WEB_SENTRY_DSN')
SENTRY_PUBLIC_DSN = os.environ.get('EDW_RUN_WEB_SENTRY_PUBLIC_DSN')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = bool(os.environ.get('EDW_RUN_WEB_DEBUG'))

ALLOWED_HOSTS = ['*']

# Selenium
#TEST_RUNNER = 'django_selenium.selenium_runner.SeleniumTestRunner'


# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sitemaps',
    'django.contrib.sites',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_extensions',
    'raven.contrib.django.raven_compat',
    'rest_framework',
    'static_sitemaps',
    'ckeditor',
    'ecolex',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    #'django.middleware.locale.LocaleMiddleware',
    'solid_i18n.middleware.SolidLocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    #'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    #'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    #'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'ecolex.middleware.CacheControlMiddleware',
)

TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [],
    'OPTIONS': {
        'debug': DEBUG,
        'context_processors': {
            "django.contrib.auth.context_processors.auth",
            "django.template.context_processors.debug",
            "django.template.context_processors.i18n",
            "django.template.context_processors.media",
            "django.template.context_processors.static",
            "django.template.context_processors.tz",
            "django.contrib.messages.context_processors.messages",
            "ecolex.global_config",
        },
    },
}]

# do template caching only on production
if DEBUG:
    TEMPLATES[0]['APP_DIRS'] = True
else:
    TEMPLATES[0]['OPTIONS']['loaders'] = [
        ('django.template.loaders.cached.Loader', [
            'django.template.loaders.filesystem.Loader',
            'django.template.loaders.app_directories.Loader',
        ]),
    ]

ROOT_URLCONF = 'ecolex.urls'

WSGI_APPLICATION = 'ecolex.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.7/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'HOST': 'maria',
        'NAME': os.environ.get('MYSQL_DATABASE'),
        'USER': os.environ.get('MYSQL_USER'),
        'PASSWORD': os.environ.get('MYSQL_PASSWORD'),
    }
}


# Caching.
# TODO: In production this needs to be set to something cross-processes,
# e.g. filebased.FileBasedCache with LOCATION /dev/shm, or memcached

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}


LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': "[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s",
            'datefmt': "%d/%b/%Y %H:%M:%S"
        },
    },
    'handlers': {
        # TODO dockerize this. use console.
        'logfile': {
            'class': 'logging.handlers.WatchedFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'django_errors.log'),
            'formatter': 'verbose',
        }
    },
    'loggers': {
        'django': {
            'handlers': ['logfile'],
            'level': 'DEBUG' if DEBUG else 'ERROR',
            'propagate': False,
        }
    }
}

# Internationalization
# https://docs.djangoproject.com/en/1.7/topics/i18n/

LANGUAGE_CODE = 'en'

LANGUAGES = (
    ('en', _('English')),
    ('fr', _('French')),
    ('es', _('Spanish')),
)

# TODO: refactor and DRY ...
LANGUAGE_MAP = OrderedDict([
    ('en', 'English'),
    ('fr', 'French'),
    ('es', 'Spanish'),
    ('ru', 'Russian'),
    ('other', 'Other'),
])

EXTRA_LANG_INFO = {
    'other': {
        'bidi': False,
        'code': 'other',
        'name': 'Other',
        'name_local': _('Other'),
    },
}

# Let Django know about the "Other" language
import django.conf.locale
django.conf.locale.LANG_INFO.update(EXTRA_LANG_INFO)

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = False

USE_TZ = True

# always redirect /en/ to root
SOLID_I18N_DEFAULT_PREFIX_REDIRECT = True

# drf

REST_FRAMEWORK = {
    'PAGE_SIZE': 20,
}
# used by both api and search
FACETS_PAGE_SIZE = 100
SEARCH_PAGE_SIZE = 20

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.7/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = os.environ.get('EDW_RUN_WEB_STATIC_ROOT') or os.path.join(BASE_DIR, 'static')

# Solr
SOLR_URI = os.environ.get('EDW_RUN_SOLR_URI', '')

# For default sorting, set SOLR_SORTING to ''
SOLR_SORTING = ''

SEARCH_PROXIMITY = '100'

GA_ENABLED = True
TEXT_SUGGESTION = True

SITE_ID = 1

STATICSITEMAPS_ROOT_SITEMAP = 'ecolex.sitemaps.sitemaps'
STATICSITEMAPS_PING_GOOGLE = False

# CKEDITOR SETTINGS
CKEDITOR_CONFIGS = {
    'default': {
        'toolbar': 'full',
    },
}

# API KEY FOR FAOLEX HARVESTER
FAOLEX_ENABLED = bool(os.environ.get('EDW_RUN_WEB_FAOLEX_ENABLED', 'True'))
FAOLEX_API_KEY = os.environ.get('EDW_RUN_WEB_FAOLEX_API_KEY', 'secret')
# FIXME '' for this should determine a new key generation... handle that too; one way or another
if FAOLEX_ENABLED and not FAOLEX_API_KEY:
    raise RuntimeError('EDW_RUN_WEB_FAOLEX_API_KEY not set although Faolex is enabled')

# Google Analytics keys
ECOLEX_CODE = os.environ.get('EDW_RUN_WEB_ECOLEX_CODE')
INFORMEA_CODE = os.environ.get('EDW_RUN_WEB_INFORMEA_CODE')
FAOLEX_CODE = os.environ.get('EDW_RUN_WEB_FAOLEX_CODE')
FAOLEX_CODE_2 = os.environ.get('EDW_RUN_WEB_FAOLEX_CODE_2')

EXPORT_TYPES = ['legislation', 'treaty', 'decision', 'court_decision', 'literature']

# Use SOLR_UPDATE for the `update` management command.
# The management command will replace values in SOLR_UPDATE['replace']['field']
# that are equal to SOLR_UPDATE['replace']['from'] with the value in
# SOLR_UPDATE['replace']['to']
# Additional filters in SOLR_UPDATE['filters'] are applied.
# If you don't need any additional filters, leave this list empty.
SOLR_UPDATE = {
    'replace': {
        'field': 'legCountry_en',
        'from': 'Moldova - Republic of',
        'to': 'Moldova, Republic of'
    },
    'filters': [
        # {
        #     'field': 'legCountry_en',
        #     'value': 'Moldova - Republic of',
        # }
    ]
}

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
MANAGEMENT_DIR = os.path.join(BASE_DIR, 'ecolex', 'management')
CONFIG_DIR = os.path.join(MANAGEMENT_DIR, 'config')
PARTY_COUNTRIES = os.path.join(CONFIG_DIR, 'party_countries.json')
TESTING_DIR = os.path.join(MANAGEMENT_DIR, 'testing')

SOLR_IMPORT = {
    'common': {
        'solr_timeout': 100,
        'countries_json': os.path.join(CONFIG_DIR, 'countries.json'),
        'fao_countries_json': os.path.join(CONFIG_DIR, 'fao_countries.json'),
        'languages_json': os.path.join(CONFIG_DIR, 'languages.json'),
        'regions_json': os.path.join(CONFIG_DIR, 'regions.json'),
        'subdivisions_json': os.path.join(CONFIG_DIR, 'subdivisions.json'),
        'keywords_json': os.path.join(CONFIG_DIR, 'keywords.json'),
        'subjects_json': os.path.join(CONFIG_DIR, 'subjects.json'),
    },
    'court_decision': {
        'test_input_file': os.path.join(TESTING_DIR, 'court_decision_in.json'),
        'test_output_file': os.path.join(TESTING_DIR, 'court_decision_out.json'),
        'court_decisions_url': 'http://informea.org/ws/court-decisions',
        'days_ago': 30,
        'data_url': 'http://informea.org/node/%s/json',
        'update': True,
    },
    'treaty': {
        'treaties_url': 'http://www2.ecolex.org/elis_isis3w.php',
        'query_export': '?database=tre&search_type=page_search&table=all',
        'query_format': 'ES:I AND STAT:C AND (DE:%d%02d OR DM:%d%02d)',
        'query_filter': '&spage_query=%s',
        'query_skip': '&spage_first=%d',
        'query_type': '&format_name=@xmlexp&lang=xmlf&page_header=@xmlh&sort_name=@SMOD',
        'per_page': 20,
    },
    'literature': {
        'literature_url': 'http://www2.ecolex.org/elis_isis3w.php',
        'query_export': '?database=libcat&search_type=page_search&table=all',
        'query_format': 'ES:I AND STAT:C AND (DE:%d%02d OR DM:%d%02d)',
        'query_filter': '&spage_query=%s',
        'query_skip': '&spage_first=%d',
        'query_type': '&format_name=@xmlexp&lang=xmlf&page_header=@xmlh&sort_name=@SMOD',
        'per_page': 20,
    },
    'decision': {
        'cop_decision_url': 'http://odata.informea.org/informea.svc/Decisions',
        'query_skip': '$top=%d&$skip=%d',
        'query_filter': "$filter=updated gt datetime'%s'",
        'query_format': '$format=json',
        'query_expand': '$expand=title,longTitle,keywords,content,files,summary',
        'query_order': '$orderby=updated asc',
        'per_page': 20,
        'days_ago': 30,
    },
    'legislation': {},
}

RAVEN_CONFIG = {
    'dsn': SENTRY_DSN,
}

# Local settings
try:
    from ecolex.local_settings import *
except ImportError:
    pass
