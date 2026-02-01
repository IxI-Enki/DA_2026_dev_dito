# =============================================================================
# Dev Dito - Module Evaluator
# =============================================================================
# Executes the Content Evaluator (evaluator.py) inside Docker.
# Constitution Article VII: Thin Wrapper only!
#
# Build: docker compose build module_evaluator
# Run:   docker compose --profile pipeline run --rm module_evaluator <job_id>
# =============================================================================

FROM python:3.11-slim

LABEL maintainer="Jan Ritt <j.ritt@htl-leonding.ac.at>"
LABEL description="Dev Dito Content Evaluator Module"
LABEL version="0.1.0"

# Environment
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV CONFIG_PATH=/config/env.yaml
ENV DATA_PATH=/data
ENV PIPELINE_PATH=/pipeline/02_deep_evaluation

WORKDIR /app

# System dependencies (ignore time-based validity checks)
RUN apt-get -o Acquire::Check-Valid-Until=false -o Acquire::Check-Date=false update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Entrypoint script
COPY entrypoint.py .

# Default command
ENTRYPOINT ["python", "entrypoint.py"]
