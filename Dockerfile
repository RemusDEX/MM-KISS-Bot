FROM python:3.12-slim

# Add system-level dependencies (including gcc and npm)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       libpq-dev gcc g++ make libffi-dev build-essential \
       curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install -U pip && pip install poetry

# Create app directory
RUN mkdir /app
WORKDIR /app

# Copy the pyproject.toml and poetry.lock files into container's /app/ directory
COPY pyproject.toml poetry.lock /app/

# Install dependencies from the poetry.lock file
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-root

# Copy the rest of the application code
COPY . /app

#Run application
CMD ["python3", "main.py"]
