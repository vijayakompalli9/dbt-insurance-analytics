# Offline, credential-free image that builds the project and exports sample output.
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DBT_SEND_ANONYMOUS_USAGE_STATS=false

WORKDIR /app
COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements-dev.txt

COPY . .
RUN pip install --no-cache-dir -e . --no-deps

RUN useradd --create-home analyst && chown -R analyst /app
USER analyst

# Default: full build (snapshot history + dbt build) and export of sample marts.
CMD ["make", "run"]
