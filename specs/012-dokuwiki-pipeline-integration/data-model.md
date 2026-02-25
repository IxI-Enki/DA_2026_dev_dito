# Data Model: DokuWiki Pipeline Integration Fix

**Branch**: `012-dokuwiki-pipeline-integration`
**Input**: Entities from spec.md + existing `data/logs/pipeline_runs.schema.json`

---

## Entity 1: Pipeline Run (canonical — written by Python, read by PHP)

Represents one execution of a pipeline stage. Written to `data/logs/pipeline_runs.json` (array of runs).

| Field              | Type     | Required | Description                                                      |
| :----------------- | :------- | :------- | :--------------------------------------------------------------- |
| `job_id`           | string   | yes      | Format: `{stage}_{YYYYMMDD_HHMMSS}` e.g. `fetch_20260223_143000` |
| `stage`            | enum     | yes      | One of: `fetch`, `evaluate`, `preprocess`, `embed`, `deploy`     |
| `status`           | enum     | yes      | One of: `running`, `success`, `error`, `cancelled`               |
| `started_at`       | ISO 8601 | yes      | Set at job creation, immutable. Canonical sort key.              |
| `updated_at`       | ISO 8601 | yes      | Updated on every status change                                   |
| `finished_at`      | ISO 8601 | no       | Set when status is `success`, `error`, or `cancelled`            |
| `duration_seconds` | number   | no       | Elapsed seconds from start to finish                             |
| `stats`            | object   | no       | Stage-specific output statistics (see below)                     |
| `error`            | string   | no       | Human-readable error message (max 500 chars)                     |
| `output_dir`       | string   | no       | Absolute path to stage output directory                          |

**Stage-specific `stats` shapes**:

| Stage        | Stats Fields                                                                                    |
| :----------- | :---------------------------------------------------------------------------------------------- |
| `fetch`      | `pages`, `media`                                                                                |
| `evaluate`   | `pages_evaluated`, `overall_quality`, `pages_to_include`, `pages_to_exclude`, `pages_to_review` |
| `preprocess` | `documents_processed`, `pages_converted`, `media_extracted`, `total_output_files`               |
| `embed`      | `chunks`, `vectors`, `dimensions`, `cost_usd`, `model`                                          |
| `deploy`     | `uploaded`, `collection`                                                                        |

**State transitions**:
```
(created) → running → success
                    → error
                    → cancelled
```

**Invariant**: `started_at` is immutable after creation. Any PHP write via `updateJobStatus()` MUST NOT overwrite `started_at`.

---

## Entity 2: Pipeline Stage Definition (server.py `PIPELINE_STAGES`)

Defines execution parameters per stage. Lives in `server.py` only (single source of truth after this fix).

| Field              | Type          | Description                                                       |
| :----------------- | :------------ | :---------------------------------------------------------------- |
| `name`             | string        | Display name (e.g., "Wiki Fetcher")                               |
| `description`      | string        | Short German description for dashboard                            |
| `container`        | string        | Docker service name (e.g., `module_fetcher`)                      |
| `pipeline_dir`     | string?       | Relative dir under `pipeline/` to mount (e.g., `01_wiki_fetcher`) |
| `extra_env`        | dict[str,str] | Extra env vars passed to container                                |
| `needs_openai_key` | bool          | Whether to inject OPENAI_API_KEY                                  |
| `entrypoint_args`  | list[str]?    | Override CMD; if absent, `[job_id]` is appended                   |

**All 5 stages after fix**:

| Stage ID     | container             | pipeline_dir            | entrypoint_args                                             |
| :----------- | :-------------------- | :---------------------- | :---------------------------------------------------------- |
| `fetch`      | `module_fetcher`      | `01_wiki_fetcher`       | `[job_id]` (default)                                        |
| `evaluate`   | `module_evaluator`    | `02_deep_evaluation`    | `[job_id]` (default)                                        |
| `preprocess` | `module_preprocessor` | `03_rag_preprocessing`  | `[job_id]` (default)                                        |
| `embed`      | `module_embedder`     | `04_embeddings_creator` | `[job_id]` (default)                                        |
| `deploy`     | `module_deployer`     | `05_deploy`             | `["python", "run_deploy.py", "qdrant", "--job-id", job_id]` |

---

## Entity 3: Job Options

Parameters forwarded from dashboard button click through to the pipeline container.

| Field  | Type | Required | Description                                |
| :----- | :--- | :------- | :----------------------------------------- |
| `mode` | enum | no       | `full` or `incremental` (fetch stage only) |

**Transport path** (after fix):
```
pipeline.js  { stage, options: { mode } }
  → action.php  $data['options']
    → PipelineOrchestrator.php  runStage($stage, $options)
      → server.py POST /run/{stage}  RunRequest(options={mode: ...})
        → _build_docker_run  env var FETCH_MODE=incremental
```

---

## Entity 4: Orchestrator API Response Shapes

### GET /status response
```json
{
  "stages": [
    {
      "id": "fetch",
      "name": "Wiki Fetcher",
      "description": "...",
      "status": "success",
      "last_run": "2026-02-23T14:30:00",
      "duration_seconds": 574,
      "stats": { "pages": 207, "media": 325 },
      "has_manifest": true
    }
  ],
  "active_job": null
}
```

### POST /run/{stage} request body (after fix)
```json
{ "options": { "mode": "incremental" } }
```

### POST /run/{stage} response
```json
{ "success": true, "job_id": "fetch_20260223_143000", "message": "Wiki Fetcher gestartet", "stage": "fetch" }
```

### GET /progress response
```json
{
  "job_id": "fetch_20260223_143000",
  "stage": "fetch",
  "status": "running",
  "started_at": "2026-02-23T14:30:00",
  "current_step": "Fetching pages...",
  "progress": { "current": 42, "total": 207, "percentage": 20 },
  "message": "42 / 207 pages",
  "substeps": [],
  "errors": []
}
```
