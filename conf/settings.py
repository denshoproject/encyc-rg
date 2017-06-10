"""
Django settings for encycrg project.

Generated by 'django-admin startproject' using Django 1.11.

For more information on this file, see
https://docs.djangoproject.com/en/1.11/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.11/ref/settings/
"""

import ConfigParser
import logging
import os
import sys

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CONFIG_FILES = [
    '/etc/encyc/encycrg.cfg',
    '/etc/encyc/encycrg-local.cfg'
]

config = ConfigParser.ConfigParser()
configs_read = config.read(CONFIG_FILES)
if not configs_read:
    raise Exception('No config file!')

# SECURITY WARNING: keep the secret key used in production secret!
with open('/etc/encyc/encycrg-secret-key.txt') as f:
    SECRET_KEY = f.read().strip()

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config.getboolean('debug', 'debug')

# Hosts/domain names that are valid for this site; required if DEBUG is False
# See https://docs.djangoproject.com/en/1.5/ref/settings/#allowed-hosts
ALLOWED_HOSTS = [
    host.strip()
    for host in config.get('security', 'allowed_hosts').split(',')
]

# Elasticsearch
DOCSTORE_HOSTS = [{
    'host':config.get('elasticsearch', 'docstore_host').split(':')[0],
    'port':config.get('elasticsearch', 'docstore_host').split(':')[1],
}]
DOCSTORE_INDEX = config.get('elasticsearch', 'docstore_index')

DEFAULT_LIMIT = 25
MAX_SIZE = 10000

# Filesystem path and URL for static media (mostly used for interfaces).
STATIC_ROOT = config.get('media', 'static_root')

# Version number appended to Bootstrap, etc URLs so updates are always
# picked up by browser. IMPORTANT: must be same as ASSETS_VERSION in Makefile!
ASSETS_VERSION = config.get('media', 'assets_version')

# Filesystem path and URL for media to be manipulated by encycrg
# (collection repositories, thumbnail cache, etc).
MEDIA_ROOT = config.get('media', 'media_root')
MEDIA_URL = config.get('media', 'media_url')
# URL of local media server ("local" = in the same cluster).
# Use this for sorl.thumbnail so it doesn't have to go through
# a CDN and get blocked for not including a User-Agent header.
# TODO Hard-coded! Replace with value from encycrg.cfg.
MEDIA_URL_LOCAL = config.get('media', 'media_url_local')

# used when document signature image field not populated
MISSING_IMG = config.get('media', 'missing_img')

THUMBNAIL_GEOMETRY='512x512>'
THUMBNAIL_COLORSPACE='sRGB'
THUMBNAIL_OPTIONS=''

# ----------------------------------------------------------------------

ADMINS = (
    ('geoffrey jost', 'geoffrey.jost@densho.org'),
    ('Geoff Froh', 'geoff.froh@densho.org'),
)

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    #
    'rest_framework',
    #
    'encycrg',
    'rg',
]

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
    'PAGE_SIZE': 20
}

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': '/var/lib/encyc/encycrg.db',
    }
}

REDIS_HOST = '127.0.0.1'
REDIS_PORT = '6379'
REDIS_DB_CACHE = 1
REDIS_DB_SORL = 4

CACHES = {
    'default': {
        'BACKEND': 'redis_cache.RedisCache',
        "LOCATION": "%s:%s" % (REDIS_HOST, REDIS_PORT),
    },
}

# whole-site caching
CACHE_MIDDLEWARE_ALIAS = 'default'
CACHE_MIDDLEWARE_SECONDS = 60 * 15
CACHE_MIDDLEWARE_KEY_PREFIX = 'encycrg'
# low-level caching
CACHE_TIMEOUT = 60 * 5

# ElasticSearch
ELASTICSEARCH_MAX_SIZE = 10000
ELASTICSEARCH_QUERY_TIMEOUT = 60 * 10  # 10 min
ELASTICSEARCH_FACETS_TIMEOUT = 60*60*1  # 1 hour

RESULTS_PER_PAGE = 25

# sorl-thumbnail
THUMBNAIL_KVSTORE = 'sorl.thumbnail.kvstores.cached_db_kvstore.KVStore'
#THUMBNAIL_KVSTORE = 'sorl.thumbnail.kvstores.redis_kvstore.KVStore'
THUMBNAIL_REDIS_PASSWORD = ''
THUMBNAIL_REDIS_HOST = REDIS_HOST
THUMBNAIL_REDIS_PORT = int(REDIS_PORT)
THUMBNAIL_REDIS_DB = REDIS_DB_SORL
THUMBNAIL_ENGINE = 'sorl.thumbnail.engines.convert_engine.Engine'
THUMBNAIL_CONVERT = 'convert'
THUMBNAIL_IDENTIFY = 'identify'
THUMBNAIL_CACHE_TIMEOUT = 60*60*24*365*10  # 10 years
THUMBNAIL_DUMMY = False
THUMBNAIL_URL_TIMEOUT = 60  # 1min

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'rg.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'encycrg.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.11/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}


# Password validation
# https://docs.djangoproject.com/en/1.11/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/1.11/topics/i18n/

TIME_ZONE='America/Los_Angeles'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.11/howto/static-files/

STATIC_URL = '/static/'
