"""Constants."""
DEVELOPMENT = "development"

START_MODE_FLASK = "flask"
START_MODE_DOCKER = "docker"

FLASK_COMMAND = "flask run --port 8008"
DOCKER_COMMAND = "docker-compose up --build dontforget"

DEFAULT_PIPES_DIR_NAME = "default_pipes"

#: Special unique separator for :py:meth:`flatten()` and :py:meth:`unflatten()`,
# to avoid collision with existing key values (e.g. the default dot separator "." can be part of a pyproject.toml key).
UNIQUE_SEPARATOR = "$#@"
