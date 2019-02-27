FROM python:3.6

ENV TERM xterm-256color
ENV DONTFORGET_DIR=/home/dontforget/dontforget-app

RUN apt-get update && \
    apt-get install -y vim lsof less --no-install-recommends --no-install-suggests && \
    apt-get clean && \
    pip3 install -U pip poetry && \
    groupadd dontforget -g 1000 && useradd dontforget -m -u 1000 -g dontforget && \
    mkdir ${DONTFORGET_DIR} && \
    chown -R dontforget:dontforget ${DONTFORGET_DIR}

WORKDIR ${DONTFORGET_DIR}

# Install Python modules as a normal user instead of root
USER dontforget:dontforget

# Whenever the project or the lock file changes, pip will be upgraded and packages will be reinstalled.
COPY --chown=dontforget:dontforget pyproject.toml poetry.lock ${DONTFORGET_DIR}/

# Upgrade pip version inside the virtualenv.
RUN poetry run pip3 install -U pip

# Install only the production packages
RUN poetry install --no-dev

# We still need individual COPY commands, because "The directory itself is not copied, just its contents":
# https://docs.docker.com/engine/reference/builder/#copy
COPY --chown=dontforget:dontforget autoapp.py manage.py ${DONTFORGET_DIR}/
COPY --chown=dontforget:dontforget dontforget ${DONTFORGET_DIR}/dontforget/
COPY --chown=dontforget:dontforget migrations ${DONTFORGET_DIR}/migrations/
