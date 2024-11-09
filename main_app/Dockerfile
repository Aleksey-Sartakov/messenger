FROM python:3.10-alpine

WORKDIR /app/main_app

COPY ./main_app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./main_app .

WORKDIR /app/migrations
COPY ./migrations .

WORKDIR /app
COPY alembic.ini .
