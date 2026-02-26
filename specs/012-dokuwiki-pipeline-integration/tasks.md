---
description: "Task list for 012-dokuwiki-pipeline-integration"
---

# Tasks: DokuWiki Pipeline Integration Fix

**Input**: `specs/012-dokuwiki-pipeline-integration/` — plan.md, spec.md, data-model.md, contracts/, research.md, quickstart.md
**Prerequisites**: Phase 2 (Foundational) MUST be complete before any User Story phase begins.
**Tests**: PHPUnit tasks included for ServiceTester (HTTP client code) and JobStatusManager.updateJobStatus() per Constitution Article III. Pytest task included for PIPELINE_STAGES structure and FR-004 concurrent rejection.
**Remediation applied**: C1 PHPUnit tasks added, C2 FR-004 test added, C3 cancel wiring task added, H1 FR-011 task added, H3 spec.md corrected, M1 T002 split into 3 tasks, M2/L3 pipeline.js note added, M3 config.py regen step added, M4 T006 "verify" replaced with concrete criterion, L1 stale line refs removed, L2 CI note added.

## Format: `[ID] [P?] [Story?] Description with file path`

- **[P]**: parallelizable (different files, no blocking dependency)
- **[Story]**: user story label — US1 through US5 mapping to spec.md stories

---

## Phase 1: Setup

**Purpose**: Create the new test file scaffolds before making any logic changes.

- [X] T001 Create `tests/unit/test_orchestrator_stages.py` as an empty pytest module with module docstring and imports (`import pytest`, path-based import of `backend_services/orchestrator/server`) — scaffold only; tests filled in T010 and T008
- [X] T002 [P] Create `tests/php/ServiceTesterTest.php` as an empty PHPUnit test class (`class ServiceTesterTest extends TestCase`) with namespace and `require_once` scaffold — tests filled in T018 (Constitution Article III: HTTP client code requires tests)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Restructure `server.py` as the single source of truth for stage definitions. All user stories depend on this. T003 → T004 → T005 are sequential (same file); T006 and T007 are sequential after T005; T008 is parallel to T003-T007.

**CRITICAL**: Complete T003 → T004 → T005 → T006 → T007 in order before any User Story phase begins.

- [X] T003 Merge the `STAGES` dict and the `STAGE_DOCKER` dict into a single `PIPELINE_STAGES: dict[str, dict]` at module top in `backend_services/orchestrator/server.py` — include all 5 stages (`fetch`, `evaluate`, `preprocess`, `embed`, `deploy`) each with keys: `name`, `description`, `container`, `pipeline_dir`, `extra_env`, `needs_openai_key`; update all route handlers (`/status`, `/run/{stage}`, `/job/{job_id}`) to reference `PIPELINE_STAGES` only; delete the original `STAGES` and `STAGE_DOCKER` dicts (FR-013)

- [X] T004 Fix sort key in `get_last_run()` in `backend_services/orchestrator/server.py`: change sort from `updated_at` to `started_at`; confirm the function returns the run with the latest `started_at` for a given stage (FR-006)

- [X] T005 Remove all debug/agent logging blocks from `backend_services/orchestrator/server.py` — search for agent log blocks, hypothesis IDs, session ID logging, and any `print`/`logger` calls not part of standard request logging; leave only FastAPI request log lines (FR-014)

- [X] T006 Add `RunRequest(BaseModel)` with `options: dict[str, str] = {}` to `backend_services/orchestrator/server.py`; update `POST /run/{stage}` signature to `async def run_stage(stage: str, request: RunRequest = Body(default=RunRequest()))`; propagate `request.options` into `_build_docker_run` and `_build_compose_run` so a `mode: incremental` option becomes `FETCH_MODE=incremental` env var on the container (FR-001)

