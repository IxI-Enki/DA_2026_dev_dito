# Quickstart: DokuWiki Pipeline Integration Fix

**Branch**: `012-dokuwiki-pipeline-integration`

This guide shows how to validate the integration end to end — both manually (CLI) and via the DokuWiki admin dashboard.

---

## Prerequisites

1. `config/env.yaml` exists (copy from `config/PLACEHOLDER_env.yaml` and fill values)
2. `config/settings.json` exists and is current (run `python config.py`)
3. Docker running, Qdrant up: `docker compose -p stack-g-devdito up qdrant -d`
4. Python venv active: `.venv\Scripts\Activate.ps1`
5. DokuWiki running in Docker (for dashboard tests): `docker compose -p stack-g-devdito --profile wiki up -d`

---

## Validate: Manual CLI execution

Run each stage directly and confirm `pipeline_runs.json` is updated.

```powershell
# Stage 01 - Fetch
python pipeline/01_wiki_fetcher/fetch_full_wiki_extended.py

# Confirm entry written
Get-Content data/logs/pipeline_runs.json | ConvertFrom-Json | Where-Object stage -eq "fetch" | Select-Object -Last 1

# Stage 03 - Preprocess (after fetch)
python pipeline/03_rag_preprocessing/run_preprocessing.py

# Stage 04 - Embed
python pipeline/04_embeddings_creator/run_embeddings.py --limit 5

# Stage 05 - Deploy
python pipeline/05_deploy/run_deploy.py qdrant --dry-run
```

**Expected**: Each command creates or updates an entry in `data/logs/pipeline_runs.json` with `stage`, `status: success`, `started_at`, `finished_at`, `stats`.

---

## Validate: Orchestrator (local host mode)

```powershell
# Start orchestrator on host
.venv\Scripts\Activate.ps1
python backend_services/orchestrator/server.py --port 18089

# In a second terminal — check health
Invoke-RestMethod http://localhost:18089/health

# Check status (should show all 5 stages)
Invoke-RestMethod http://localhost:18089/status | ConvertTo-Json -Depth 5

# Start fetch stage (full)
Invoke-RestMethod -Method POST http://localhost:18089/run/fetch `
  -ContentType "application/json" `
  -Body '{"options": {"mode": "full"}}'

# Start fetch stage (incremental — requires manifest)
Invoke-RestMethod -Method POST http://localhost:18089/run/fetch `
  -ContentType "application/json" `
  -Body '{"options": {"mode": "incremental"}}'

# Poll progress while running
Invoke-RestMethod http://localhost:18089/progress

# Cancel a running job
Invoke-RestMethod -Method POST http://localhost:18089/cancel/fetch_20260223_143000
```

---

## Validate: DokuWiki Admin Dashboard

1. Open DokuWiki → Admin → "Dev Dito Core Setup"
2. Verify **all 5 stages** appear: Fetch, Evaluate, Preprocess, Embed, Deploy
3. Verify Qdrant status shows green (service running)
4. Click **"Full Fetch"** — dashboard should show "Laeuft..." within 2s
5. Watch progress bar update every 2s
6. After completion — stage card shows "Erfolgreich" + stats
7. If a manifest exists — "Incremental" button is enabled; click it and verify only changed pages processed
8. Start any stage → click "Abbrechen" → confirm status shows "cancelled"

---

## Run Tests

```powershell
# Python unit tests (orchestrator)
pytest tests/unit/test_orchestrator_stages.py -v

# All tests
pytest tests/ -v --tb=short

# Linting
ruff check .
black --check .

# PHP linting (if phpcs installed)
vendor/bin/phpcs --standard=PSR12 dokuwiki_plugin/
```

---

## Troubleshooting

| Symptom | Likely Cause | Fix |
| :------ | :----------- | :-- |
| Dashboard shows only 4 stages (no Preprocess) | `JobStatusManager::getStatusSummary()` not updated | Check Bug 3 fix |
| Incremental button does nothing | JS options format incorrect | Check Bug 2 fix |
| Cancel button causes PHP error | `updateJobStatus()` missing | Check Bug 1 fix |
| Deploy stage fails silently | `pipeline_dir` not mounted | Check Bug 4 fix |
| Dashboard stage cards show stale data after CLI run | Sort key mismatch | Check Bug 7 fix |
