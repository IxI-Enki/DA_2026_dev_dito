# Implementation Plan: DokuWiki Pipeline Integration Fix

**Branch**: `012-dokuwiki-pipeline-integration` | **Date**: 2026-02-23 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `specs/012-dokuwiki-pipeline-integration/spec.md`

## Summary

Fix 10 bugs and inconsistencies across the DokuWiki plugin (PHP), JS dashboard, and Python orchestrator so the pipeline runs correctly from the extension and manually. Ground truth: `pipeline/` and `evaluation/` — unchanged. The orchestrator (`backend_services/orchestrator/server.py`) bridges PHP and Docker; `pipeline_runs.json` is the shared PHP/Python status contract.

## Technical Context

**Language/Version**: Python 3.11+ (orchestrator/server.py), PHP 8.1+ (DokuWiki plugin), JavaScript ES2020 (pipeline.js, no framework)
**Primary Dependencies**: FastAPI + uvicorn + Pydantic v2 (orchestrator), DokuWiki Extension API + PSR-12 (plugin), Docker CLI / Docker Compose (stage execution)
**Storage**: `data/logs/pipeline_runs.json` (shared PHP/Python status file), `data/logs/pipeline_progress.json` (live progress)
**Testing**: pytest (Python unit), ruff + black (Python linting), phpcs PSR-12 (PHP linting); PHP unit tests with PHPUnit for new `ServiceTester` and `JobStatusManager.updateJobStatus()`
**Target Platform**: Windows 11 (dev host), Linux (Docker containers)
**Project Type**: Multi-layer integration fix — DokuWiki plugin (PHP/JS) + Python HTTP service + Docker pipeline
**Performance Goals**: Stage start acknowledged < 2s; status poll 5s interval; progress poll 2s interval (unchanged)
**Constraints**: No `exec()`/`shell_exec()` in PHP (Article I); all cross-layer via HTTP; `pipeline/` untouched (ground truth)
**Scale/Scope**: Single admin user, 5 pipeline stages, max 1 concurrent job

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Article | Title                 | Status    | Notes                                                                                                                              |
| :------ | :-------------------- | :-------- | :--------------------------------------------------------------------------------------------------------------------------------- |
| I       | Layered Architecture  | PASS      | PHP calls HTTP only; no exec(); Docker CLI in Python only                                                                          |
| II      | JSON Interface        | PASS      | All HTTP endpoints return `application/json`; status file is JSON                                                                  |
| II-B    | Centralized Config    | PARTIAL   | `PLACEHOLDER_env.yaml` missing `preprocess` in `PIPELINE_ORCHESTRATION.stages` → planned fix (FR-010)                              |
| III     | Critical-Path Testing | ATTENTION | New `ServiceTester.php` and `JobStatusManager::updateJobStatus()` need PHPUnit tests; new `server.py` PIPELINE_STAGES needs pytest |
| IV      | Language Standards    | PASS      | ruff + black + PSR-12 enforced; declare(strict_types=1) on all new PHP files                                                       |
| V       | Documentation         | PASS      | No new modules; existing READMEs not affected; PHPDoc on all new/changed public methods                                            |
| VI      | Secret Containment    | PASS      | No changes to secret handling                                                                                                      |
| VII     | Simplicity Gate       | PASS      | No new abstraction layers; bugs fixed in-place; `ServiceTester` consolidates existing duplicate code                               |
| XIII    | DooD Deprecation      | N/A       | DooD removal explicitly out of scope                                                                                               |

**Gate result**: PASS (II-B partial violation is a known accepted state per constitution v1.4.0 and is fixed by this feature)

## Project Structure

### Documentation (this feature)

```text
specs/012-dokuwiki-pipeline-integration/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   ├── orchestrator_api.md       # HTTP API contract (PHP → Python)
│   └── pipeline_run_schema.md    # pipeline_runs.json field contract
└── tasks.md             # Phase 2 output (via /speckit.tasks)
```

### Source Code (touched files only)

```text
backend_services/orchestrator/
└── server.py                      # MODIFIED: merge STAGES+STAGE_DOCKER, RunRequest model,
                                   #   deploy pipeline_dir, compose env vars, sort fix, debug removal

dokuwiki_plugin/
├── lib/
│   ├── JobStatusManager.php       # MODIFIED: add updateJobStatus(), add preprocess to getStatusSummary()
│   ├── PipelineOrchestrator.php   # MODIFIED: forward options to API in runStage()
│   └── ServiceTester.php          # NEW: shared MCP + Qdrant test logic
├── action.php                     # MODIFIED: fix options format, use ServiceTester
├── admin.php                      # MODIFIED: use ServiceTester
└── dist/
    └── pipeline.js                # MODIFIED: fix { stage, options: { mode } } format

config/
└── PLACEHOLDER_env.yaml           # MODIFIED: add preprocess to PIPELINE_ORCHESTRATION.stages

tests/
└── unit/
    └── test_orchestrator_stages.py  # NEW: pytest — PIPELINE_STAGES structure, RunRequest, sort order
```

**Structure Decision**: Multi-layer (PHP plugin + Python service). No new directories. Changes are in-place fixes and one new PHP class.

## Complexity Tracking

| Violation                     | Why Needed                                                                                  | Simpler Alternative Rejected Because                                                    |
| :---------------------------- | :------------------------------------------------------------------------------------------ | :-------------------------------------------------------------------------------------- |
| `ServiceTester.php` new class | DRY: `testMcpServer()` + `testQdrant()` duplicated verbatim in `action.php` and `admin.php` | Leaving the duplication means any future fix must be made twice and bugs will resurface |
