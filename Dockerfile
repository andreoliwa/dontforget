FROM python:3.6

ENV TERM xterm-256color

RUN mkdir /dontforget
WORKDIR /dontforget

RUN apt-get update && apt-get install -y vim lsof less --no-install-recommends --no-install-suggests && apt-get clean
RUN pip install -U pip pipenv

COPY Pipfile.lock .
RUN pipenv install --dev

COPY . /dontforget