- [X] T007 In `backend_services/orchestrator/server.py` PIPELINE_STAGES deploy entry: set `pipeline_dir` to `"05_deploy"` and add `entrypoint_args: ["python", "run_deploy.py", "qdrant", "--job-id"]`; update `_build_docker_run` and `_build_compose_run` to append `entrypoint_args + [job_id]` when `entrypoint_args` key is present, else append `[job_id]` as default; add `extra_env` iteration loop to `_build_compose_run` (mirrors existing `_build_docker_run` logic) (FR-002, FR-003)

- [X] T008 [P] Add `preprocess` stage block to the `PIPELINE_ORCHESTRATION.stages` section in `config/PLACEHOLDER_env.yaml` — match the format of existing `fetch`, `evaluate`, `embed`, `deploy` entries (`container`, `timeout`, `description` keys); after editing, run `python config.py` from repo root to regenerate `config/settings.json` and confirm `preprocess` appears in the output (FR-010; M3 fix: settings.json must be regenerated)

**Checkpoint**: `PIPELINE_STAGES` in server.py has exactly 5 entries, `RunRequest` model exists, deploy uses `run_deploy.py qdrant`, compose-run passes extra_env, `PLACEHOLDER_env.yaml` + `settings.json` both have preprocess. ✓

---

## Phase 3: User Stories 1 + 5 — Core Stage Execution (Priority: P1) MVP

**Goal (US1)**: Admin opens dashboard and sees all 5 stages with correct status.
**Goal (US5)**: CLI-run stages produce pipeline_runs.json entries that the dashboard reads correctly.

**Independent Test**:
- US1: Start orchestrator → `GET /status` → JSON contains 5 stage objects including `preprocess`
- US5: Run `python pipeline/01_wiki_fetcher/...` → `data/logs/pipeline_runs.json` contains a new entry visible in dashboard

- [X] T009 [US1] Add `"preprocess"` to the ordered stage list in `JobStatusManager::getStatusSummary()` in `dokuwiki_plugin/lib/JobStatusManager.php` — position it between `evaluate` and `embed`; confirm that `getLastRun("preprocess")` returns `null` when no preprocess runs exist (by reading the `getAllRuns()` + stage-filter pattern) and returns the most recent run object when one exists (M4 fix: concrete criterion replaces vague "verify") (FR-005)

- [X] T010 [P] [US5] Implement pytest tests in `tests/unit/test_orchestrator_stages.py`: (a) assert `PIPELINE_STAGES` has exactly 5 keys in order: `fetch`, `evaluate`, `preprocess`, `embed`, `deploy`; (b) assert each entry contains `name`, `container`, `pipeline_dir` keys; (c) assert `get_last_run` picks the entry with the largest `started_at` value, not `updated_at` — test with two mock runs where `updated_at` and `started_at` order differ; (d) assert `RunRequest()` defaults to `options == {}`; (e) assert `deploy` entry has `entrypoint_args` key; (f) assert `POST /run/{stage}` returns 409 when `_active_job` is already set — mock the active job state to test FR-004 concurrent rejection (C2 fix: FR-004 coverage added here)

**Checkpoint**: `pytest tests/unit/test_orchestrator_stages.py` passes. Dashboard shows 5 stages. CLI runs appear in dashboard. ✓

---

## Phase 4: User Story 2 — Incremental Fetch Options (Priority: P1)

**Goal**: `mode: incremental` flows from dashboard button → JS → PHP → HTTP → container env var without loss.

**Independent Test**: Full fetch first (creates manifest) → click Incremental → orchestrator log shows `FETCH_MODE=incremental` passed to container.

- [X] T011 [US2] Fix `runStage()` in `dokuwiki_plugin/dist/pipeline.js` to send `{ stage: stageId, options: { mode: selectedMode } }` instead of the current flat `{ stage: stageId, mode: selectedMode }` — the `options` dict is forwarded generically so future stages can use it without further JS changes; `fetch` is the only stage with options in v0.12.0; do NOT change the polling interval constants (`STATUS_POLL_INTERVAL`, `PROGRESS_POLL_INTERVAL`) — they must remain 5000ms and 2000ms respectively (M2 fix: poll intervals protected; L3 fix: fetch-only scope noted) (FR-001, FR-007)

