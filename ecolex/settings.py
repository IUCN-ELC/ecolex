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
SECRET_KEY = 'cm32+t-u1nb=x7_gc3(rcs)6@#e=hn$ww0@l$^1^^6x6jv)u@t'
FAOLEX_API_KEY = 'tay'
# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*']

# Selenium
#TEST_RUNNER = 'django_selenium.selenium_runner.SeleniumTestRunner'


# Application definition

INSTALLED_APPS = (
    #'django.contrib.admin',
    #'django.contrib.auth',
    'django.contrib.contenttypes',
    #'django.contrib.sessions',
    #'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'ecolex',
)

MIDDLEWARE_CLASSES = (
    #'django.contrib.sessions.middleware.SessionMiddleware',
    #'django.middleware.locale.LocaleMiddleware',
    'solid_i18n.middleware.SolidLocaleMiddleware',
    #'django.middleware.common.CommonMiddleware',
    #'django.middleware.csrf.CsrfViewMiddleware',
    #'django.contrib.auth.middleware.AuthenticationMiddleware',
    #'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    #'django.contrib.messages.middleware.MessageMiddleware',
    #'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'ecolex.middleware.CacheControlMiddleware',
)

TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [],
    'APP_DIRS': True,
    'OPTIONS': {
        'debug': DEBUG,
        'context_processors': {
            #"django.contrib.auth.context_processors.auth",
            "django.template.context_processors.debug",
            "django.template.context_processors.i18n",
            "django.template.context_processors.media",
            "django.template.context_processors.static",
            "django.template.context_processors.tz",
            #"django.contrib.messages.context_processors.messages",
            "ecolex.global_config",
        },
    },
}]
# do template caching only on production
if not DEBUG:
    TEMPLATES['OPTIONS']['loaders'] = [
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
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
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
    },
    'loggers': {
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
STATIC_ROOT = os.path.join(BASE_DIR, 'static')

# Solr
SOLR_URI = os.environ.get('SOLR_URI', '')

# For default sorting, set SOLR_SORTING to ''
SOLR_SORTING = ''

SEARCH_PROXIMITY = '100'

GA_ENABLED = True

TEXT_SUGGESTION = True

LANGUAGES_JSON = '/ecolex/ecolex/management/languages.json'
REGIONS_JSON = '/ecolex/ecolex/management/regions.json'
COUNTRIES_JSON = '/ecolex/ecolex/management/countries.json'
SUBDIVISIONS_JSON = '/ecolex/ecolex/management/subdivisions.json'

# Local settings
try:
    from ecolex.local_settings import *
except ImportError:
    pass
