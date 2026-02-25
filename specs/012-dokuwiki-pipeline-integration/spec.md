# Feature Specification: DokuWiki Pipeline Integration Fix

**Feature Branch**: `012-dokuwiki-pipeline-integration`
**Created**: 2026-02-23
**Status**: Draft
**Input**: Fix DokuWiki extension integration so the pipeline runs correctly from the extension and manually, eliminating bugs and inconsistencies across PHP plugin, JS dashboard, and Python orchestrator.

## Context

The dev_dito system has a 5-stage pipeline (Fetch, Evaluate, Preprocess, Embed, Deploy) that can be triggered either:
- **Manually**: via CLI commands in the repo
- **Via the DokuWiki admin extension**: via an admin dashboard that calls a Python orchestrator over HTTP

The DokuWiki extension (PHP + JS) and the Python orchestrator currently have multiple bugs and inconsistencies that prevent correct end-to-end operation from the extension. The pipeline itself (ground truth: `pipeline/` and `evaluation/`) is working correctly and must not be changed.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Admin runs a pipeline stage from DokuWiki (Priority: P1)

A wiki administrator opens the Dev Dito admin dashboard in DokuWiki, sees all 5 pipeline stages (Fetch, Evaluate, Preprocess, Embed, Deploy) with their current status, and can start any available stage with a single button click. The stage runs in the background, and the dashboard shows live progress until completion.

**Why this priority**: This is the core value of the entire DokuWiki extension — without it, the extension is non-functional as a pipeline trigger. Every other story depends on this working correctly.

**Independent Test**: Can be fully tested by starting the orchestrator, opening the admin dashboard, clicking "Starten" on the Fetch stage, and verifying the dashboard shows "Laeuft..." then updates to "Erfolgreich" after completion.

**Acceptance Scenarios**:

1. **Given** the orchestrator is running and the admin dashboard is open, **When** an admin clicks "Starten" on any stage, **Then** the stage starts, the button shows "Laeuft...", and progress updates appear within 5 seconds.
2. **Given** a stage is running, **When** the admin watches the dashboard, **Then** progress percentage, current step, and elapsed time update every 2 seconds without full page reload.
3. **Given** a stage completes successfully, **When** the dashboard refreshes, **Then** the stage card shows "Erfolgreich", the last-run timestamp, and stage-specific statistics.
4. **Given** a stage fails, **When** the dashboard refreshes, **Then** the stage card shows "Fehler" and a human-readable error message (max 200 characters).

---

### User Story 2 - Admin triggers incremental wiki fetch (Priority: P1)

A wiki administrator wants to re-fetch only pages that have changed since the last full fetch. The dashboard shows an "Incremental" button (enabled only when a previous fetch manifest exists) alongside the standard "Full Fetch" button. Clicking it starts the incremental fetch and the selected mode is correctly passed through to the pipeline.

**Why this priority**: Incremental fetch is the primary operational mode after initial setup — full fetch takes ~9 minutes, incremental seconds to minutes. Without mode forwarding working, every refresh triggers a full fetch.

**Independent Test**: Run a full fetch first (creates manifest), then click "Incremental" — verify only changed pages are processed by checking the output statistics.

**Acceptance Scenarios**:

1. **Given** no previous fetch manifest exists, **When** the admin views the Fetch stage card, **Then** the "Incremental" button is disabled.
2. **Given** a fetch manifest exists, **When** the admin clicks "Incremental", **Then** the orchestrator receives the `mode: incremental` option and the fetcher runs in incremental mode.
3. **Given** an incremental fetch completes, **When** the dashboard shows results, **Then** the statistics reflect only the pages that were updated (fewer than a full fetch).

---

### User Story 3 - Admin cancels a running pipeline job (Priority: P2)

A wiki administrator can cancel a pipeline stage that is currently running. After cancellation, the dashboard reflects the cancelled status, and a new stage can be started immediately without error.

**Why this priority**: Long-running stages (evaluate: up to 2 hours) need a cancel mechanism. Without a working cancel, a stuck stage blocks the entire pipeline indefinitely.

**Independent Test**: Start the evaluate stage, wait for it to show as running, click "Abbrechen" — verify status changes to "cancelled" and a new stage can be started.

