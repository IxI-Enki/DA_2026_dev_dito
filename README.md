---
title: Dev Dito -- Expert Architecture Review
description: Collaborative expert review of the dev_dito repository (Stack-G) covering Docker infrastructure, codebase architecture, and thesis alignment.
author:
  name: Jan Ritt
  github: 'https://github.com/IxI-Enki'
version: 1.0.0
created: 2026-02-13
updated: 2026-02-13
tags: [dev-dito, architecture-review, docker, evaluation, diploma-thesis, stack-g]
---

# Dev Dito -- Expert Architecture Review

> **Purpose**: This README captures the collaborative findings of three expert agents (Docker, Software Architect, Thesis) analyzing the dev_dito repository for professional cleanup. Each section is written by one expert, followed by a second iteration where experts comment on each other's findings. A final section by the Spec-Kit Architect compares these proposals against the Constitution.

---

## 1. Docker Expert -- Current State Assessment

### 1.1 Executive Summary

The `dev_dito/` repository is a diploma thesis project (Stack-G in a 9-stack ecosystem) that combines a DokuWiki plugin (PHP), a Python pipeline, an evaluation framework, and Docker-based backend services. The Docker infrastructure is **functional but organically grown**, with several architectural debts: DooD (Docker-outside-of-Docker) via socket mounting (deprecated per Constitution Article XIII), duplicated status management code across entrypoints, missing resource limits on most services, and a `:latest` tag violation on the DokuWiki image.

The module template (`DA_2026_service_module_template`) in the external `dev_dito_modules/` repo defines a "Guru-pattern" for services but is **entirely empty** (all template files are 1-line stubs). The fetcher skeleton (`DA_2026_service_module_fetcher`) is a copy of the template with placeholder variables renamed but no actual implementation. Neither template has been adopted into the main `dev_dito/` repository.

### 1.2 Key Findings

**Docker-compose.yml**
- GOOD: Named volumes, external network, profiles (`wiki`, `pipeline`, `test`), health checks on all always-on services
- GOOD: Qdrant image pinned to `v1.13.2`
- BAD: DokuWiki uses `lscr.io/linuxserver/dokuwiki:latest` -- violates Article XII
- BAD: No `deploy.resources.limits` on ANY service -- violates Article XII
- BAD: Orchestrator mounts `/var/run/docker.sock` -- DooD, deprecated per Article XIII
- BAD: No `start_period` on health checks for Qdrant (slow starter)
- BAD: Pipeline modules have no health checks (run-to-completion, but still no signal handling)
- BAD: `module_fetcher` mounts `../config.py:/app/config.py:ro` -- leaks root-level Python file into container

**Orchestrator**
- Functional FastAPI server with DooD path discovery via `docker inspect`
- Dual-mode: container (DooD via docker.sock) vs host (`docker compose run`)
- Status management via JSON file on shared volume
- 666 lines, well-structured but carries DooD complexity that should be removed

**Entrypoints**
- All follow the same "thin wrapper" pattern (Article VII compliant)
- Each duplicates ~60 lines of status management boilerplate (load/save/update JSON)
- `module_deployer/entrypoint.py` contains actual Qdrant upload logic (377 LOC) -- NOT thin
- No shared base class or library for status management

**Dockerfiles**
- All use `python:3.11-slim` -- good base choice
- None use multi-stage builds -- image size not optimized
- None create non-root users -- security concern
- `Dockerfile.module.template` exists but is generic and not DRY with actual Dockerfiles

**Orphaned services (no compose reference)**
- `backend_services/qdrant_db/` -- has Dockerfile, init_collection.py, but compose uses official `qdrant/qdrant:v1.13.2` directly
- `backend_services/wiki_dev_mcp_server/` -- belongs to Stack-H per constitution
- `backend_services/embeddings/` -- contains only a README.md placeholder

**Module Template vs Current Reality**

| Aspect          | Module Template (Guru Pattern)                                | Current backend_services/     |
| --------------- | ------------------------------------------------------------- | ----------------------------- |
| Structure depth | `services/<name>/src/<name>/core/adapters/common/` (6 levels) | `module_<name>/` (1 level)    |
| Build system    | `pyproject.toml` per service                                  | `requirements.txt` per module |
| Testing         | `tests/unit/`, `tests/integration/`, `conftest.py`            | No per-module tests           |
| Config          | `config/settings.yaml`, `config/logging.conf`                 | Environment variables only    |

**Assessment**: The Guru pattern is designed for permanent services with complex domain logic. The current pipeline modules are run-to-completion thin wrappers around existing scripts. The Guru pattern is **over-engineered** for this use case. The constitution explicitly acknowledges this in the scope boundaries.

