# -*- coding: utf-8 -*-
"""Application configuration."""
import os

from prettyconf import config

LOCAL_TIMEZONE = config('LOCAL_TIMEZONE', default='Europe/Berlin')
TELEGRAM_TOKEN = config('TELEGRAM_TOKEN', default=None)
TELEGRAM_IDLE_TIMEOUT = config('TELEGRAM_IDLE_TIMEOUT', default=120, cast=int)

# By default, database will be refreshed every time a test runs.
TEST_REFRESH_DATABASE = config('TEST_REFRESH_DATABASE', default=True, cast=config.boolean)


class Config(object):
    """Base configuration."""

    SECRET_KEY = os.environ.get('DONTFORGET_SECRET', 'r9UVPJectYXDHm2X87W92C')
    APP_DIR = os.path.abspath(os.path.dirname(__file__))  # This directory
    PROJECT_ROOT = os.path.abspath(os.path.join(APP_DIR, os.pardir))
    DEBUG_TB_INTERCEPT_REDIRECTS = False
    SQLALCHEMY_TRACK_MODIFICATIONS = False


class ProdConfig(Config):
    """Production configuration."""

    ENV = 'prod'
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = 'postgresql://dontforget:dontforget@postgresql:5432/dontforget'


class DevConfig(Config):
    """Development configuration."""

    ENV = 'dev'
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'postgresql://dontforget:dontforget@postgresql:5433/dontforget_dev'
    DEBUG_TB_ENABLED = True


class TestConfig(Config):
    """Test configuration."""

    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'postgresql://dontforget:dontforget@postgresql:5433/dontforget_test'
    WTF_CSRF_ENABLED = False  # Allows form testing