**Acceptance Scenarios**:

1. **Given** a stage is running, **When** the admin clicks "Abbrechen" and confirms, **Then** the job is stopped and the status updates to "cancelled" within 10 seconds.
2. **Given** a job is cancelled, **When** the admin views the dashboard, **Then** no other stage is blocked and any stage can be started again.
3. **Given** the orchestrator is offline during cancel, **When** the admin clicks "Abbrechen", **Then** the job is marked as cancelled in the local status file and the dashboard reflects this.

---

### User Story 4 - Admin monitors service health from the dashboard (Priority: P2)

A wiki administrator can see the connection status of MCP Server and Qdrant in the service status section, and can trigger a manual connection test with a single click per service. The configuration section shows accurate values loaded from the central config.

**Why this priority**: Rapid diagnosis of connectivity issues without SSH access. The configuration display also confirms the correct setup is active.

**Independent Test**: With Qdrant running, open the admin page — the Qdrant indicator should turn green automatically on page load.

**Acceptance Scenarios**:

1. **Given** Qdrant is reachable, **When** the admin page loads, **Then** the Qdrant indicator shows green ("Connected") automatically.
2. **Given** an admin clicks "Test" next to any service, **Then** the indicator updates within 5 seconds showing connection result and latency.
3. **Given** the central config is loaded, **When** the configuration table is displayed, **Then** all values (Qdrant host/port, collection, fetcher timeout, embedding model) match the active `env.yaml`.

---

### User Story 5 - Admin runs pipeline manually via CLI (Priority: P1)

A developer or administrator can run each pipeline stage directly from the command line without the DokuWiki extension or orchestrator. All 5 stages produce the same output format and update the same status file regardless of whether they were triggered from the extension or CLI.

**Why this priority**: CLI execution is the development and fallback mode. The pipeline must be the single source of truth — the extension is just a trigger, not a requirement.

**Independent Test**: Run each stage's entry point (`run_preprocessing.py`, `run_embeddings.py`, `run_deploy.py qdrant`) directly and verify `data/logs/pipeline_runs.json` is updated with correct stage/status/stats fields.

**Acceptance Scenarios**:

1. **Given** all previous stages have run, **When** a developer runs any stage directly from CLI, **Then** the stage completes and writes a status entry to `pipeline_runs.json` with `stage`, `status`, `started_at`, `finished_at`, and `stats`.
2. **Given** a CLI-triggered run completes, **When** the DokuWiki dashboard polls for status, **Then** the completed stage is shown correctly in the dashboard with the same information.

---

### Edge Cases

- What happens when the orchestrator goes offline mid-run? The dashboard must show "orchestrator offline" and retain the last known status from the local status file.
- What happens when two admins try to start a stage simultaneously? The second request must be rejected with a clear "job already running" message.
- What happens when the status file is missing or corrupted? Each component must fall back gracefully (empty state, no crash).
- What happens when a pipeline container image does not exist? The orchestrator must report the error clearly in the job status.
- What happens when the deploy stage runs but `pipeline/05_deploy/` is not mounted? The container must fail with a clear error, not silently produce wrong results.

---

## Requirements *(mandatory)*

### Functional Requirements

**Pipeline Execution**

- **FR-001**: The system MUST forward the `mode` option (e.g., `full`, `incremental`) from the dashboard button click through the AJAX call, PHP layer, and HTTP API to the pipeline runner without loss.
- **FR-002**: The system MUST start the Deploy stage by invoking `run_deploy.py qdrant` from the `pipeline/05_deploy/` directory, not a separate entrypoint.
- **FR-003**: The system MUST pass stage-specific environment variables (output directory, token paths, API keys) to pipeline containers in both Docker-run mode and Docker Compose run mode.
- **FR-004**: The system MUST reject a stage start request with a clear error if another job is already running.

**Status & Progress**

- **FR-005**: The system MUST include the `preprocess` stage in all status summaries, status files, and dashboard displays alongside `fetch`, `evaluate`, `embed`, and `deploy`.
- **FR-006**: The system MUST use `started_at` as the canonical sort key when determining the most recent run for a stage, consistently across PHP and Python components.
- **FR-007**: The dashboard MUST poll for status every 5 seconds and for live progress every 2 seconds while a job is running.

