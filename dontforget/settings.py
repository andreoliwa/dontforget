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
UI_TELEGRAM_BOT_IDLE_TIMEOUT = config('UI_TELEGRAM_BOT_IDLE_TIMEOUT', default=60, cast=int)


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
    DB_NAME = 'prod.sqlite'
    # Put the db file in project root
    DB_PATH = os.path.join(Config.PROJECT_ROOT, DB_NAME)
    SQLALCHEMY_DATABASE_URI = 'sqlite:///{0}'.format(DB_PATH)
    DEBUG_TB_ENABLED = False  # Disable Debug toolbar


class DevConfig(Config):
    """Development configuration."""

    ENV = 'dev'
    DEBUG = True
    DB_NAME = 'dev.sqlite'
    # Put the db file in project root
    DB_PATH = os.path.join(Config.PROJECT_ROOT, DB_NAME)
    SQLALCHEMY_DATABASE_URI = 'sqlite:///{0}'.format(DB_PATH)
    DEBUG_TB_ENABLED = True
    ASSETS_DEBUG = True  # Don't bundle/minify static assets
    CACHE_TYPE = 'simple'  # Can be "memcached", "redis", etc.


class TestConfig(Config):
    """Test configuration."""

    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite://'
    BCRYPT_LOG_ROUNDS = 4  # For faster tests; needs at least 4 to avoid "ValueError: Invalid rounds"
    WTF_CSRF_ENABLED = False  # Allows form testing