- [X] T012 [US2] Fix options extraction in `dokuwiki_plugin/action.php`: read `$data['options'] ?? []` (not a flat `$data['mode']` key); pass the options array to `PipelineOrchestrator::runStage()` — confirm no option keys are dropped and existing calls without options still work

- [X] T013 [US2] Update `PipelineOrchestrator::runStage(string $stage, array $options = [])` in `dokuwiki_plugin/lib/PipelineOrchestrator.php` to include `['options' => $options]` in the `callOrchestratorApi('POST', "/run/$stage", ...)` body payload; add PHPDoc `@param array $options` to the method signature (FR-001)

**Checkpoint**: `POST /run/fetch` with `{"options": {"mode": "incremental"}}` → container receives `FETCH_MODE=incremental`. ✓

---

## Phase 5: User Story 3 — Cancel Running Job (Priority: P2)

**Goal**: Admin cancels a running stage from the dashboard; status updates to `cancelled` even when orchestrator is offline.

**Independent Test**: Start evaluate stage → wait for `running` → click Abbrechen → `pipeline_runs.json` shows `status: cancelled` within 10s.

- [X] T014 [US3] Add `private function writeRuns(array $runs): void` and `public function updateJobStatus(string $jobId, array $updates): void` to `dokuwiki_plugin/lib/JobStatusManager.php` — `writeRuns` uses `fopen($this->statusFile, 'w')` + `LOCK_EX` + `json_encode($runs, JSON_PRETTY_PRINT)` + `fclose`; `updateJobStatus` reads via `getAllRuns()`, iterates to find matching `job_id`, applies only whitelisted keys (`status`, `finished_at`, `error`), silently ignores all other keys (`job_id`, `stage`, `started_at`, `stats`, `output_dir`), invalidates `$this->cachedRuns = null` after write; add PHPDoc for both methods (FR-008, FR-009)

- [X] T015 [US3] Wire the cancel fallback in `dokuwiki_plugin/lib/PipelineOrchestrator.php`: add `public function cancelJob(string $jobId): array` — first attempt `callOrchestratorApi('POST', "/cancel/$jobId")`; if the call returns `null` (orchestrator unreachable), instantiate `JobStatusManager` and call `updateJobStatus($jobId, ['status' => 'cancelled', 'finished_at' => date('c'), 'error' => 'Manuell abgebrochen'])`, return `['success' => true, 'fallback' => true]`; update `dokuwiki_plugin/action.php` AJAX routing to call `$orchestrator->cancelJob($jobId)` for cancel actions (C3 fix: cancel calling chain wired) (FR-008, FR-009)

- [X] T016 [P] [US3] Implement PHPUnit tests in `tests/php/JobStatusManagerTest.php` (create file): test `updateJobStatus()` (a) updates `status`, `finished_at`, `error` correctly; (b) does NOT overwrite `job_id`, `stage`, `started_at`, `stats`; (c) uses file locking (mock or verify `LOCK_EX` is passed); test `writeRuns()` produces valid JSON parseable by `json_decode` (Constitution Article III: critical-path logic; C1 fix)

**Checkpoint**: Cancel button → `pipeline_runs.json` updated to `cancelled` — with or without orchestrator running. ✓

---

## Phase 6: User Story 4 — Service Health Monitoring (Priority: P2)

**Goal**: MCP and Qdrant testing logic in exactly one PHP file; admin dashboard config display matches settings.json.

**Independent Test**: Qdrant running → admin page loads → Qdrant indicator green; click "Test" MCP → result within 5s; config table values match active `settings.json`.

