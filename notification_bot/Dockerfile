FROM python:3.10-alpine

WORKDIR /bot

COPY ./notification_bot/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./notification_bot .
