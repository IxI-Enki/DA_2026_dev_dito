# =============================================================================
# Dev Dito - Module Fetcher
# =============================================================================
# Executes the Wiki Fetcher (fetch_full_wiki_extended.py) inside Docker.
# Constitution Article VII: Thin Wrapper only!
#
# Build: docker compose build module_fetcher
# Run:   docker compose run --rm module_fetcher <job_id>
# =============================================================================

FROM python:3.11-slim

LABEL maintainer="Jan Ritt <j.ritt@htl-leonding.ac.at>"
LABEL description="Dev Dito Wiki Fetcher Module"
LABEL version="0.1.0"

# Environment
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV CONFIG_PATH=/config/env.yaml
ENV DATA_PATH=/data
ENV PIPELINE_PATH=/pipeline/01_wiki_fetcher

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Entrypoint script
COPY entrypoint.py .

ENTRYPOINT ["python", "entrypoint.py"]
