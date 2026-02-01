# =============================================================================
# Dev Dito Orchestrator
# =============================================================================
# Manages pipeline execution and provides status API for DokuWiki plugin
# =============================================================================

FROM python:3.11-slim

LABEL maintainer="Jan Ritt <github.com/IxI-Enki>"
LABEL description="Dev Dito Pipeline Orchestrator API"

WORKDIR /app

# Install system dependencies
RUN apt-get update -o Acquire::Check-Valid-Until=false -o Acquire::Check-Date=false \
    && apt-get install -y --no-install-recommends \
        curl \
        docker.io \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY server.py .

# Expose API port
EXPOSE 8089

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8089/health || exit 1

# Run the server
CMD ["python", "server.py"]
