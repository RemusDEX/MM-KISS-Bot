FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       libpq-dev gcc g++ make libffi-dev build-essential \
       curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install -U pip && pip install poetry

RUN mkdir /app
WORKDIR /app

COPY pyproject.toml poetry.lock /app/

RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-root

COPY . /app

CMD ["python3", "main.py"]