### 1.3 Complete Current File Tree

```tree
dev_dito/                                          # KEEP - Repository root for Stack-G
|-- .claude/                                       # KEEP - Claude Code agent commands (speckit)
|   +-- commands/                                  # KEEP - 8 speckit slash commands
|
|-- .cursor/                                       # KEEP - Cursor IDE integration
|   |-- commands/                                  # KEEP - 9 speckit commands
|   +-- plans/                                     # REVIEW - 4 Cursor-generated plans (may be stale)
|
|-- .github/                                       # KEEP - GitHub integration
|   |-- workflows/
|   |   |-- ci.yml                                 # KEEP - CI pipeline
|   |   +-- issue-from-spec.yml                    # KEEP - Auto-issue creation
|   |-- ISSUE_TEMPLATE/                            # KEEP - Bug + feature templates
|   |-- BRANCH_PROTECTION.md                       # KEEP - Branch rules documentation
|   +-- PULL_REQUEST_TEMPLATE.md                   # KEEP - PR template
|
|-- .planning/                                     # MOVE to docs/ - scattered planning files
|   |-- .archive/                                  # KEEP archived plans for reference
|   |-- architecture.md                            # MOVE to docs/architecture.md
|   |-- dev_dito_icon.png                          # MOVE to docs/assets/
|   |-- dev_dito_pipeline_manager.md               # MOVE to docs/
|   |-- README_ARCHITECTURE.md                     # MOVE to docs/
|   +-- sources_dev_dito.yaml                      # KEEP as reference - pipeline source map
|
|-- .prompts/                                      # REVIEW - Agent prompt files
|   |-- Next_Prompt_Feat_006.improved.md           # KEEP - Feature 006 planning
|   |-- Next_Prompt_Feat_006.md                    # DELETE - Superseded by .improved version
|   +-- Prompt.md                                  # REVIEW - May overlap with constitution
|
|-- .specify/                                      # KEEP - Speckit framework
|   |-- memory/
|   |   +-- constitution.md                        # KEEP - Project constitution v1.3.0
|   |-- scripts/powershell/                        # KEEP - 5 speckit utility scripts
|   +-- templates/                                 # KEEP - 5 spec/plan/task templates
|
|-- backend_services/                              # REFACTOR - Docker service definitions
|   |-- .env                                       # KEEP - Local env (gitignored)
|   |-- .env.template                              # KEEP - Env template for new setups
|   |-- docker-compose.yml                         # REFACTOR - Need resource limits, pin DokuWiki, remove DooD
|   |-- Dockerfile.module.template                 # REFACTOR - Not DRY with actual Dockerfiles
|   |-- README.md                                  # KEEP
|   |-- orchestrator/                              # REFACTOR - Remove DooD, simplify to compose-only
|   |   |-- Dockerfile                             # REFACTOR - Add non-root user, remove docker.io dep
|   |   |-- requirements.txt                       # KEEP
|   |   +-- server.py                              # REFACTOR - Remove DooD path, keep compose-run path
|   |-- module_fetcher/                            # KEEP - Thin wrapper
|   |   |-- Dockerfile                             # REFACTOR - Add non-root user
|   |   |-- entrypoint.py                          # KEEP
|   |   |-- install_cert.sh                        # KEEP
|   |   +-- requirements.txt                       # KEEP
|   |-- module_evaluator/                          # KEEP - Thin wrapper
|   |-- module_preprocessor/                       # KEEP - Thin wrapper
|   |-- module_embedder/                           # KEEP - Thin wrapper
|   |-- module_deployer/                           # REFACTOR - entrypoint.py has business logic (377 LOC)
|   |-- qdrant_db/                                 # DELETE - Orphaned, not referenced in compose
|   |-- wiki_dev_mcp_server/                       # DELETE - Belongs to Stack-H (Article XIV)
|   +-- embeddings/                                # DELETE - Empty placeholder
|
|-- config/                                        # KEEP - Centralized configuration (Article II-B)
|   |-- env.yaml                                   # KEEP - Active config (gitignored)
|   |-- env.development.yaml                       # KEEP - Dev overrides
|   |-- env.minimal.yaml                           # KEEP - Minimal config
|   |-- PLACEHOLDER_env.yaml                       # KEEP - Template for new setups
|   |-- settings.json                              # KEEP - Auto-generated from env.yaml
|   |-- sources.yaml                               # KEEP - Wiki source definitions
|   +-- secrets/                                   # KEEP - Secret files (gitignored)
|       |-- README.md                              # KEEP - Documents required secrets
|       +-- .gitkeep                               # KEEP
|
|-- data/                                          # KEEP - Pipeline data output (gitignored content)
|   |-- embeddings/.gitkeep                        # KEEP
|   |-- evaluated/.gitkeep                         # KEEP
|   |-- fetched/.gitkeep                           # KEEP (runtime data gitignored)
|   |-- logs/.gitkeep                              # KEEP
|   |-- logs/pipeline_runs.schema.json             # KEEP - Schema for status tracking
|   +-- preprocessed/.gitkeep                      # KEEP
|
|-- dokuwiki_plugin/                               # KEEP - DokuWiki plugin (PHP layer)
|   |-- action.php                                 # KEEP - Event hooks and AJAX handlers
|   |-- admin.php                                  # KEEP - Admin page controller
|   |-- logo.png                                   # KEEP
|   |-- plugin.info.txt                            # KEEP
|   |-- conf/                                      # KEEP - Plugin configuration
|   |-- dist/                                      # KEEP - Compiled frontend assets
|   |-- lang/                                      # KEEP - i18n (de, en)
|   +-- lib/                                       # KEEP - PHP helper classes
|
|-- evaluation/                                    # KEEP - Thesis evaluation infrastructure (Article X)
|   |-- __init__.py                                # KEEP
|   |-- config.py                                  # KEEP - ExperimentConfig frozen dataclass
|   |-- requirements.txt                           # KEEP
|   |-- README.md                                  # KEEP
|   |-- experiments/                               # KEEP - 8 YAML experiment configs
|   |-- ground_truth/                              # KEEP - 50 verified Q&A pairs
|   |-- metrics/                                   # KEEP - Pure functions (MRR, P@K, NDCG)
|   |-- providers/                                 # KEEP - Embedding providers (Ollama, OpenAI)
|   |-- results/                                   # KEEP - Experiment outputs (gitignored)
|   |-- scripts/                                   # KEEP - 5 thesis evaluation scripts
|   +-- tests/                                     # KEEP - 56+ passing tests
|
|-- pipeline/                                      # KEEP - Pipeline modules (Python layer)
|   |-- 01_wiki_fetcher/                           # KEEP - Stage 1: Content acquisition
|   |   |-- config/                                # KEEP - Module-level config placeholders
|   |   |-- api_client.py                          # KEEP - WikiAPIClient (JSON-RPC)
|   |   |-- config.py                              # KEEP - Module config
|   |   +-- (12 more files)                        # KEEP - All fetcher functionality
|   |-- 02_deep_evaluation/                        # KEEP - Stage 2: Content analysis
|   |   |-- env.yaml                               # FIX - Points to prototype path, not dev_dito
|   |   |-- check_models.py                        # DELETE - Debug utility
|   |   |-- cleanup_strategies.py                  # DELETE - One-off script
|   |   +-- (analyzers/, core/, generators/)       # KEEP - Analysis functionality
|   |-- 03_embeddings_creator/                     # KEEP - Stage 4: Embedding creation
|   |   |-- env.yaml                               # FIX - Local env with hardcoded paths
|   |   +-- (7 files)                              # KEEP
|   |-- 03_rag_preprocessing/                      # KEEP - Stage 3: Wiki-to-Markdown
|   |   |-- env.yaml                               # FIX - Should use central config
|   |   +-- (5 files)                              # KEEP
|   +-- 04_deploy/                                 # KEEP - Stage 5: Qdrant deployment
|       |-- config.yaml                            # MERGE into central env.yaml
|       +-- (2 files)                              # KEEP
|
|-- scripts/                                       # KEEP - Operational PowerShell scripts
|   |-- _JANS_MULTISCRIPT_.ps1                     # REVIEW - Personal utility
|   +-- (5 more scripts + README)                  # KEEP
|
|-- specs/                                         # KEEP - Feature specifications (001-007)
|
|-- tests/                                         # KEEP - Root-level test suite
|   |-- conftest.py                                # KEEP
|   |-- integration/                               # KEEP
|   |-- smoke/                                     # KEEP - Docker smoke tests
|   +-- unit/                                      # KEEP - Config + schema tests
|
|-- config.py                                      # REFACTOR - Root-level shared config loader
|-- install.ps1                                    # KEEP - Installation script (Feature 006)
|-- README.md                                      # REWRITE - This file
+-- README_old.md                                  # DELETE - Superseded
```

