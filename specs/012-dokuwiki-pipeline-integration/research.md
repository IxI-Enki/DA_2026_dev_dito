# Research: DokuWiki Pipeline Integration Fix

**Branch**: `012-dokuwiki-pipeline-integration`
**Input**: Technical context unknowns from plan.md Phase 0

---

## R-001: Unified Stage Dictionary in server.py

**Question**: How to merge `STAGES` (Zeile 280) and `STAGE_DOCKER` (Zeile 108) into a single dict without breaking the existing FastAPI route logic?

**Decision**: Replace both with a single `PIPELINE_STAGES` dict at module level. Each entry contains all keys previously split across both dicts.

**Structure**:
```python
PIPELINE_STAGES: dict[str, dict] = {
    "fetch": {
        "name": "Wiki Fetcher",
        "container": "module_fetcher",
        "description": "Fetcht Wiki-Inhalte via JSON-RPC API",
        "pipeline_dir": "01_wiki_fetcher",
        "extra_env": {
            "OUTPUT_DIR": "/data/fetched",
            "TOKEN_PATH": "/config/secrets/json_rpc_api.token",
            "SSL_CERT_PATH": "/config/secrets/ssl.cert",
        },
    },
    "evaluate": { ... },
    "preprocess": { ... },
    "embed": { ... "needs_openai_key": True },
    "deploy": {
        "pipeline_dir": "05_deploy",
        "entrypoint_args": ["python", "run_deploy.py", "qdrant"],
        ...
    },
}
```

**Rationale**: Single source of truth. All references to `STAGES[s]` and `STAGE_DOCKER.get(s)` become `PIPELINE_STAGES[s]`. Eliminates manual sync requirement.

**Alternatives considered**: Keep two dicts and add a sync assertion test — rejected because it adds test complexity without reducing the root cause.

---

## R-002: RunRequest Pydantic Model and Options Forwarding

**Question**: How should the `/run/{stage}` FastAPI endpoint accept options (e.g., `mode: incremental`) from PHP?

**Decision**: Add a Pydantic `RunRequest` model with an optional `options` dict. Pass relevant options as env vars to the container.

```python
class RunRequest(BaseModel):
    options: dict[str, str] = {}

@app.post("/run/{stage}")
async def run_stage(stage: str, request: RunRequest = Body(default=RunRequest())):
    ...
    if stage == "fetch" and request.options.get("mode") == "incremental":
        extra_env["FETCH_MODE"] = "incremental"
```

**PHP side** — `PipelineOrchestrator.php::runStage()` sends:
```php
$this->callOrchestratorApi('POST', "/run/$stage", ['options' => $options]);
```

**JS side** — `pipeline.js::runStage()` sends:
```js
{ stage: stageId, options: { mode: 'incremental' } }
```

**PHP action.php** reads correctly:
```php
$options = $data['options'] ?? [];
```
(already correct — only JS and orchestrator side need fixing)

**Rationale**: Minimal change to the existing contract. `options` is an open dict allowing future stage-specific params without schema changes.

**Alternatives considered**: Separate endpoint `/run/{stage}/incremental` — rejected as over-engineering for a single option flag.

---

## R-003: JobStatusManager::updateJobStatus() — PHP writing pipeline_runs.json

**Question**: Should PHP write to `pipeline_runs.json` directly, or should cancel always go through the orchestrator?

**Decision**: PHP writes directly to `pipeline_runs.json` as a fallback when the orchestrator is not reachable. The format must match exactly what Python writes (see `data-model.md` Pipeline Run schema).

**Implementation**:
```php
public function updateJobStatus(string $jobId, array $updates): void {
    $runs = $this->getAllRuns();
    foreach ($runs as &$run) {
        if (($run['job_id'] ?? '') === $jobId) {
            foreach ($updates as $k => $v) {
                $run[$k] = $v;
            }
            break;
        }
    }
    $this->writeRuns($runs);
    $this->cachedRuns = null; // invalidate cache
}
```

A new `writeRuns(array $runs): void` private method handles the file write with file locking (`LOCK_EX`).

**Rationale**: The cancel fallback is a best-effort operation — if the orchestrator is down, PHP cannot stop the container anyway. The goal is just to reflect the cancelled state in the status file so the dashboard shows it.

**Alternatives considered**: Always require orchestrator for cancel — rejected because it blocks the UI when the orchestrator crashes mid-run.

---

## R-004: Sort Key Consistency Between PHP and Python

**Question**: Should `get_last_run` sort by `started_at` or `updated_at`?

**Decision**: Both PHP and Python use `started_at` as the canonical sort key.

**Rationale**: `started_at` is set once at job creation and is immutable. `updated_at` changes on every status update, so two updates to the same job could change the order relative to another job. `started_at` gives a stable, chronological ordering by when the job began.

**Change required**: `server.py::get_last_run` currently sorts by `updated_at` — change to `started_at`.

---

## R-005: ServiceTester.php Extraction

**Question**: Should `testMcpServer()` and `testQdrant()` be a new class, a trait, or a static helper?

**Decision**: New class `ServiceTester` in `dokuwiki_plugin/lib/ServiceTester.php` with two public static methods.

```php
class ServiceTester {
    public static function testMcp(string $url, int $timeout = 5): array { ... }
    public static function testQdrant(string $host, int $port, int $timeout = 5): array { ... }
}
```

Both `action.php` and `admin.php` `require_once` the same file and call `ServiceTester::testMcp(...)`.

**Rationale**: Static methods avoid instantiation overhead; no shared state needed. Class is cleaner than a procedural helper file (aligns with existing `ConfigLoader` pattern).

**Alternatives considered**: PHP trait — rejected because traits are for code reuse within class hierarchies; here we want shared utility callable from two unrelated classes.

---

## R-006: Deploy Stage Container Entrypoint

**Question**: How does the `module_deployer` container know to run `run_deploy.py qdrant` instead of its own `entrypoint.py`?

**Decision**: Add `"pipeline_dir": "05_deploy"` to the deploy entry in `PIPELINE_STAGES`. In `_build_docker_run`, override the image's default CMD by appending the entrypoint args:

```python
cmd.append(image)
if stage_cfg.get("entrypoint_args"):
    cmd.extend(stage_cfg["entrypoint_args"])
else:
    cmd.append(job_id)  # legacy: pass job_id as first arg
```

For deploy: `entrypoint_args = ["python", "run_deploy.py", "qdrant", "--job-id", job_id]`

**Rationale**: `run_deploy.py` is the correct entry point per the pipeline ground truth. The `module_deployer` container still needs the `pipeline/05_deploy/` directory mounted — this was the missing piece.

---

## R-007: compose run Stage-Specific Env Vars

**Question**: When running on host via `docker compose run`, how should stage-specific env vars be passed?

**Decision**: Extend `_build_compose_run` to also iterate `PIPELINE_STAGES[stage].get("extra_env", {})` and append `-e KEY=VALUE` for each entry, mirroring the `_build_docker_run` logic.

**Rationale**: The two execution paths must be equivalent. Currently compose-run is missing all stage-specific env vars (output dir, token paths), making host-mode execution silently broken.
