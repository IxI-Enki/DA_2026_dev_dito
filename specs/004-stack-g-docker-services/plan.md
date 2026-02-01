# Implementation Plan: Stack-G Docker Services

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        DokuWiki Container                               │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  Dev Dito Plugin                                                 │   │
│  │  - admin.php (Dashboard UI)                                      │   │
│  │  - PipelineOrchestrator.php (HTTP client)                        │   │
│  └─────────────────────┬───────────────────────────────────────────┘   │
└────────────────────────│────────────────────────────────────────────────┘
                         │ HTTP (host.docker.internal:8089)
                         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  HOST: Orchestrator API (server.py :8089)                               │
│  - POST /run/{stage} → docker compose run module_{stage}                │
│  - GET /progress → reads pipeline_progress.json                         │
└────────────────────────│────────────────────────────────────────────────┘
                         │ docker compose run
                         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Stack-G: Dev Dito Services (docker-compose.yml)                        │
│                                                                         │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐      │
│  │ module_fetcher   │  │ module_evaluator │  │ module_embedder  │      │
│  │ (01_wiki_fetcher)│  │ (02_deep_eval)   │  │ (03_embeddings)  │      │
│  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘      │
│           │                     │                     │                 │
│           ▼                     ▼                     ▼                 │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  Shared Volumes: /config, /data, /pipeline/*                     │  │
│  │  - progress_tracker.py writes to /data/logs/pipeline_progress.json│  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  ┌──────────────────┐                                                   │
│  │ module_deployer  │────────────────┐                                  │
│  │ (04_deploy)      │                │                                  │
│  └──────────────────┘                ▼                                  │
│                              ┌──────────────────┐                       │
│                              │ qdrant_db        │                       │
│                              │ (vector store)   │                       │
│                              └──────────────────┘                       │
└─────────────────────────────────────────────────────────────────────────┘
```

## File Structure

```
backend_services/
├── docker-compose.yml          # Updated with all modules
├── Dockerfile.module.template  # Base template
├── module_fetcher/             # EXISTS
│   ├── Dockerfile
│   ├── entrypoint.py
│   └── requirements.txt
├── module_evaluator/           # TO CREATE
│   ├── Dockerfile
│   ├── entrypoint.py
│   └── requirements.txt
├── module_embedder/            # TO CREATE
│   ├── Dockerfile
│   ├── entrypoint.py
│   └── requirements.txt
└── module_deployer/            # TO CREATE
    ├── Dockerfile
    ├── entrypoint.py
    └── requirements.txt
```

## Phase 1: Module Evaluator

### 1.1 Create Dockerfile

```dockerfile
FROM python:3.11-alpine

WORKDIR /app

# Install dependencies
RUN apk add --no-cache curl ca-certificates

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy entrypoint
COPY entrypoint.py .

# Default command
ENTRYPOINT ["python", "entrypoint.py"]
```

### 1.2 Create entrypoint.py

Key logic:
1. Parse job_id from args or generate
2. Initialize ProgressTracker
3. Find latest fetch directory in /data/fetched/
4. Call evaluator.py with correct paths
5. Handle success/error and update status

### 1.3 Create requirements.txt

```
pyyaml>=6.0
requests>=2.31.0
```

### 1.4 Update docker-compose.yml

Uncomment and configure the `module_evaluator` service.

## Phase 2: Module Embedder

### 2.1 Create Dockerfile

Same pattern as evaluator, but include OpenAI dependencies.

### 2.2 Create entrypoint.py

Key logic:
1. Find evaluated data or fetched data
2. Run chunking (content_aware_chunker.py)
3. Run embedding (embedder.py)
4. Report progress per chunk batch

### 2.3 Dependencies

```
pyyaml>=6.0
openai>=1.0.0
tiktoken>=0.5.0
numpy>=1.24.0
```

## Phase 3: Module Deployer

### 3.1 Create Dockerfile

Same pattern, include qdrant-client.

### 3.2 Create entrypoint.py

Key logic:
1. Load embeddings from /data/embeddings/
2. Connect to Qdrant (qdrant_db:6333)
3. Create/recreate collection
4. Upload vectors in batches with progress

### 3.3 Dependencies

```
pyyaml>=6.0
qdrant-client>=1.7.0
```

## Phase 4: Integration

### 4.1 Update Orchestrator

Ensure `backend_services/orchestrator/server.py` correctly handles all stages.

### 4.2 Update PHP Plugin

Ensure `PipelineOrchestrator.php` has correct container names:
- `module_fetcher`
- `module_evaluator`
- `module_embedder`
- `module_deployer`

### 4.3 Test Full Pipeline

1. Start Orchestrator: `python backend_services/orchestrator/server.py`
2. Start Qdrant: `docker compose -f backend_services/docker-compose.yml up -d qdrant_db`
3. Run each stage via Dashboard
4. Verify Qdrant collection has embeddings

## Shared Components

### progress_tracker.py

All modules use the same progress tracker pattern from `pipeline/01_wiki_fetcher/progress_tracker.py`:

```python
from progress_tracker import ProgressTracker

tracker = ProgressTracker(job_id, "evaluate")
tracker.start()
tracker.update_step("[1/3] Loading data", current=0, total=100)
# ... work ...
tracker.complete(stats={"pages_evaluated": 209})
```

The tracker writes to `/data/logs/pipeline_progress.json` which the Orchestrator API serves.

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| LLM not available for evaluation | Make LLM optional, use heuristics as fallback |
| OpenAI API errors | Retry logic, rate limiting, local model fallback |
| Large embedding files | Streaming upload, batch processing |
| Qdrant connection issues | Health check dependency, retry on failure |
