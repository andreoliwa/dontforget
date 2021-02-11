"""Application settings."""
import logging
from pathlib import Path

from appdirs import AppDirs
from environs import Env
from ruamel.yaml import YAML

from dontforget.constants import CONFIG_YAML, PROJECT_NAME

env = Env()
env.read_env()

DEBUG = bool(env("DEBUG", default=False))
LOG_LEVEL = (env("LOG_LEVEL", default="") or logging.getLevelName(logging.DEBUG if DEBUG else logging.WARNING)).upper()

LOCAL_TIMEZONE = env("LOCAL_TIMEZONE", default="Europe/Berlin")

TOGGL_API_TOKEN = env("TOGGL_API_TOKEN")

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

#: List of directories with user-configured pipes
USER_PIPES_DIR = env.list("USER_PIPES_DIR")

DEFAULT_DIRS = AppDirs(PROJECT_NAME)
CONFIG_FILE_PATH = Path(DEFAULT_DIRS.user_config_dir) / CONFIG_YAML
if not CONFIG_FILE_PATH.exists():
    raise RuntimeError(f"Config file not found: {CONFIG_FILE_PATH}")


def load_config_file():
    """Load the YAML config file."""
    yaml = YAML()
    return yaml.load(CONFIG_FILE_PATH)
