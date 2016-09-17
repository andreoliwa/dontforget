FROM python:3.5
ENV TERM xterm-256color
RUN apt-get update && apt-get install -y vim lsof less --no-install-recommends --no-install-suggests && apt-get clean
RUN pip install -U pip

RUN mkdir /dontforget
WORKDIR /dontforget

ADD requirements/prod.txt requirements.txt
RUN pip install -r requirements.txt

ADD . /dontforget
