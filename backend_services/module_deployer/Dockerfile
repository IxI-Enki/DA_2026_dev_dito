# =============================================================================
# Dev Dito - Module Deployer
# =============================================================================
# Uploads embeddings to Qdrant vector database.
# Constitution Article VII: Thin Wrapper only!
#
# Build: docker compose build module_deployer
# Run:   docker compose --profile pipeline run --rm module_deployer <job_id>
# =============================================================================

FROM python:3.11-slim

LABEL maintainer="Jan Ritt <janritt.office@gmail.com>"
LABEL description="Dev Dito Qdrant Deployer Module"
LABEL version="0.1.0"

# Environment
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV CONFIG_PATH=/config/env.yaml
ENV DATA_PATH=/data
ENV QDRANT_HOST=qdrant_db
ENV QDRANT_PORT=6333

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
