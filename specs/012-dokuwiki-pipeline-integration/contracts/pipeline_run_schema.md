# Contract: pipeline_runs.json Schema

**File**: `data/logs/pipeline_runs.json`
**Writers**: Python pipeline entrypoints + `server.py` (status updates) + `JobStatusManager.php` (cancel fallback only)
**Readers**: `server.py` (all endpoints), `JobStatusManager.php` (status display)

---

## Format

Top-level array of Pipeline Run objects, max 100 entries (oldest trimmed).

```json
[
  {
    "job_id": "fetch_20260223_143000",
    "stage": "fetch",
    "status": "success",
    "started_at": "2026-02-23T14:30:00.000000",
    "updated_at": "2026-02-23T14:39:34.000000",
    "finished_at": "2026-02-23T14:39:34.000000",
    "duration_seconds": 574,
    "stats": { "pages": 207, "media": 325 },
    "output_dir": "/data/fetched/fetched_at_20260223_143000",
    "error": null
  }
]
```

---

## Field Contracts

| Field | Writer | Read by PHP? | Invariant |
| :---- | :----- | :----------- | :-------- |
| `job_id` | Python / server.py | yes | Immutable after creation. Format: `{stage}_{YYYYMMDD_HHMMSS}` |
| `stage` | Python / server.py | yes | Immutable. One of 5 stage IDs |
| `status` | Python / server.py / PHP (cancel only) | yes | Mutable. Enum: `running`, `success`, `error`, `cancelled` |
| `started_at` | server.py at job creation | yes | **Immutable**. ISO 8601. Canonical sort key for "last run" |
| `updated_at` | server.py on every change | no | Mutable. Updated by Python only |
| `finished_at` | Python entrypoint | yes | Set when terminal status reached |
| `duration_seconds` | Python entrypoint | yes | Computed at finish |
| `stats` | Python entrypoint | yes | Stage-specific object |
| `output_dir` | Python entrypoint | yes | Absolute path string |
| `error` | Python / server.py | yes | String or null |

---

## PHP Write Rules (cancel fallback)

`JobStatusManager::updateJobStatus()` MAY only write:
- `status` → `"cancelled"`
- `finished_at` → current ISO timestamp
- `error` → `"Manuell abgebrochen"`

It MUST NOT write: `job_id`, `stage`, `started_at`, `stats`, `output_dir`.

It MUST use `LOCK_EX` file locking to avoid race conditions with Python writers.

---

## Sort Key Rule

Both Python (`server.py::get_last_run`) and PHP (`JobStatusManager::getLastRun`) sort by `started_at` descending to find the most recent run for a stage. This is the canonical rule after this fix.