### 1.4 Proposed Optimal Architecture

```
dev_dito/                                          # Repository root - Stack-G of 9-stack ecosystem
|-- .claude/commands/                              # Agent tooling - Claude Code speckit commands
|-- .cursor/commands/                              # Agent tooling - Cursor IDE speckit commands
|-- .github/                                       # CI/CD (workflows, templates, branch rules)
|-- .specify/                                      # Speckit framework (constitution + templates)
|
|-- backend_services/                              # Docker service definitions (Stack-G)
|   |-- .env + .env.template                       # Docker-specific env vars
|   |-- docker-compose.yml                         # Stack-G compose (profiles, limits, pinned)
|   |-- orchestrator/                              # FastAPI pipeline API (compose-run only, no DooD)
|   |-- module_fetcher/                            # Thin wrapper (Dockerfile + entrypoint.py + reqs)
|   |-- module_evaluator/                          # Thin wrapper
|   |-- module_preprocessor/                       # Thin wrapper
|   |-- module_embedder/                           # Thin wrapper
|   +-- module_deployer/                           # Thin wrapper (extract Qdrant logic to pipeline/)
|
|-- config/                                        # Centralized configuration (Article II-B)
|   |-- env.yaml                                   # Active config (gitignored)
|   |-- PLACEHOLDER_env.yaml                       # Documented template
|   |-- secrets/                                   # Token/cert files (gitignored)
|   +-- sources.yaml                               # Wiki source definitions
|
|-- data/                                          # Pipeline runtime data (gitignored)
|
|-- docs/                                          # Consolidated documentation
|   |-- architecture.md                            # System architecture overview
|   |-- pipeline-flow.md                           # Pipeline stage flow diagram
|   +-- sources_dev_dito.yaml                      # Full source reference
|
|-- dokuwiki_plugin/                               # DokuWiki plugin (PHP layer)
|-- evaluation/                                    # Thesis evaluation framework (HIGHEST PRIORITY)
|-- pipeline/                                      # Pipeline modules (Python, 5 stages)
|-- scripts/                                       # Operational PowerShell scripts
|-- specs/                                         # Feature specifications (001-007+)
|-- tests/                                         # Root-level test suite
|
|-- config.py                                      # Shared Python config loader
|-- install.ps1                                    # One-command installation
+-- README.md                                      # Project README
```