- [X] T017 [US4] Create `dokuwiki_plugin/lib/ServiceTester.php` — `declare(strict_types=1)`, `class ServiceTester`, two `public static` methods: `testMcp(string $url, int $timeout = 5): array` and `testQdrant(string $host, int $port, int $timeout = 5): array` — each returns `['success' => bool, 'latency_ms' => int, 'error' => string|null]`; extract existing inline logic verbatim from `action.php`; add PHPDoc blocks on both methods; file must pass `phpcs --standard=PSR12` (FR-012)

- [X] T018 [P] [US4] Implement PHPUnit tests in `tests/php/ServiceTesterTest.php`: test `testMcp()` (a) returns `success: true` and positive `latency_ms` when server responds with 200; (b) returns `success: false` and non-null `error` on connection refused — use a mock HTTP server or skip with `@group integration`; test `testQdrant()` (a) returns `success: true` for reachable host/port; (b) returns `success: false` for unreachable port; assert return shape contains exactly `success`, `latency_ms`, `error` keys (Constitution Article III: HTTP client code; C1 fix)

- [X] T019 [P] [US4] Replace inline `testMcpServer` / `testQdrant` logic in `dokuwiki_plugin/action.php` with `require_once __DIR__ . '/lib/ServiceTester.php'` and calls to `ServiceTester::testMcp(...)` / `ServiceTester::testQdrant(...)` — delete the now-duplicate inline functions (FR-012)

- [X] T020 [P] [US4] Replace inline `testMcpServer` / `testQdrant` logic in `dokuwiki_plugin/admin.php` with the same `require_once` and `ServiceTester::testMcp(...)` / `ServiceTester::testQdrant(...)` calls — delete the now-duplicate inline functions (FR-012)

- [X] T021 [US4] Audit the configuration display section in `dokuwiki_plugin/admin.php`: for each displayed config value (Qdrant host/port, collection name, fetcher timeout, embedding model), confirm the value is read from `ConfigLoader::get(...)` or equivalent, not a hardcoded string literal; replace any hardcoded fallback strings with `ConfigLoader` calls or an explicit `"[not configured]"` sentinel; add a comment marking each config read location (FR-011; H1 fix)

**Checkpoint**: `grep -r "function testMcp\|function testQdrant" dokuwiki_plugin/` returns exactly 2 hits in `ServiceTester.php`. Admin config table shows no hardcoded values. ✓

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Linting, formatting, and end-to-end validation.

- [X] T022 [P] Run `ruff check .` and `black --check .` on all Python files from repo root; fix any violations introduced by T003-T007 and T010 — ensure all new functions have type hints (Constitution Article IV)

- [X] T023 [P] Run `phpcs --standard=PSR12 dokuwiki_plugin/` and fix violations in: `ServiceTester.php`, `JobStatusManager.php`, `PipelineOrchestrator.php`, `action.php`, `admin.php`, `tests/php/ServiceTesterTest.php`, `tests/php/JobStatusManagerTest.php` (Constitution Article IV)

- [X] T024 Run end-to-end validation per `specs/012-dokuwiki-pipeline-integration/quickstart.md` — CLI execution of each stage, orchestrator health/status check, dashboard smoke test; confirm SC-001 through SC-007 pass; record results in PR description (manual only — no CI automation; automated coverage provided by T010 pytest and T016/T018 PHPUnit) (L2 fix: CI limitation noted)

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (T001 || T002)
  ↓
Phase 2 (T003 → T004 → T005 → T006 → T007) || (T008)
  ↓
Phase 3 (T009 || T010) — US1+US5 MVP
  ↓
Phase 4 (T011 → T012 → T013) — US2
  ↓
Phase 5 (T014 → T015) || (T016) — US3
  ↓
Phase 6 (T017 → T018 || T019 || T020 → T021) — US4
  ↓
