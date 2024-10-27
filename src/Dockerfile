FROM python:3.10-alpine

WORKDIR /app/src

COPY ./src/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./src .

WORKDIR /app/migrations
COPY ./migrations .

WORKDIR /app
COPY alembic.ini .