### 1.5 Docker-Compose Strategy

**Profiles**: `(default)` orchestrator+qdrant | `wiki` +dokuwiki | `pipeline` +modules | `test` +qdrant-test

**Resource Limits**: Qdrant 1g/1CPU, Orchestrator 512m/0.5CPU, Embedder 2g/2CPU, Others 512m/1CPU

**DooD Removal**: Remove socket mount, docker.io dep, DooD code paths. Keep compose-run only.

**Guru Template Verdict**: Do NOT adopt into dev_dito. Constitution Article VII mandates thin wrappers for <500 LOC. Template is for permanent services in other stacks (Stack-H, Stack-I).

### 1.6 Docker Expert Cleanup Priorities

| Priority    | Action                                                                                       | Effort |
| ----------- | -------------------------------------------------------------------------------------------- | ------ |
| P1          | Pin DokuWiki, add resource limits, add start_period, add .dockerignore, delete orphaned dirs | 1-2h   |
| P2          | DooD removal (socket mount, docker.io, DooD code paths)                                      | 2-4h   |
| P3          | Move .planning/ to docs/                                                                     | 1-2h   |
| POST-THESIS | Multi-stage builds, non-root users, shared status lib, init:true                             | Later  |

---

## 2. Software Architect -- Codebase Analysis & Optimization Proposals

### 2.1 Config Consolidation Analysis

**5 separate config.py files + 3 local env.yaml files alongside the central one:**

| Location                                   | Reads Central env.yaml?          | Has Own env.yaml?     | Notes                          |
| ------------------------------------------ | -------------------------------- | --------------------- | ------------------------------ |
| `config.py` (root)                         | YES (primary)                    | N/A                   | 438 LOC, typed exports         |
| `pipeline/01_wiki_fetcher/config.py`       | YES (central)                    | NO                    | 659 LOC, FetchConfig dataclass |
| `pipeline/02_deep_evaluation/config.py`    | **NO** (reads `research/` path!) | YES (prototype)       | VIOLATION                      |
| `pipeline/03_embeddings_creator/config.py` | NO (local env.yaml)              | YES (hardcoded paths) | VIOLATION                      |
| `pipeline/03_rag_preprocessing/config.py`  | NO (local env.yaml)              | YES (local)           | VIOLATION                      |
| `evaluation/config.py`                     | Partially                        | NO (experiment YAMLs) | Clean                          |

**Critical Issues:**
- `resolve_placeholders()` / `resolve_variables()` **copy-pasted 4 times** with minor variations
- `02_deep_evaluation/env.yaml` points OUTSIDE the repository to prototype location
- `03_embeddings_creator/env.yaml` has hardcoded absolute Windows paths
- Only `01_wiki_fetcher/config.py` actually uses the central `config/env.yaml`