Phase 7 (T022 || T023 → T024)
```

### Within Phases — Sequential Constraints

| Constraint | Reason |
| :--------- | :----- |
| T003 → T004 → T005 → T006 → T007 | Same file (server.py); each builds on previous |
| T008 \|\| T003-T007 | Different file (PLACEHOLDER_env.yaml); fully parallel |
| T014 → T015 | T015 calls `updateJobStatus()` added in T014 |
| T017 → T018 | T018 tests the class created in T017 |
| T017 → T019, T017 → T020 | T019/T020 require ServiceTester.php to exist |
| T019 \|\| T020 | Different files; fully parallel |

### User Story Dependencies

| Story | Priority | Can Start After | Notes |
| :---- | :------- | :-------------- | :---- |
| US1 + US5 | P1 | T007 done | Foundation complete |
| US2 | P1 | T007 done | RunRequest (T006) required |
| US3 | P2 | T007 done | No dependency on US1/US2 |
| US4 | P2 | T007 done | No dependency on US1-US3 |

---

## Parallel Opportunities

```text
# Phase 1:
T001  (test_orchestrator_stages.py scaffold)
T002  (ServiceTesterTest.php scaffold)

# Phase 2:
T003 → T004 → T005 → T006 → T007  (server.py, sequential)
T008                               (PLACEHOLDER_env.yaml, parallel)

# Phase 3:
T009  (JobStatusManager.php)
T010  (test_orchestrator_stages.py)

# Phase 5 (US3):
T014 → T015  (JobStatusManager + PipelineOrchestrator, sequential)
T016         (JobStatusManagerTest.php, parallel)

# Phase 6 (US4):
T017  (ServiceTester.php — must finish first)
  → T018  (ServiceTesterTest.php)
  → T019  (action.php)        ← these three can run in parallel
  → T020  (admin.php)
T021  (admin.php config audit — after T020)

# Phase 7:
T022  (Python linting)
T023  (PHP linting)
```

---

## Implementation Strategy

### MVP (User Stories 1 + 5 only)

1. Complete Phase 1: T001, T002
2. Complete Phase 2: T003 → T004 → T005 → T006 → T007 (+ T008 in parallel)
3. Complete Phase 3: T009 + T010
4. **STOP and VALIDATE**: `pytest tests/unit/test_orchestrator_stages.py` passes; `GET /status` shows 5 stages; dashboard displays preprocess
5. Demo: CLI run appears in dashboard

### Incremental Delivery

| Step | Phase(s) | Delivers | Validates |
| :--- | :------- | :------- | :-------- |
| 1 | 1 + 2 | Foundation | Orchestrator starts, 5-stage PIPELINE_STAGES |
| 2 | 3 | US1+US5 MVP | Dashboard shows 5 stages, CLI runs visible |
| 3 | 4 | US2 | Incremental fetch mode forwarded end-to-end |
| 4 | 5 | US3 | Cancel works with offline orchestrator |
| 5 | 6 | US4 | ServiceTester DRY, health indicators, config display correct |
| 6 | 7 | Polish | All linting passes, quickstart.md validated |

---

## Task Summary

| Phase | Tasks | User Story | Files Changed |
| :---- | :---- | :--------- | :------------ |
| 1 Setup | T001–T002 | — | tests/unit/test_orchestrator_stages.py, tests/php/ServiceTesterTest.php |
| 2 Foundational | T003–T008 | — | server.py (×5 sequential), PLACEHOLDER_env.yaml |
| 3 US1+US5 | T009–T010 | US1, US5 | JobStatusManager.php, test_orchestrator_stages.py |
| 4 US2 | T011–T013 | US2 | pipeline.js, action.php, PipelineOrchestrator.php |
| 5 US3 | T014–T016 | US3 | JobStatusManager.php, PipelineOrchestrator.php, action.php, JobStatusManagerTest.php |
| 6 US4 | T017–T021 | US4 | ServiceTester.php (NEW), ServiceTesterTest.php, action.php, admin.php (×2) |
| 7 Polish | T022–T024 | — | all modified files |
| **Total** | **24 tasks** | **5 stories** | **9 files (2 new PHP classes)** |
