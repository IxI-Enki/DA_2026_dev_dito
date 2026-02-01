# Tasks: Stack-G Docker Services

## Progress Tracker

| Phase | Tasks | Completed | Progress |
|-------|-------|-----------|----------|
| Phase 1: Evaluator | 4 | 0 | 0% |
| Phase 2: Embedder | 4 | 0 | 0% |
| Phase 3: Deployer | 4 | 0 | 0% |
| Phase 4: Integration | 4 | 0 | 0% |
| **Total** | **16** | **0** | **0%** |

---

## Phase 1: Module Evaluator (Estimated: 30 min)

### Task 1.1: Create Dockerfile
- [ ] Create `backend_services/module_evaluator/Dockerfile`
- [ ] Base: `python:3.11-alpine`
- [ ] Install: curl, ca-certificates
- [ ] Copy requirements.txt and install
- [ ] Copy entrypoint.py
- [ ] Set ENTRYPOINT

**Acceptance Criteria:**
- `docker build -t module_evaluator backend_services/module_evaluator` succeeds

### Task 1.2: Create entrypoint.py
- [ ] Create `backend_services/module_evaluator/entrypoint.py`
- [ ] Parse job_id from sys.argv or generate
- [ ] Add progress_tracker.py to path
- [ ] Find latest fetch directory
- [ ] Call evaluator.py with:
  - `--fetch-dir /data/fetched/<latest>/`
  - `--output /data/evaluated/`
- [ ] Update progress at each evaluation step
- [ ] Handle success/error states

**Acceptance Criteria:**
- Entrypoint runs evaluator and writes progress to `/data/logs/pipeline_progress.json`

### Task 1.3: Create requirements.txt
- [ ] Create `backend_services/module_evaluator/requirements.txt`
- [ ] Add: pyyaml, requests

**Acceptance Criteria:**
- All imports in evaluator.py are satisfied

### Task 1.4: Enable in docker-compose.yml
- [ ] Uncomment `module_evaluator` service
- [ ] Add volumes: /config, /data, /pipeline/02_deep_evaluation
- [ ] Add environment variables
- [ ] Add to devdito_network
- [ ] Set profile: pipeline

**Acceptance Criteria:**
- `docker compose --profile pipeline run --rm module_evaluator test_job` starts container

---

## Phase 2: Module Embedder (Estimated: 30 min)

### Task 2.1: Create Dockerfile
- [ ] Create `backend_services/module_embedder/Dockerfile`
- [ ] Base: `python:3.11-alpine`
- [ ] Install: curl, ca-certificates, gcc (for numpy)
- [ ] Copy and install requirements
- [ ] Copy entrypoint.py

**Acceptance Criteria:**
- `docker build -t module_embedder backend_services/module_embedder` succeeds

### Task 2.2: Create entrypoint.py
- [ ] Create `backend_services/module_embedder/entrypoint.py`
- [ ] Find input from /data/fetched/ or /data/evaluated/
- [ ] Run chunking with content_aware_chunker.py
- [ ] Run embedding with embedder.py
- [ ] Report progress: chunks processed / total
- [ ] Output to /data/embeddings/

**Acceptance Criteria:**
- Produces `embedded_chunks.jsonl` in /data/embeddings/

### Task 2.3: Create requirements.txt
- [ ] Create `backend_services/module_embedder/requirements.txt`
- [ ] Add: pyyaml, openai, tiktoken, numpy, requests

**Acceptance Criteria:**
- All embedder imports satisfied

### Task 2.4: Enable in docker-compose.yml
- [ ] Uncomment `module_embedder` service
- [ ] Add volumes
- [ ] Add OPENAI_API_KEY from host env
- [ ] Add to devdito_network

**Acceptance Criteria:**
- Container starts and connects to OpenAI API

---

## Phase 3: Module Deployer (Estimated: 30 min)

### Task 3.1: Create Dockerfile
- [ ] Create `backend_services/module_deployer/Dockerfile`
- [ ] Base: `python:3.11-alpine`
- [ ] Install: curl, ca-certificates
- [ ] Copy and install requirements

**Acceptance Criteria:**
- `docker build -t module_deployer backend_services/module_deployer` succeeds

### Task 3.2: Create entrypoint.py
- [ ] Create `backend_services/module_deployer/entrypoint.py`
- [ ] Load embeddings from /data/embeddings/embedded_chunks.jsonl
- [ ] Connect to Qdrant at qdrant_db:6333
- [ ] Create collection if not exists
- [ ] Upload vectors in batches (100 per batch)
- [ ] Report progress: vectors uploaded / total

**Acceptance Criteria:**
- Vectors appear in Qdrant collection after run

### Task 3.3: Create requirements.txt
- [ ] Create `backend_services/module_deployer/requirements.txt`
- [ ] Add: pyyaml, qdrant-client>=1.7.0

**Acceptance Criteria:**
- Qdrant client can connect

### Task 3.4: Enable in docker-compose.yml
- [ ] Uncomment `module_deployer` service
- [ ] Add depends_on: qdrant_db (condition: service_healthy)
- [ ] Add volumes
- [ ] Add QDRANT_HOST, QDRANT_PORT env vars

**Acceptance Criteria:**
- Container waits for Qdrant health before starting

---

## Phase 4: Integration (Estimated: 20 min)

### Task 4.1: Update Orchestrator server.py
- [ ] Verify STAGES dict has all 4 modules
- [ ] Verify container names match docker-compose.yml
- [ ] Test /run/{stage} for each stage

**Acceptance Criteria:**
- All stages trigger correct Docker container

### Task 4.2: Update PipelineOrchestrator.php
- [ ] Verify STAGES constant has all 4 modules
- [ ] Verify container names match

**Acceptance Criteria:**
- Dashboard shows all 4 stages

### Task 4.3: Test Dashboard Integration
- [ ] Start Orchestrator API
- [ ] Start Qdrant: `docker compose up -d qdrant_db`
- [ ] Trigger Fetch from Dashboard → verify success
- [ ] Trigger Evaluate from Dashboard → verify success
- [ ] Trigger Embed from Dashboard → verify success
- [ ] Trigger Deploy from Dashboard → verify success

**Acceptance Criteria:**
- Full pipeline runs from Dashboard with progress tracking

### Task 4.4: Verify Qdrant Data
- [ ] Query Qdrant REST API: `GET :6333/collections/wiki_embeddings`
- [ ] Verify points_count > 0
- [ ] Run test search query

**Acceptance Criteria:**
- Semantic search returns relevant results

---

## Completion Checklist

- [ ] All 4 Docker services build successfully
- [ ] All 4 Docker services run with progress tracking
- [ ] Dashboard can start/monitor/cancel all stages
- [ ] Full pipeline produces searchable embeddings
- [ ] Documentation updated
- [ ] Committed to branch `004-stack-g-docker-services`