### 2.2 Module Quality Assessment

| Module                              | Quality | Constitution    | Tests         | Overall                    |
| ----------------------------------- | ------- | --------------- | ------------- | -------------------------- |
| **evaluation/**                     | **A**   | Full compliance | 56 unit tests | Reference implementation   |
| **pipeline/01_wiki_fetcher/**       | **B**   | Good            | NO tests      | Mature but untested        |
| **pipeline/02_deep_evaluation/**    | **C**   | **VIOLATION**   | NO tests      | Needs rework               |
| **pipeline/03_embeddings_creator/** | **B-**  | Partial         | NO tests      | Functional, not integrated |
| **pipeline/03_rag_preprocessing/**  | **B**   | Partial         | NO tests      | Clean but isolated         |
| **pipeline/04_deploy/**             | **C-**  | **VIOLATION**   | NO tests      | Minimal                    |

### 2.3 Import Architecture: 23 sys.path Hacks

| Module                         | Hacks  | Notes                     |
| ------------------------------ | ------ | ------------------------- |
| `pipeline/02_deep_evaluation/` | **14** | Every file inserts parent |
| `evaluation/scripts/`          | 4      | Each inserts REPO_ROOT    |
| Others                         | 5      | Various                   |
| **evaluation/tests/**          | **0**  | Correct pattern           |

**Pragmatic decision:** Accept sys.path hacks for thesis timeline. Full restructuring = 8h + HIGH risk.

### 2.4 Dead Code

- `pipeline/02_deep_evaluation/check_models.py` -- DELETE
- `pipeline/02_deep_evaluation/cleanup_strategies.py` -- DELETE
- `backend_services/qdrant_db/` -- DELETE (orphaned)
- `backend_services/wiki_dev_mcp_server/` -- DELETE (Stack-H)
- `backend_services/embeddings/` -- DELETE (empty)

### 2.5 Software Architect Cleanup Priorities

**MUST-DO (5h total):**
1. Fix `02_deep_evaluation/env.yaml` to point to dev_dito paths (1h)
2. Consolidate `resolve_placeholders()` into one shared utility (2h)
3. Add `[project.dependencies]` to `pyproject.toml` (1h)

**SHOULD-DO:**
4. Migrate `03_embeddings_creator` + `03_rag_preprocessing` config to central (5h)
5. Add `__init__.py` to pipeline modules (30min)
6. Remove dead scripts (15min)
7. Merge `04_deploy/config.yaml` into central env.yaml (1h)

**Bottom Line:** `evaluation/` is exemplary -- use as reference. Pipeline modules are prototype-quality. Given deadline, invest only in MUST-DO (5h). Everything else is post-thesis.

---

## 3. Thesis Expert -- Completeness & Scope Assessment

### 3.1 Research Question Coverage

| ID                                 | Status       | Gap                                  |
| ---------------------------------- | ------------ | ------------------------------------ |
| **FF1** Semantic vs Keyword        | **PARTIAL**  | Scripts exist, no results generated  |
| **FF3** Embedding Model Comparison | **PARTIAL**  | Needs execution with all 3 models    |
| **J1** Test Corpus                 | **COMPLETE** | 50 pairs, exceeds minimum            |
| **J2** Model Comparison            | **PARTIAL**  | Code solid, needs execution          |
| **J3** DokuWiki Parsing            | **COMPLETE** | Needs thesis documentation           |
| **J4** Chunk Size Impact           | **PARTIAL**  | Framework complete, needs execution  |
| **J5** Qdrant Schema               | **COMPLETE** | Needs formal documentation           |
| **J6** Hybrid vs Dense             | **PARTIAL**  | "Hybrid" runs same dense search (D5) |
| **US5** LaTeX Export               | **COMPLETE** | All 4 thesis tables                  |

**Summary**: Frameworks built. Zero evaluation runs executed. Code ready; data missing.

### 3.2 Critical Gaps

1. **No evaluation results exist.** `evaluation/results/` is empty.
2. **Hybrid search is not truly hybrid.** Either implement BM25 payload index OR document as limitation.
3. **Thesis chapters not written.** 40 pages/student, deadline May 30.
4. **Root README.md** needs professional polish.

### 3.3 Scope Guard

| Essential (MUST DO)                  | Skip                          |
| ------------------------------------ | ----------------------------- |
| Execute all 5 eval scripts           | DooD migration                |
| Generate result JSONs + LaTeX tables | Additional Docker profiles    |
| Write thesis chapters 1-7            | More governance documents     |
| Document Qdrant schema formally      | CI/CD pipeline                |
| At least 1 end-to-end demo           | Additional QA pairs beyond 50 |

### 3.4 Key Takeaway

> The evaluation **framework** is thesis-ready. The **results** don't exist. The **thesis text** hasn't been written. Priority: **(1) Run evaluations, (2) Start writing, (3) Stop building infrastructure.** The code demonstrates engineering competence. The final 10% (execution + writing) represents 90% of the thesis grade.

---

## 4. Round 2 -- Expert Cross-Review

### Docker Expert -- Round 2 Cross-Review

**Agreements:**
- Config consolidation is critical. Multiple `env.yaml` files with hardcoded prototype paths make Docker builds brittle.
- `evaluation/` as reference implementation -- excellent. Clean separation, no sys.path hacks, proper testing.
- "Stop building infrastructure" -- absolutely. Code/results gap means Docker resource limits are premature optimization.

**Revised Docker Priorities (after reading colleagues):**

| Old                 | New                                  | Rationale                            |
| ------------------- | ------------------------------------ | ------------------------------------ |
| P1: Resource limits | **DEFER**                            | No results = no profiling data yet   |
| P2: DooD removal    | **DEFER**                            | Functional debt, not blocking thesis |
| **NEW P0**          | Fix prototype paths in configs       | Blocking containerization            |
| **NEW P1**          | Pin DokuWiki + add .dockerignore     | Quick wins for reproducibility       |
| **NEW P2**          | Health check start_period for Qdrant | Prevent flaky CI                     |

**Docker-specific additions:**
- `module_deployer/entrypoint.py` has 377 LOC of Qdrant logic -- NOT thin. Violates Article VII. Extract to `pipeline/04_deploy/`. (But defer -- not blocking thesis.)
- Cannot defer config fixes. Hardcoded prototype paths = broken containers = no reproducible results.
- Create `evaluation/Dockerfile` + compose service so thesis evaluations run in containers. 1h effort, high thesis value for reproducibility.

### Software Architect -- Round 2 Cross-Review

**Agreements:**
- DooD removal is correct per Article XIII, but from thesis perspective: **defer** (2-4h + test risk for zero thesis value)
- Guru template rejection is correct -- incompatible with thin wrappers
- Hybrid search gap (J6/D5): Qdrant BM25 payload indexes needed. Either implement or document as limitation + future work.

**Revised Architecture Priorities:**

| Priority | Task                                                                         | Effort | Reason                          |
| -------- | ---------------------------------------------------------------------------- | ------ | ------------------------------- |
| **P0**   | Fix `02_deep_evaluation` + `03_embeddings_creator` env.yaml paths            | 1h     | Blocks evaluation execution     |
| **P0**   | Delete orphaned dirs + dead scripts                                          | 15min  | Reduces confusion               |
| **P1**   | Pin DokuWiki, add resource limits to compose.yml                             | 1h     | Prevents demo-day failures      |
| **POST** | DooD removal, resolve_placeholders consolidation, module_deployer extraction | Later  | Code quality, not functionality |

**Bottom line:** Docker expert is right about technical debt. Thesis expert is right about priorities. My job is to unblock the evaluation pipeline (1h15min) and get out of the way.

### Thesis Expert -- Round 2 Cross-Review

**Agreements:**
- Docker P1 (limits, pin, .dockerignore): 1-2h, professional polish, zero risk -- DO IT
- Orphaned dir deletion: 15min cleanup -- DO IT
- Fix `02_deep_evaluation/env.yaml`: **HIGH impact** -- prevents broken runs
- Dead code removal: 15min, reduces noise -- DO IT
- Guru template rejection: Correct
- sys.path hack acceptance: Correct for timeline

**Disagreements:**
- DooD removal (Docker P2): **ZERO thesis impact** -- evaluator doesn't care. 2-4h + test risk. DEFER.
- `resolve_placeholders()` consolidation: **ZERO thesis impact** -- works today. 2h + cross-module risk. DEFER.
- Config migration for 03_embed/03_preproc: **ZERO thesis impact** -- modules work. 5h wasted. DEFER.

**Time Budget Reality Check:**
- ~170h of thesis-critical work remaining (writing, evaluation execution, demo)
- **Only 7.5h of proposed cleanup has non-zero thesis ROI**
- Docker + Architect proposed 17.5h total -- cut 10h that delivers no thesis value

**Final Unified Priority (all experts converge):**

**Tier 1: DO NOW (7.5h, zero thesis risk)**
1. Docker P1: Pin DokuWiki, resource limits, start_period, .dockerignore (1-2h)
2. Delete orphaned dirs + dead scripts (30min)
3. Fix `02_deep_evaluation/env.yaml` to dev_dito paths (1h)
4. Add `pyproject.toml` dependencies (1h)
5. Move `.planning/` to `docs/` (1-2h)
6. Professional README.md rewrite (2h)

**Tier 2: POST-THESIS**
- DooD removal, resolve_placeholders() consolidation, config migration, multi-stage builds, non-root users, sys.path refactor

**Then immediately: Execute evaluations, fix/document hybrid search, write thesis chapters.**

---

## 5. Spec-Kit Architect -- Constitution Comparison & Amendment Proposals

### 5.A Alignment Matrix

| Article  | Title                          | Expert Consensus                                                                                                                                         | Amendment?    |
| -------- | ------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------- |
| **I**    | Layered Module Architecture    | AGREE -- layer separation working                                                                                                                        | None          |
| **II**   | JSON Interface Standard        | AGREE -- JSON/JSONL consistent                                                                                                                           | None          |
| **II-B** | Centralized YAML Configuration | **EXTEND** -- mandate exists but massively violated (3/5 modules ignore central config). Per-module `config/env.yaml` pattern contradicts "centralized." | YES (Amend 1) |
| **III**  | Critical-Path Unit Testing     | **EXTEND** -- evaluation has 56 tests (exemplary), pipeline has zero. Enforcement references `qdrant_db/` which is orphaned.                             | YES (Amend 2) |
| **IV**   | Language Standards             | AGREE                                                                                                                                                    | None          |
| **V**    | Pragmatic Documentation        | **EXTEND** -- `.planning/` moving to `docs/`. `README_ARCHITECTURE.md` reference stale.                                                                  | YES (Amend 3) |
| **VI**   | Secret Containment             | AGREE -- working as designed                                                                                                                             | None          |
| **VII**  | Integration Simplicity Gate    | **EXTEND** -- `module_deployer` (377 LOC) violates "no business logic" but deferred. No measurable threshold.                                            | YES (Amend 4) |
| **VIII** | Direct Framework Usage         | AGREE -- RAGAS decision consistent                                                                                                                       | None          |
| **IX**   | Realistic Integration Testing  | **EXTEND** -- References non-existent `docker-compose.test.yml`. 23 sys.path hacks accepted for timeline.                                                | YES (Amend 5) |
| **X**    | Evaluation-First Development   | **EXTEND** -- Framework built but zero results generated. Article mandates infrastructure but not execution.                                             | YES (Amend 6) |
| **XI**   | Thesis Milestone Alignment     | **EXTEND** -- Deliverable status table stale (J1 shows "coming soon" but is COMPLETE).                                                                   | YES (Amend 7) |
| **XII**  | Resource Governance            | **DISAGREE on priority** -- Zero compliance today. Experts defer resource limits (no profiling data) but keep image pinning as P1.                       | YES (Amend 8) |
| **XIII** | DooD Deprecation               | AGREE -- All experts defer removal to post-thesis. Article already says "post-Evaluation."                                                               | None          |
| **XIV**  | Inter-Stack Communication      | AGREE -- `wiki_dev_mcp_server/` deletion consistent with article                                                                                         | None          |

### 5.B Proposed Constitution Amendments (v1.4.0)

#### Amendment 1: Article II-B -- Config Reality + Fix Path

**Current:** "ALLE Konfigurationswerte werden in YAML-Dateien (`config/env.yaml`) ausgelagert. Jedes Modul folgt dem gleichen Pattern wie der Wiki Fetcher."

**Problem:** Per-module `config/env.yaml` pattern encourages the fragmentation it forbids. `02_deep_evaluation` points to prototype path OUTSIDE repo.

**Proposed:** Distinguish central config (`config/env.yaml`) from module overrides. Add "Known Violations" subsection listing non-compliant modules with fix schedule: `02_deep_evaluation` = Tier 1 (blocking), others = post-thesis.

---

#### Amendment 2: Article III -- Update Test Enforcement

**Current enforcement:** "`backend_services/qdrant_db/` hat Tests fuer Collection-Schema-Validierung"

**Proposed:** Remove `qdrant_db/` reference (orphaned). Add: "`evaluation/` serves as reference implementation (56+ tests). Pipeline module tests deferred to post-thesis."

---

#### Amendment 3: Article V -- Update Documentation Locations

**Current:** "`README_ARCHITECTURE.md` im Repository-Root"

**Proposed:** Replace with `docs/architecture.md`. Add: "Consolidated documentation lives in `docs/`."

---

#### Amendment 4: Article VII -- Add Measurable Threshold

**Current:** "Modul-Wrapper enthalten keine eigene Business-Logik"

**Proposed:** Add: "Entrypoint MUST NOT exceed 100 LOC of non-boilerplate code. Business logic MUST reside in `pipeline/` modules." Known violation: `module_deployer` (377 LOC) deferred to post-thesis.

---

#### Amendment 5: Article IX -- Fix Stale References

**Current:** "`docker-compose.test.yml` fuer Test-Umgebung"

**Proposed:** Replace with: "Docker Compose test profile (`--profile test`) provides isolated test infrastructure."

---

#### Amendment 6: Article X -- Add Execution Mandate (MOST IMPORTANT)

**Current:** "Implementierung von Evaluations-Infrastruktur hat VORRANG"

**Problem:** Treats infrastructure as the goal. All experts: "framework built, zero results."

**Proposed:** Add subsection "Execution Mandate": "Evaluation infrastructure without executed results has ZERO thesis value. Generating result data (`evaluation/results/`) takes ABSOLUTE PRIORITY over any further infrastructure, documentation, or code cleanup."

New enforcement:
- Each research question (FF1, FF3) has at least one result JSON
- LaTeX tables generated from actual results, not placeholders

---

#### Amendment 7: Article XI -- Update Deliverable Status

**Proposed:** Update J1 to COMPLETE. Mark J2/J4/J6 as "Code Complete / Results Pending." Add J6 hybrid search note: "Dense search only. Either implement BM25 payload index OR document as limitation."

---

#### Amendment 8: Article XII -- Split Mandatory vs Deferred

**Current:** "Jeder Docker-Service MUSS memory/cpu limits definieren"

**Problem:** Creates priority conflict with Article X. Experts agree resource limits are premature without profiling data.

**Proposed:** Split into:
- **Tier 1 (NOW):** Image pinning (no `:latest`), health check `start_period`, `.dockerignore`
- **Tier 2 (AFTER eval results):** `deploy.resources.limits` calibrated from profiling

### 5.C New Sections Needed

#### C.1 Known Violations Register

Track intentionally-deferred violations. Prevents agents from "discovering" and re-triaging already-accepted debt.

| Article | Violation                                        | Status                 | Target             |
| ------- | ------------------------------------------------ | ---------------------- | ------------------ |
| II-B    | `02_deep_evaluation/env.yaml` prototype path     | Fix Scheduled (Tier 1) | 2026-02-28         |
| II-B    | `03_embeddings_creator/env.yaml` hardcoded paths | Deferred               | Post-thesis        |
| II-B    | `03_rag_preprocessing/env.yaml` local config     | Deferred               | Post-thesis        |
| VII     | `module_deployer/entrypoint.py` 377 LOC          | Accepted               | Post-thesis        |
| XII     | No resource limits on any service                | Accepted               | After eval results |
| XII     | DokuWiki image uses `:latest`                    | Fix Scheduled (Tier 1) | 2026-02-28         |

#### C.2 Dead Code Policy

Directories not referenced by compose, not imported by Python, and not documented in `docs/` MUST be deleted. Immediate deletions per expert consensus:
- `backend_services/qdrant_db/`, `wiki_dev_mcp_server/`, `embeddings/`
- `pipeline/02_deep_evaluation/check_models.py`, `cleanup_strategies.py`

### 5.D Articles to Deprecate

**None.** All 14 articles remain relevant. Experts recommend deferring enforcement, not removing governance.

### 5.E Priority Classification

**BLOCKING (apply before any cleanup work):**

| #   | Amendment                           | Rationale                                                         | Effort |
| --- | ----------------------------------- | ----------------------------------------------------------------- | ------ |
| 1   | Amend 6 (Art X execution mandate)   | Without this, agents keep building instead of running evaluations | 15min  |
| 2   | Amend 7 (Art XI deliverable status) | Stale table causes agents to re-implement completed work          | 30min  |
| 3   | Amend 1 (Art II-B config reality)   | Agents must know which configs to fix NOW vs defer                | 20min  |
| 4   | Section C.1 (Violations register)   | Prevents re-triaging already-accepted debt                        | 20min  |
| 5   | Amend 8 (Art XII tier split)        | Current "MUSS" for limits contradicts Art X priority              | 15min  |

**Total blocking amendments: ~1.5h of Constitution editing.**

**NICE-TO-HAVE (apply when convenient):**
- Amendments 2-5 (test checklist, docs location, LOC threshold, stale references)
- Sections C.2-C.3 (dead code policy, evaluation Dockerfile)

---

**Summary:** Constitution v1.3.0 is structurally sound. No fundamental architectural disagreements. Primary gaps: (1) Article X lacks execution mandate, (2) deliverable status stale, (3) Article XII conflicts with Article X on resource limits priority, (4) no mechanism for tracking deferred violations. Five blocking amendments (~1.5h) resolve these. Six cosmetic amendments can be applied opportunistically.
