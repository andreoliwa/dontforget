# -*- coding: utf-8 -*-
"""Application configuration."""
import os

from environs import Env

env = Env()
env.read_env()

FLASK_ENV = env("FLASK_ENV")

LOCAL_TIMEZONE = env("LOCAL_TIMEZONE", default="Europe/Berlin")
TELEGRAM_TOKEN = env("TELEGRAM_TOKEN", default=None)
TELEGRAM_IDLE_TIMEOUT = env.int("TELEGRAM_IDLE_TIMEOUT", default=120)

# By default, database will be refreshed every time a test runs.
REFRESH_TEST_DATABASE = env.bool("REFRESH_TEST_DATABASE", default=True)

LONG_OVERDUE = env.int("LONG_OVERDUE", default=14)
MEDIUM_OVERDUE = env.int("MEDIUM_OVERDUE", default=7)

ICONS = env.list("ICONS")

TOGGL_API_TOKEN = env("TOGGL_API_TOKEN")
TODOIST_API_TOKEN = env("TODOIST_API_TOKEN")

#: Working hours
HOME_HOURS = env.int("HOME_HOURS")

#: How many minutes before the reminder should be set
HOME_MINUTES_BEFORE = env.int("HOME_MINUTES_BEFORE")

#: Toggl clients to count as working hours
HOME_TOGGL_CLIENTS = env.list("HOME_TOGGL_CLIENTS")

#: Tags that should not be considered working hours
HOME_TOGGL_NOT_WORK_TAGS = env.list("HOME_TOGGL_NOT_WORK_TAGS")

#: Descriptions that should not be considered working hours
HOME_TOGGL_NOT_WORK_DESCRIPTIONS = env.list("HOME_TOGGL_NOT_WORK_DESCRIPTIONS")

#: Project name where the task will be created
HOME_TODOIST_PROJECT = env("HOME_TODOIST_PROJECT")

#: Description of the task that will be created
HOME_TODOIST_TASK = env("HOME_TODOIST_TASK")


class Config(object):
    """Base configuration."""

    SECRET_KEY = os.environ.get("DONTFORGET_SECRET", "r9UVPJectYXDHm2X87W92C")
    APP_DIR = os.path.abspath(os.path.dirname(__file__))  # This directory
    PROJECT_ROOT = os.path.abspath(os.path.join(APP_DIR, os.pardir))
    DEBUG_TB_INTERCEPT_REDIRECTS = False
    SQLALCHEMY_TRACK_MODIFICATIONS = False


class ProdConfig(Config):
    """Production configuration."""

    ENV = "prod"
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = "postgresql://dontforget:dontforget@localhost:7710/dontforget"


class DevConfig(Config):
    """Development configuration."""

    ENV = "dev"
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = "postgresql://dontforget:dontforget@localhost:7710/dontforget_dev"
    DEBUG_TB_ENABLED = True


class TestConfig(Config):
    """Test configuration."""

    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = "postgresql://dontforget:dontforget@localhost:7710/dontforget_test"
    WTF_CSRF_ENABLED = False  # Allows form testing
