# Feature 004: Stack-G Docker Services

## Overview

| Field | Value |
|-------|-------|
| **Feature ID** | 004 |
| **Branch** | `004-stack-g-docker-services` |
| **Status** | Draft |
| **Created** | 2026-02-01 |
| **Author** | Jan Ritt (IxI-Enki) |

## Problem Statement

### Current Situation
The Dev Dito pipeline currently has:
- **Working**: `module_fetcher` Docker service with progress tracking
- **Missing**: `module_evaluator`, `module_embedder`, `module_deployer` as Docker services
- **Manual**: Pipeline modules must be run as local Python scripts
- **Incomplete**: Dashboard shows "NIE AUSGEFUEHRT" for missing services

### User Needs
As a **wiki administrator**, I need to:
1. Start all pipeline stages from the DokuWiki Dashboard
2. Monitor progress of each stage in real-time
3. Have a fully automated Wiki-to-Qdrant pipeline
4. Not require local Python installation on the server

### Business Impact
- **Automation**: Full end-to-end pipeline from Dashboard
- **Portability**: Docker containers work on any server
- **Consistency**: Same environment in dev and production
- **Monitoring**: All stages report progress to Dashboard

---

## Functional Requirements

### FR-1: Module Evaluator Service

#### FR-1.1: Docker Container
| ID | Requirement |
|----|-------------|
| FR-1.1.1 | Service SHALL be defined in `backend_services/docker-compose.yml` |
| FR-1.1.2 | Container SHALL use Python 3.11+ Alpine base image |
| FR-1.1.3 | Container SHALL mount `/config`, `/data`, `/pipeline/02_deep_evaluation` |
| FR-1.1.4 | Container SHALL use `pipeline` profile (not auto-start) |

#### FR-1.2: Entrypoint
| ID | Requirement |
|----|-------------|
| FR-1.2.1 | Entrypoint SHALL accept job_id as argument |
| FR-1.2.2 | Entrypoint SHALL write progress to `/data/logs/pipeline_progress.json` |
| FR-1.2.3 | Entrypoint SHALL call `evaluator.py` with correct paths |
| FR-1.2.4 | Entrypoint SHALL handle errors and update job status |

### FR-2: Module Embedder Service

#### FR-2.1: Docker Container
| ID | Requirement |
|----|-------------|
| FR-2.1.1 | Service SHALL be defined in `backend_services/docker-compose.yml` |
| FR-2.1.2 | Container SHALL support OpenAI API and local LLM (Ollama) |
| FR-2.1.3 | Container SHALL mount `/config`, `/data`, `/pipeline/03_embeddings_creator` |
| FR-2.1.4 | Container SHALL use `pipeline` profile |

#### FR-2.2: Entrypoint
| ID | Requirement |
|----|-------------|
| FR-2.2.1 | Entrypoint SHALL write progress (chunks processed / total) |
| FR-2.2.2 | Entrypoint SHALL support batch processing for large datasets |
| FR-2.2.3 | Entrypoint SHALL output embeddings to `/data/embeddings/` |

### FR-3: Module Deployer Service

#### FR-3.1: Docker Container
| ID | Requirement |
|----|-------------|
| FR-3.1.1 | Service SHALL be defined in `backend_services/docker-compose.yml` |
| FR-3.1.2 | Container SHALL connect to Qdrant via Docker network |
| FR-3.1.3 | Container SHALL mount `/config`, `/data` |
| FR-3.1.4 | Container SHALL depend on `qdrant_db` health check |

#### FR-3.2: Entrypoint
| ID | Requirement |
|----|-------------|
| FR-3.2.1 | Entrypoint SHALL upload embeddings to Qdrant collection |
| FR-3.2.2 | Entrypoint SHALL report upload progress (vectors / total) |
| FR-3.2.3 | Entrypoint SHALL verify collection after upload |

### FR-4: Orchestrator Integration

#### FR-4.1: Dashboard Integration
| ID | Requirement |
|----|-------------|
| FR-4.1.1 | All stages SHALL be startable from DokuWiki Dashboard |
| FR-4.1.2 | All stages SHALL show real-time progress |
| FR-4.1.3 | All stages SHALL support cancellation |
| FR-4.1.4 | Stage dependencies SHALL be enforced (fetch → evaluate → embed → deploy) |

---

## Non-Functional Requirements

### NFR-1: Performance
| ID | Requirement |
|----|-------------|
| NFR-1.1 | Container startup SHALL be < 5 seconds |
| NFR-1.2 | Progress updates SHALL be written every 2 seconds |
| NFR-1.3 | Memory usage SHALL be < 2GB per container |

### NFR-2: Reliability
| ID | Requirement |
|----|-------------|
| NFR-2.1 | Containers SHALL gracefully handle SIGTERM |
| NFR-2.2 | Failed jobs SHALL update status file before exit |
| NFR-2.3 | Partial progress SHALL be saved on failure |

### NFR-3: Consistency
| ID | Requirement |
|----|-------------|
| NFR-3.1 | All modules SHALL follow the same Dockerfile pattern |
| NFR-3.2 | All modules SHALL use the same entrypoint structure |
| NFR-3.3 | All modules SHALL use ProgressTracker for updates |

---

## Technical Constraints

### TC-1: Existing Architecture
- Must use existing `progress_tracker.py` pattern
- Must integrate with existing Orchestrator API
- Must follow Constitution Article VII (thin wrappers)

### TC-2: Docker
- No Docker socket mounting in wiki container
- Orchestrator runs on host, triggers `docker compose run`
- Containers use `devdito_network` for inter-service communication

### TC-3: Configuration
- All config from `/config/env.yaml` (mounted)
- Secrets from `/config/secrets/` (mounted)
- Environment variables override paths for Docker context

---

## Design Decisions

### DD-001: Dockerfile Template
Use `backend_services/Dockerfile.module.template` as base for all modules.

### DD-002: Progress Tracker Reuse
Copy `progress_tracker.py` into each module or mount from shared location.

### DD-003: Entrypoint Pattern
All entrypoints follow:
```python
def main(job_id):
    tracker = ProgressTracker(job_id, stage)
    try:
        tracker.start()
        # ... do work with progress updates ...
        tracker.complete(stats)
    except Exception as e:
        tracker.error(str(e))
        sys.exit(1)
```

---

## Success Criteria

| Criteria | Measurement |
|----------|-------------|
| All 4 stages startable from Dashboard | Manual test |
| Real-time progress shown for each stage | Visual verification |
| Full pipeline runs end-to-end | Automated test |
| Qdrant contains valid embeddings after deploy | Query test |
