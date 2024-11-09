FROM python:3.10-alpine

WORKDIR /bot

COPY ./notification_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./notification_service .
