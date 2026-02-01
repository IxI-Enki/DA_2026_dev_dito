# Tasks: Stack-G Docker Services

## Progress Tracker

| Phase | Tasks | Completed | Progress |
|-------|-------|-----------|----------|
| Phase 1: Evaluator | 4 | 4 | 100% |
| Phase 2: Embedder | 4 | 4 | 100% |
| Phase 3: Deployer | 4 | 4 | 100% |
| Phase 4: Integration | 4 | 0 | 0% |
| **Total** | **16** | **12** | **75%** |

---

## Phase 1: Module Evaluator (Estimated: 30 min)

### Task 1.1: Create Dockerfile
- [x] Create `backend_services/module_evaluator/Dockerfile`
- [x] Base: `python:3.11-slim`
- [x] Install: curl, ca-certificates
- [x] Copy requirements.txt and install
- [x] Copy entrypoint.py
- [x] Set ENTRYPOINT

**Acceptance Criteria:**
- [x] `docker compose build module_evaluator` succeeds

### Task 1.2: Create entrypoint.py
- [x] Create `backend_services/module_evaluator/entrypoint.py`
- [x] Parse job_id from sys.argv or generate
- [x] Inline ProgressTracker class
- [x] Find latest fetch directory
- [x] Call evaluator.py with correct paths
- [x] Update progress at each evaluation step
- [x] Handle success/error states

**Acceptance Criteria:**
- [x] Entrypoint runs evaluator and writes progress to `/data/logs/pipeline_progress.json`

### Task 1.3: Create requirements.txt
- [x] Create `backend_services/module_evaluator/requirements.txt`
- [x] Add: pyyaml, requests

**Acceptance Criteria:**
- [x] All imports in evaluator.py are satisfied

### Task 1.4: Enable in docker-compose.yml
- [x] Enable `module_evaluator` service
- [x] Add volumes: /config, /data, /pipeline/02_deep_evaluation
- [x] Add environment variables
- [x] Add to devdito_network
- [x] Set profile: pipeline

**Acceptance Criteria:**
- [x] `docker compose --profile pipeline run --rm module_evaluator test_job` starts container

---

## Phase 2: Module Embedder (Estimated: 30 min)

### Task 2.1: Create Dockerfile
- [x] Create `backend_services/module_embedder/Dockerfile`
- [x] Base: `python:3.11-slim`
- [x] Install: curl, ca-certificates, gcc, g++ (for numpy/tiktoken)
- [x] Copy and install requirements
- [x] Copy entrypoint.py

**Acceptance Criteria:**
- [x] `docker compose build module_embedder` succeeds

### Task 2.2: Create entrypoint.py
- [x] Create `backend_services/module_embedder/entrypoint.py`
- [x] Find input from /data/fetched/ or /data/evaluated/
- [x] Call main.py with correct paths
- [x] Report progress: chunks processed / total
- [x] Output to /data/embeddings/

**Acceptance Criteria:**
- [x] Produces `embedded_chunks.jsonl` in /data/embeddings/

### Task 2.3: Create requirements.txt
- [x] Create `backend_services/module_embedder/requirements.txt`
- [x] Add: pyyaml, openai, tiktoken, numpy, requests

**Acceptance Criteria:**
- [x] All embedder imports satisfied

### Task 2.4: Enable in docker-compose.yml
- [x] Enable `module_embedder` service
- [x] Add volumes
- [x] Add OPENAI_API_KEY from host env
- [x] Add to devdito_network

**Acceptance Criteria:**
- [x] Container starts and can connect to OpenAI API

---

## Phase 3: Module Deployer (Estimated: 30 min)

### Task 3.1: Create Dockerfile
- [x] Create `backend_services/module_deployer/Dockerfile`
- [x] Base: `python:3.11-slim`
- [x] Install: curl, ca-certificates
- [x] Copy and install requirements

**Acceptance Criteria:**
- [x] `docker compose build module_deployer` succeeds

### Task 3.2: Create entrypoint.py
- [x] Create `backend_services/module_deployer/entrypoint.py`
- [x] Load embeddings from /data/embeddings/*.jsonl
- [x] Connect to Qdrant at qdrant_db:6333
- [x] Create collection if not exists
- [x] Upload vectors in batches (100 per batch)
- [x] Report progress: vectors uploaded / total

**Acceptance Criteria:**
- [x] Vectors appear in Qdrant collection after run

### Task 3.3: Create requirements.txt
- [x] Create `backend_services/module_deployer/requirements.txt`
- [x] Add: pyyaml, qdrant-client>=1.7.0, numpy

**Acceptance Criteria:**
- [x] Qdrant client can connect

### Task 3.4: Enable in docker-compose.yml
- [x] Enable `module_deployer` service
- [x] Add depends_on: qdrant_db (condition: service_healthy)
- [x] Add volumes
- [x] Add QDRANT_HOST, QDRANT_PORT env vars

**Acceptance Criteria:**
- [x] Container waits for Qdrant health before starting

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
