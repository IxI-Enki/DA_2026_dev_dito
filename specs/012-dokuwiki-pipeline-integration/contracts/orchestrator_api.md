# Contract: Orchestrator HTTP API

**Version**: 0.3.0 (post-fix)
**Consumer**: `dokuwiki_plugin/lib/PipelineOrchestrator.php`
**Provider**: `backend_services/orchestrator/server.py`
**Transport**: HTTP/1.1, JSON body, port 18089 (host) / 8089 (container)

---

## GET /health

Returns service health. No auth required.

**Response 200**:
```json
{ "status": "ok", "service": "pipeline-orchestrator" }
```

---

## GET /status

Returns status of all 5 pipeline stages and the currently active job (if any).

**Response 200**:
```json
{
  "stages": [
    {
      "id": "fetch",
      "name": "Wiki Fetcher",
      "description": "Fetcht Wiki-Inhalte via JSON-RPC API",
      "status": "success | error | running | never_run | cancelled",
      "last_run": "2026-02-23T14:30:00 | null",
      "duration_seconds": 574,
      "stats": { "pages": 207, "media": 325 },
      "has_manifest": true
    },
    { "id": "evaluate", ... },
    { "id": "preprocess", ... },
    { "id": "embed", ... },
    { "id": "deploy", ... }
  ],
  "active_job": null
}
```

**Note**: `stages` array MUST contain exactly 5 entries in execution order: fetch, evaluate, preprocess, embed, deploy.

---

## POST /run/{stage}

Starts a pipeline stage. `stage` must be one of: `fetch`, `evaluate`, `preprocess`, `embed`, `deploy`.

**Request body** (all fields optional):
```json
{ "options": { "mode": "full | incremental" } }
```

**Response 200** (success):
```json
{ "success": true, "job_id": "fetch_20260223_143000", "message": "Wiki Fetcher gestartet", "stage": "fetch" }
```

**Response 400** (unknown stage):
```json
{ "detail": "Unknown stage: xyz" }
```

**Response 409** (job already running):
```json
{ "detail": "Job already running: fetch_20260223_143000" }
```

**Response 500** (execution error):
```json
{ "detail": "Container exit code 1: ..." }
```

---

## GET /job/{job_id}

Returns the full pipeline run record for a specific job.

**Response 200**: Pipeline Run object (see data-model.md Entity 1)

**Response 404**:
```json
{ "detail": "Job not found: xyz" }
```

---

## GET /progress

Returns live progress for the currently running job.

**Response 200** (job running):
```json
{
  "job_id": "fetch_20260223_143000",
  "stage": "fetch",
  "status": "running",
  "started_at": "2026-02-23T14:30:00",
  "current_step": "Fetching pages...",
  "progress": { "current": 42, "total": 207, "percentage": 20 },
  "message": "42 / 207 pages fetched",
  "substeps": [],
  "errors": []
}
```

**Response 200** (no active job):
```json
{ "status": "no_progress", "message": "No progress file found" }
```

---

## GET /progress/{job_id}

Returns progress for a specific job ID. If that job is not the current one, returns last known status.

---

## POST /cancel/{job_id}

Attempts to stop a running job. Best-effort (sends `docker stop`).

**Response 200**:
```json
{ "success": true, "message": "Job fetch_20260223_143000 cancelled" }
```

**Response 404**: Job not found.
**Response 400**: Job is not running.

---

## PHP Fallback Behavior (orchestrator offline)

When `callOrchestratorApi()` returns `null` (connection refused):

| Operation | Fallback |
| :-------- | :------- |
| `getStatus()` | Read from `pipeline_runs.json` via `JobStatusManager` |
| `runStage()` | Return error: "Orchestrator nicht erreichbar" |
| `getJobStatus()` | Read from `pipeline_runs.json` |
| `getProgress()` | Return `{ status: orchestrator_offline }` |
| `cancelJob()` | Write `status: cancelled` to `pipeline_runs.json` directly |