**Cancel**

- **FR-008**: The system MUST update the job status to `cancelled` in `pipeline_runs.json` when a cancel request is received, even when the orchestrator is not reachable.
- **FR-009**: The PHP cancel fallback MUST write the cancellation to the status file without causing a runtime error.

**Configuration**

- **FR-010**: The `PIPELINE_ORCHESTRATION.stages` configuration section MUST include all 5 stages: `fetch`, `evaluate`, `preprocess`, `embed`, `deploy`.
- **FR-011**: The admin configuration display MUST show values that exactly match the active `settings.json`, with no hardcoded fallback values visible to the admin.

**Code Consistency**

- **FR-012**: Service connection testing logic (MCP, Qdrant) MUST exist in exactly one place in the PHP codebase, shared by both the admin page and AJAX handler.
- **FR-013**: Stage definitions (name, description, container, pipeline directory) MUST be defined in exactly one place in `server.py`, not in two separate dictionaries.
- **FR-014**: The Python orchestrator MUST NOT contain leftover debug logging code (agent log blocks, hypothesis IDs, session IDs).

### Key Entities

- **Pipeline Run**: Represents one execution of a stage. Fields: `job_id`, `stage`, `status`, `started_at`, `finished_at`, `duration_seconds`, `stats`, `error`. Written by Python pipeline; read by PHP extension and orchestrator.
- **Pipeline Stage**: One of 5 named steps (`fetch`, `evaluate`, `preprocess`, `embed`, `deploy`). Has a container name, pipeline directory, environment variables, and timeout.
- **Job Options**: Parameters passed with a stage start request. Currently: `mode` (`full` | `incremental`) for the fetch stage.
- **Orchestrator API**: HTTP service exposing `/status`, `/run/{stage}`, `/job/{job_id}`, `/progress`, `/cancel/{job_id}`. Bridge between PHP and Docker.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All 5 pipeline stages are visible and correctly reflect their last-run status in the DokuWiki admin dashboard after any run (CLI or extension-triggered).
- **SC-002**: An admin can start, monitor, and cancel any pipeline stage from the DokuWiki dashboard without SSH access or CLI interaction — zero steps outside the browser.
- **SC-003**: Incremental fetch mode is correctly activated when selected: the pipeline processes only changed pages, confirmed by output statistics showing fewer pages than a full fetch.
- **SC-004**: A stage started from the dashboard produces an identical `pipeline_runs.json` entry (same fields, same format) as the same stage started from CLI.
- **SC-005**: No PHP fatal error occurs during any dashboard operation (start, cancel, status poll, service test) under any orchestrator availability state (online, offline, mid-run).
- **SC-006**: All service connection tests (MCP, Qdrant) complete and return a result within 5 seconds.
- **SC-007**: The codebase contains zero duplicate service-testing implementations and zero duplicate stage-definition dictionaries after the changes.

---

## Assumptions

- The Python pipeline scripts (`pipeline/` directory) are correct and are not changed in this feature — they are ground truth.
- The `pipeline_runs.json` schema (defined by `data/logs/pipeline_runs.schema.json`) is the contract between Python and PHP — no schema changes are needed.
- The orchestrator runs on the host at port 18089; DokuWiki running in Docker accesses it via `host.docker.internal:18089`.
- The `config/settings.json` is generated from `config/env.yaml` by `config.py` and is placed at `dokuwiki_plugin/config/settings.json` as part of the deployment process. `ConfigLoader.php` path resolution is correct for the current dev setup; deployment documentation is sufficient.
- The 5 stage IDs (`fetch`, `evaluate`, `preprocess`, `embed`, `deploy`) are stable and will not change in this feature.

---

## Out of Scope

- DooD (Docker-outside-of-Docker) socket removal — deferred to post-thesis
- Multi-stage builds or non-root user security hardening in Dockerfiles
- Changes to pipeline Python scripts or evaluation framework
- New pipeline features or additional stages
- DokuWiki plugin UI redesign
