FROM python:3.10

ENV PYTHONUNBUFFERED=1

WORKDIR /usr/src/ludo_bot

COPY ./requirements.txt /usr/src/requirements.txt
RUN pip install --upgrade pip
RUN pip install -r /usr/src/requirements.txt

COPY . /usr/src/ludo_bot