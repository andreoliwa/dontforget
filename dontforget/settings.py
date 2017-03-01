# -*- coding: utf-8 -*-
"""Application configuration."""
import os

from prettyconf import config

UI_MODULE_NAME = config('UI_MODULE_NAME', default='cocoa_dialog')
UI_COCOA_DIALOG_PATH = config(
    'UI_COCOA_DIALOG_PATH',
    default='/Applications/cocoaDialog.app/Contents/MacOS/cocoaDialog')
UI_DIALOG_TIMEOUT = config('UI_DIALOG_TIMEOUT', default=30, cast=int)
UI_DEFAULT_SNOOZE = config('UI_DEFAULT_SNOOZE', default='1 hour')
UI_TELEGRAM_BOT_TOKEN = config('UI_TELEGRAM_BOT_TOKEN', default=None)
UI_TELEGRAM_BOT_IDLE_TIMEOUT = config('UI_TELEGRAM_BOT_IDLE_TIMEOUT', default=120, cast=int)

# By default, database will be refreshed every time a test runs.
TEST_REFRESH_DATABASE = config('TEST_REFRESH_DATABASE', default=True, cast=config.boolean)

# Tests running on Travis CI?
RUNNING_ON_TRAVIS = config('RUNNING_ON_TRAVIS', default=False, cast=config.boolean)


class Config(object):
    """Base configuration."""

    SECRET_KEY = os.environ.get('DONTFORGET_SECRET', 'secret-key')  # TODO: Change me
    APP_DIR = os.path.abspath(os.path.dirname(__file__))  # This directory
    PROJECT_ROOT = os.path.abspath(os.path.join(APP_DIR, os.pardir))
    BCRYPT_LOG_ROUNDS = 13
    ASSETS_DEBUG = False
    DEBUG_TB_ENABLED = False  # Disable Debug toolbar
    DEBUG_TB_INTERCEPT_REDIRECTS = False
    CACHE_TYPE = 'simple'  # Can be "memcached", "redis", etc.
    SQLALCHEMY_TRACK_MODIFICATIONS = False


class ProdConfig(Config):
    """Production configuration."""

    ENV = 'prod'
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = 'postgresql://dontforget:dontforget@postgresql:5432/dontforget'
    DEBUG_TB_ENABLED = False  # Disable Debug toolbar


class DevConfig(Config):
    """Development configuration."""

    ENV = 'dev'
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'postgresql://dontforget:dontforget@postgresql:5433/dontforget_dev'
    DEBUG_TB_ENABLED = True
    ASSETS_DEBUG = True  # Don't bundle/minify static assets
    CACHE_TYPE = 'simple'  # Can be "memcached", "redis", etc.


class TestConfig(Config):
    """Test configuration."""

    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'postgresql://dontforget:dontforget@postgresql:5433/dontforget_test'
    BCRYPT_LOG_ROUNDS = 4  # For faster tests; needs at least 4 to avoid "ValueError: Invalid rounds"
    WTF_CSRF_ENABLED = False  # Allows form testing
