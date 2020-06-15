FROM python:3.6

ENV TERM xterm-256color
ENV APP_USER=dontforget
ENV APP_DIR=/home/${APP_USER}/app

RUN pip3 install -U pip poetry && \
    groupadd ${APP_USER} -g 1000 && useradd ${APP_USER} -m -u 1000 -g ${APP_USER}

# Install Python modules as a normal user instead of root
USER ${APP_USER}:${APP_USER}
WORKDIR ${APP_DIR}

# Whenever the project or the lock file changes, pip will be upgraded and packages will be reinstalled.
COPY --chown=dontforget:dontforget pyproject.toml poetry.lock ${APP_DIR}/

# Upgrade pip version inside the virtualenv.
RUN poetry run pip3 install -U pip

# Install only the production packages
RUN poetry install --no-dev

# We still need individual COPY commands, because "The directory itself is not copied, just its contents":
# https://docs.docker.com/engine/reference/builder/#copy
COPY --chown=dontforget:dontforget wsgi.py ${APP_DIR}/
COPY --chown=dontforget:dontforget src/dontforget ${APP_DIR}/dontforget/
COPY --chown=dontforget:dontforget migrations ${APP_DIR}/migrations/
