# Feature 002: Pipeline Orchestration - Implementation Tasks

> **Status**: Ready for Implementation | **Branch**: `002-pipeline-orchestration`
> **Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)
> **Created**: 2026-01-31 | **Estimated Total Effort**: 5-7 Tage

---

## Progress Tracker

| Phase | Tasks | Completed | Progress |
|-------|-------|-----------|----------|
| Phase 1: Foundation | 6 | 0 | ░░░░░░░░░░ 0% |
| Phase 2: Docker Modules | 8 | 0 | ░░░░░░░░░░ 0% |
| Phase 3: PHP Integration | 6 | 0 | ░░░░░░░░░░ 0% |
| Phase 4: Dashboard UI | 5 | 0 | ░░░░░░░░░░ 0% |
| Phase 5: Integration | 4 | 0 | ░░░░░░░░░░ 0% |
| **Total** | **29** | **0** | ░░░░░░░░░░ 0% |

---

## Phase 1: Foundation (Day 1)

### Task 1.1: Data Directory Structure

**ID**: `T-1.1` | **Priority**: P1 | **Effort**: 15 min | **Dependencies**: None

**Description**: Erstelle die Verzeichnisstruktur fuer Pipeline-Output und Logs.

**Files to Create**:
```
data/
├── fetched/
│   └── .gitkeep
├── evaluated/
│   └── .gitkeep
├── embeddings/
│   └── .gitkeep
└── logs/
    └── .gitkeep
```

**Definition of Done**:
- [ ] Alle Verzeichnisse existieren
- [ ] `.gitkeep` Dateien vorhanden
- [ ] `.gitignore` aktualisiert (Output ignorieren, .gitkeep nicht)
- [ ] Commit: "Add data directory structure for pipeline output"

---

### Task 1.2: Update .gitignore for Pipeline Data

**ID**: `T-1.2` | **Priority**: P1 | **Effort**: 10 min | **Dependencies**: T-1.1

**Description**: Aktualisiere `.gitignore` um Pipeline-Output zu ignorieren aber Struktur zu behalten.

**Changes to `.gitignore`**:
```gitignore
# Pipeline Output (Article II-B)
data/fetched/*
!data/fetched/.gitkeep
data/evaluated/*
!data/evaluated/.gitkeep
data/embeddings/*
!data/embeddings/.gitkeep
data/logs/*
!data/logs/.gitkeep
```

**Definition of Done**:
- [ ] `.gitignore` aktualisiert
- [ ] `git status` zeigt keine Pipeline-Output-Dateien
- [ ] Commit: "Update .gitignore for pipeline data directories"

---

### Task 1.3: Pipeline Runs JSON Schema

**ID**: `T-1.3` | **Priority**: P1 | **Effort**: 20 min | **Dependencies**: T-1.1

**Description**: Definiere das JSON-Schema fuer `pipeline_runs.json` und erstelle Beispiel-Datei.

**File**: `data/logs/pipeline_runs.schema.json`
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "array",
  "items": {
    "type": "object",
    "required": ["job_id", "stage", "status", "started_at"],
    "properties": {
      "job_id": { "type": "string", "pattern": "^(fetch|evaluate|embed|deploy)_\\d{8}_\\d{6}$" },
      "stage": { "type": "string", "enum": ["fetch", "evaluate", "embed", "deploy"] },
      "status": { "type": "string", "enum": ["running", "success", "error", "interrupted"] },
      "started_at": { "type": "string", "format": "date-time" },
      "finished_at": { "type": ["string", "null"], "format": "date-time" },
      "duration_seconds": { "type": ["number", "null"] },
      "output_dir": { "type": ["string", "null"] },
      "stats": { "type": ["object", "null"] },
      "error": { "type": ["string", "null"] }
    }
  }
}
```

**Definition of Done**:
- [ ] Schema-Datei erstellt
- [ ] Beispiel `pipeline_runs.json` mit leerem Array erstellt
- [ ] Commit: "Add pipeline_runs.json schema and example"

---

### Task 1.4: Extend env.yaml for Pipeline Config

**ID**: `T-1.4` | **Priority**: P1 | **Effort**: 30 min | **Dependencies**: None

**Description**: Erweitere `config/env.yaml` und `PLACEHOLDER_env.yaml` um Pipeline-spezifische Konfiguration.

**New Section in env.yaml**:
```yaml
PIPELINE_ORCHESTRATION:
  # Docker execution settings
  docker:
    compose_path: ${root_dir}/backend_services
    network: devdito_network
  
  # Stage-specific settings
  stages:
    fetch:
      container: dev-dito-module-fetcher
      timeout_seconds: 3600  # 1 hour max
    evaluate:
      container: dev-dito-module-evaluator
      timeout_seconds: 7200  # 2 hours max
    embed:
      container: dev-dito-module-embedder
      timeout_seconds: 3600
      batch_size: 100
    deploy:
      container: dev-dito-module-deployer
      timeout_seconds: 1800
      default_mode: replace  # replace | upsert
  
  # Logging settings
  logging:
    status_file: ${data_dir}/logs/pipeline_runs.json
    max_log_entries: 100
```

**Definition of Done**:
- [ ] `config/env.yaml` erweitert
- [ ] `config/PLACEHOLDER_env.yaml` erweitert
- [ ] `python config.py` generiert `settings.json` ohne Fehler
- [ ] Commit: "Add PIPELINE_ORCHESTRATION section to env.yaml"

---

### Task 1.5: Verify Existing Pipeline Scripts

**ID**: `T-1.5` | **Priority**: P1 | **Effort**: 30 min | **Dependencies**: None

**Description**: Verifiziere dass die bestehenden Pipeline-Skripte in `pipeline/` aufrufbar sind.

**Checks**:
```powershell
# Check fetcher
cd pipeline/01_wiki_fetcher
python -c "import api_client; print('Fetcher OK')"

# Check evaluator  
cd ../02_deep_evaluation
python -c "import config; print('Evaluator OK')"

# Check embedder
cd ../03_embeddings_creator
python -c "import main; print('Embedder OK')"

# Check deployer
cd ../04_deploy
python -c "import transfer_to_pi; print('Deployer OK')"
```

**Definition of Done**:
- [ ] Alle 4 Module importierbar ohne Fehler
- [ ] Dependencies dokumentiert in jeweiligem `requirements.txt`
- [ ] Eventuell fehlende `__init__.py` erstellt
- [ ] Commit: "Verify and fix pipeline module imports"

---

### Task 1.6: Create Base Dockerfile Template

**ID**: `T-1.6` | **Priority**: P1 | **Effort**: 20 min | **Dependencies**: None

**Description**: Erstelle ein Basis-Dockerfile-Template fuer alle Pipeline-Module.

**File**: `backend_services/Dockerfile.module.template`
```dockerfile
# Base Dockerfile for Dev Dito Pipeline Modules
# Copy and customize for each module

FROM python:3.11-slim

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Entrypoint script
COPY entrypoint.py .

# Mount points:
#   /config  - Zentrale env.yaml (read-only)
#   /data    - Pipeline output
#   /pipeline - Existing scripts (read-only)

ENV PYTHONUNBUFFERED=1
ENV CONFIG_PATH=/config/env.yaml
ENV DATA_PATH=/data

ENTRYPOINT ["python", "entrypoint.py"]
```

**Definition of Done**:
- [ ] Template-Datei erstellt
- [ ] Kommentare erklaeren Mount-Points
- [ ] Commit: "Add Dockerfile template for pipeline modules"

---

## Phase 2: Docker Modules (Day 2-3)

### Task 2.1: Create module_fetcher Container

**ID**: `T-2.1` | **Priority**: P1 | **Effort**: 2h | **Dependencies**: T-1.5, T-1.6

**Description**: Erstelle den Wiki Fetcher Docker-Container mit Thin Wrapper.

**Files to Create**:
```
backend_services/module_fetcher/
├── Dockerfile
├── entrypoint.py
└── requirements.txt
```

**entrypoint.py Logic**:
1. Parse CLI args (job_id)
2. Update status → "running"
3. Execute `fetch_full_wiki_extended.py`
4. Parse output, extract stats
5. Update status → "success" oder "error"

**Definition of Done**:
- [ ] Dockerfile erstellt (basierend auf Template)
- [ ] entrypoint.py implementiert (< 100 Zeilen)
- [ ] requirements.txt mit Fetcher-Dependencies
- [ ] `docker build` erfolgreich
- [ ] `docker run --rm module_fetcher test_job` schreibt Status
- [ ] Commit: "Add module_fetcher Docker container"

---

### Task 2.2: Create module_evaluator Container

**ID**: `T-2.2` | **Priority**: P2 | **Effort**: 2h | **Dependencies**: T-2.1

**Description**: Erstelle den Deep Evaluation Docker-Container.

**Files to Create**:
```
backend_services/module_evaluator/
├── Dockerfile
├── entrypoint.py
└── requirements.txt
```

**Special Considerations**:
- Braucht Zugriff auf LLM (Ollama/OpenAI)
- Laengere Laufzeit (bis 2h)
- Output: ANALYSIS_REPORT.md

**Definition of Done**:
- [ ] Dockerfile erstellt
- [ ] entrypoint.py implementiert
- [ ] OLLAMA_HOST Environment-Variable konfigurierbar
- [ ] `docker build` erfolgreich
- [ ] Commit: "Add module_evaluator Docker container"

---

### Task 2.3: Create module_embedder Container

**ID**: `T-2.3` | **Priority**: P2 | **Effort**: 2h | **Dependencies**: T-2.1

**Description**: Erstelle den Embeddings Creator Docker-Container.

**Files to Create**:
```
backend_services/module_embedder/
├── Dockerfile
├── entrypoint.py
└── requirements.txt
```

**Special Considerations**:
- OPENAI_API_KEY muss sicher uebergeben werden
- Output: embedded_chunks.jsonl
- Batch-Processing fuer Rate Limits

**Definition of Done**:
- [ ] Dockerfile erstellt
- [ ] entrypoint.py implementiert
- [ ] Secrets via Environment (nicht in Logs!)
- [ ] `docker build` erfolgreich
- [ ] Commit: "Add module_embedder Docker container"

---

### Task 2.4: Create module_deployer Container

**ID**: `T-2.4` | **Priority**: P3 | **Effort**: 1.5h | **Dependencies**: T-2.1

**Description**: Erstelle den Qdrant Deploy Docker-Container.

**Files to Create**:
```
backend_services/module_deployer/
├── Dockerfile
├── entrypoint.py
└── requirements.txt
```

**Special Considerations**:
- Muss auf Qdrant warten (depends_on + healthcheck)
- Support fuer `replace` und `upsert` Modi
- Collection-Name konfigurierbar

**Definition of Done**:
- [ ] Dockerfile erstellt
- [ ] entrypoint.py implementiert
- [ ] Deploy-Modus via Argument waehlbar
- [ ] `docker build` erfolgreich
- [ ] Commit: "Add module_deployer Docker container"

---

### Task 2.5: Update docker-compose.yml

**ID**: `T-2.5` | **Priority**: P1 | **Effort**: 1h | **Dependencies**: T-2.1, T-2.2, T-2.3, T-2.4

**Description**: Erweitere `backend_services/docker-compose.yml` um alle Pipeline-Module.

**Changes**:
- Add services: module_fetcher, module_evaluator, module_embedder, module_deployer
- Add `profiles: ["pipeline"]` zu allen Modulen
- Add shared volumes fuer /config, /data, /pipeline
- Update network configuration

**Definition of Done**:
- [ ] Alle 4 Module in docker-compose.yml
- [ ] `docker compose config` zeigt keine Fehler
- [ ] `docker compose --profile pipeline build` erfolgreich
- [ ] Commit: "Add pipeline modules to docker-compose.yml"

---

### Task 2.6: Test Module Fetcher Standalone

**ID**: `T-2.6` | **Priority**: P1 | **Effort**: 1h | **Dependencies**: T-2.5

**Description**: Teste den Wiki Fetcher Container standalone mit echtem LeoWiki-Fetch.

**Test Commands**:
```powershell
cd backend_services

# Build
docker compose --profile pipeline build module_fetcher

# Run with test job ID
docker compose --profile pipeline run --rm module_fetcher test_fetch_001

# Check output
cat ../data/logs/pipeline_runs.json
ls ../data/fetched/
```

**Definition of Done**:
- [ ] Fetcher laeuft durch ohne Fehler
- [ ] `pipeline_runs.json` enthaelt Job-Entry
- [ ] Output in `data/fetched/` vorhanden
- [ ] Statistiken (pages, media) im Status
- [ ] Commit: "Test module_fetcher - working"

---

### Task 2.7: Test Module Embedder Standalone

**ID**: `T-2.7` | **Priority**: P2 | **Effort**: 1h | **Dependencies**: T-2.6

**Description**: Teste den Embeddings Creator Container mit kleinem Test-Datensatz.

**Test Setup**:
1. Kopiere 5-10 Pages aus vorherigem Fetch nach `data/fetched/test_subset/`
2. Run embedder mit diesem Subset
3. Verifiziere Output

**Definition of Done**:
- [ ] Embedder laeuft mit Test-Subset
- [ ] `embedded_chunks.jsonl` wird erstellt
- [ ] Keine API-Keys in Logs sichtbar
- [ ] Commit: "Test module_embedder - working"

---

### Task 2.8: Test Module Deployer Standalone

**ID**: `T-2.8` | **Priority**: P3 | **Effort**: 1h | **Dependencies**: T-2.7

**Description**: Teste den Qdrant Deployer mit Test-Collection.

**Test Setup**:
```powershell
# Start Qdrant if not running
docker compose up -d qdrant_db

# Run deployer with test collection
docker compose --profile pipeline run --rm \
  -e COLLECTION_NAME=wiki_embeddings_test \
  module_deployer test_deploy_001
```

**Definition of Done**:
- [ ] Deployer erstellt Collection in Qdrant
- [ ] Vectors sind in Collection sichtbar
- [ ] `replace` Modus loescht alte Daten
- [ ] Commit: "Test module_deployer - working"

---

## Phase 3: PHP Integration (Day 3-4)

### Task 3.1: Create JobStatusManager.php

**ID**: `T-3.1` | **Priority**: P1 | **Effort**: 1h | **Dependencies**: T-1.3

**Description**: Implementiere die PHP-Klasse zum Lesen/Schreiben von `pipeline_runs.json`.

**File**: `dokuwiki_plugin/lib/JobStatusManager.php`

**Methods**:
- `getAllRuns(): array`
- `getLastRun(string $stage): ?array`
- `getActiveJob(): ?array`
- `getJob(string $jobId): ?array`

**Definition of Done**:
- [ ] Klasse implementiert mit PHPDoc
- [ ] PSR-12 konform
- [ ] Keine Fehler bei `phpcs --standard=PSR12`
- [ ] Commit: "Add JobStatusManager.php"

---

### Task 3.2: Create PipelineOrchestrator.php

**ID**: `T-3.2` | **Priority**: P1 | **Effort**: 2h | **Dependencies**: T-3.1, T-2.5

**Description**: Implementiere die Hauptklasse fuer Pipeline-Ausfuehrung.

**File**: `dokuwiki_plugin/lib/PipelineOrchestrator.php`

**Methods**:
- `runStage(string $stage, array $options = []): array`
- `getStatus(): array`
- `getQdrantInfo(): array`
- `private executeDocker(string $container, string $jobId): bool`

**Security**:
- `escapeshellarg()` fuer alle Inputs
- Admin-Check vor Ausfuehrung

**Definition of Done**:
- [ ] Klasse implementiert mit PHPDoc
- [ ] PSR-12 konform
- [ ] Docker-Pfad aus ConfigLoader
- [ ] Commit: "Add PipelineOrchestrator.php"

---

### Task 3.3: Add AJAX Handler: devdito_pipeline_status

**ID**: `T-3.3` | **Priority**: P1 | **Effort**: 1h | **Dependencies**: T-3.2

**Description**: Fuege AJAX-Handler fuer Pipeline-Status zu `action.php` hinzu.

**Changes to action.php**:
```php
public function register(EventHandler $controller): void
{
    $controller->register_hook('AJAX_CALL_UNKNOWN', 'BEFORE', $this, 'handleAjax');
}

public function handleAjax(Event $event): void
{
    if ($event->data === 'devdito_pipeline_status') {
        $event->stopPropagation();
        $event->preventDefault();
        
        header('Content-Type: application/json');
        
        $orchestrator = new PipelineOrchestrator();
        echo json_encode($orchestrator->getStatus());
    }
}
```

**Definition of Done**:
- [ ] AJAX-Handler registriert
- [ ] `/lib/exe/ajax.php?call=devdito_pipeline_status` liefert JSON
- [ ] Response-Format entspricht API-Contract
- [ ] Commit: "Add AJAX handler for pipeline_status"

---

### Task 3.4: Add AJAX Handler: devdito_run_stage

**ID**: `T-3.4` | **Priority**: P1 | **Effort**: 1.5h | **Dependencies**: T-3.3

**Description**: Fuege AJAX-Handler zum Starten von Pipeline-Stufen hinzu.

**Security Requirements**:
- Admin-Check (`auth_isadmin()`)
- CSRF-Token Validierung
- Input-Sanitization

**Definition of Done**:
- [ ] AJAX-Handler implementiert
- [ ] Admin-Only Access
- [ ] POST-Request mit JSON-Body
- [ ] Response: `{success, job_id, message}`
- [ ] Commit: "Add AJAX handler for run_stage"

---

### Task 3.5: Add AJAX Handler: devdito_job_status

**ID**: `T-3.5` | **Priority**: P1 | **Effort**: 1h | **Dependencies**: T-3.4

**Description**: Fuege AJAX-Handler fuer Job-Status-Abfrage hinzu.

**Definition of Done**:
- [ ] AJAX-Handler implementiert
- [ ] Parameter: `job_id`
- [ ] Response enthaelt Progress und Logs-Tail
- [ ] Commit: "Add AJAX handler for job_status"

---

### Task 3.6: PHP Integration Test

**ID**: `T-3.6` | **Priority**: P1 | **Effort**: 1h | **Dependencies**: T-3.5

**Description**: Teste alle AJAX-Endpoints manuell via Browser/curl.

**Test Commands**:
```powershell
# Status
curl "http://localhost:8080/lib/exe/ajax.php?call=devdito_pipeline_status"

# Run (als Admin eingeloggt)
curl -X POST "http://localhost:8080/lib/exe/ajax.php?call=devdito_run_stage" \
  -H "Content-Type: application/json" \
  -d '{"stage":"fetch"}' \
  --cookie "DokuWiki=..."
```

**Definition of Done**:
- [ ] Alle 3 Endpoints funktionieren
- [ ] JSON-Responses valide
- [ ] Non-Admin bekommt Fehler
- [ ] Commit: "PHP integration tests passed"

---

## Phase 4: Dashboard UI (Day 4-5)

### Task 4.1: Create pipeline.js

**ID**: `T-4.1` | **Priority**: P1 | **Effort**: 2h | **Dependencies**: T-3.6

**Description**: Implementiere das JavaScript fuer das Pipeline-Dashboard.

**File**: `dokuwiki_plugin/dist/pipeline.js`

**Functions**:
- `DevDitoPipeline.init()`
- `DevDitoPipeline.loadStatus()`
- `DevDitoPipeline.renderStages(data)`
- `DevDitoPipeline.runStage(stageId)`
- `DevDitoPipeline.startPolling()`

**Definition of Done**:
- [ ] JavaScript implementiert (Vanilla JS, kein Framework)
- [ ] Status-Polling alle 5 Sekunden
- [ ] Error-Handling fuer Network-Fehler
- [ ] Commit: "Add pipeline.js dashboard script"

---

### Task 4.2: Add Pipeline CSS Styles

**ID**: `T-4.2` | **Priority**: P2 | **Effort**: 1h | **Dependencies**: T-4.1

**Description**: Fuege CSS-Styles fuer Pipeline-Dashboard hinzu.

**File**: `dokuwiki_plugin/dist/pipeline.css`

**Styles**:
- `.devdito-pipeline-grid`: 4-Spalten Grid
- `.devdito-stage-card`: Card fuer jede Stufe
- `.status-success`, `.status-error`, `.status-running`, `.status-pending`
- `.devdito-qdrant-info`: Qdrant-Status-Box
- Responsive fuer Mobile

**Definition of Done**:
- [ ] CSS-Datei erstellt
- [ ] HTL-Branding-Farben (aus bestehendem CSS)
- [ ] Mobile-responsive
- [ ] Commit: "Add pipeline.css styles"

---

### Task 4.3: Extend admin.php with Pipeline Card

**ID**: `T-4.3` | **Priority**: P1 | **Effort**: 1.5h | **Dependencies**: T-4.1, T-4.2

**Description**: Fuege Pipeline-Card zum Admin-Dashboard hinzu.

**Changes to admin.php**:
- Load `pipeline.js` und `pipeline.css`
- Neue Methode `renderPipelineCard()`
- Aufruf in `html()` Methode

**Definition of Done**:
- [ ] Pipeline-Card wird angezeigt
- [ ] JS/CSS werden geladen
- [ ] Keine JS-Konsolen-Fehler
- [ ] Commit: "Add pipeline card to admin dashboard"

---

### Task 4.4: Implement Progress Indicators

**ID**: `T-4.4` | **Priority**: P2 | **Effort**: 1h | **Dependencies**: T-4.3

**Description**: Implementiere Progress-Anzeige waehrend laufender Jobs.

**UI Elements**:
- Spinner-Animation bei "running"
- Progress-Bar wenn `progress.total` bekannt
- Logs-Tail Anzeige (letzte 5 Zeilen)

**Definition of Done**:
- [ ] Spinner bei laufendem Job
- [ ] Progress-Anzeige (wenn verfuegbar)
- [ ] Logs werden angezeigt
- [ ] Commit: "Add progress indicators to pipeline UI"

---

### Task 4.5: Dashboard UI Test

**ID**: `T-4.5` | **Priority**: P1 | **Effort**: 1h | **Dependencies**: T-4.4

**Description**: Vollstaendiger UI-Test des Pipeline-Dashboards.

**Test Cases**:
1. Dashboard laedt und zeigt alle 4 Stufen
2. Fetch-Button funktioniert
3. Status aktualisiert sich automatisch
4. Fehler werden angezeigt
5. Qdrant-Info wird angezeigt

**Definition of Done**:
- [ ] Alle 5 Test-Cases bestanden
- [ ] Screenshots dokumentiert
- [ ] Commit: "Dashboard UI tests passed"

---

## Phase 5: Integration & Deployment (Day 5-6)

### Task 5.1: Full Pipeline Run Test

**ID**: `T-5.1` | **Priority**: P1 | **Effort**: 2h | **Dependencies**: T-4.5

**Description**: Teste den kompletten Pipeline-Flow: Fetch → Evaluate → Embed → Deploy.

**Test Procedure**:
1. Starte Fetch via Dashboard
2. Warte auf Completion (5-15 Min)
3. Starte Evaluate (oder skippe wenn LLM nicht verfuegbar)
4. Starte Embed mit kleinem Subset
5. Starte Deploy zu Test-Collection
6. Verifiziere Qdrant hat neue Vectors

**Definition of Done**:
- [ ] Fetch erfolgreich (>100 Pages)
- [ ] Embed erfolgreich (oder skipped mit Dokumentation)
- [ ] Deploy erfolgreich
- [ ] Qdrant Collection hat Vectors
- [ ] Commit: "Full pipeline run test passed"

---

### Task 5.2: Error Handling Test

**ID**: `T-5.2` | **Priority**: P2 | **Effort**: 1h | **Dependencies**: T-5.1

**Description**: Teste Error-Handling fuer verschiedene Fehlerszenarien.

**Test Cases**:
1. Source Wiki nicht erreichbar → Timeout-Fehler
2. OpenAI API Key fehlt → Fehler vor Start
3. Qdrant nicht erreichbar → Health-Check Fehler
4. Concurrent Job → "Already running" Meldung

**Definition of Done**:
- [ ] Alle 4 Fehlerszenarien getestet
- [ ] Fehler werden im UI angezeigt
- [ ] Keine unbehandelten Exceptions
- [ ] Commit: "Error handling tests passed"

---

### Task 5.3: Deploy Plugin Update

**ID**: `T-5.3` | **Priority**: P1 | **Effort**: 30 min | **Dependencies**: T-5.2

**Description**: Aktualisiere `deploy-plugin.ps1` um neue Dateien.

**Changes**:
```powershell
$itemsToCopy = @(
    # ... existing items ...
    "dist/pipeline.js",
    "dist/pipeline.css"
)
```

**Definition of Done**:
- [ ] Deploy-Script aktualisiert
- [ ] `.\scripts\deploy-plugin.ps1` erfolgreich
- [ ] Neue Dateien im Ziel-Wiki
- [ ] Commit: "Update deploy script for pipeline files"

---

### Task 5.4: Documentation Update

**ID**: `T-5.4` | **Priority**: P2 | **Effort**: 1h | **Dependencies**: T-5.3

**Description**: Aktualisiere Dokumentation fuer Pipeline-Orchestration.

**Files to Update**:
- `README.md`: Pipeline-Section hinzufuegen
- `backend_services/README.md`: Module dokumentieren
- `specs/002-pipeline-orchestration/`: Status auf "Completed"

**Definition of Done**:
- [ ] README.md aktualisiert
- [ ] Module-READMEs erstellt
- [ ] Spec-Status: Completed
- [ ] Commit: "Update documentation for pipeline orchestration"

---

## Task Dependencies Graph

```
Phase 1 (Foundation)
T-1.1 ──► T-1.2
T-1.3 ──────────────────────────────────────► T-3.1
T-1.4
T-1.5 ──► T-2.1
T-1.6 ──► T-2.1

Phase 2 (Docker Modules)
T-2.1 ──► T-2.2, T-2.3, T-2.4
T-2.1, T-2.2, T-2.3, T-2.4 ──► T-2.5
T-2.5 ──► T-2.6 ──► T-2.7 ──► T-2.8

Phase 3 (PHP Integration)
T-3.1 ──► T-3.2 ──► T-3.3 ──► T-3.4 ──► T-3.5 ──► T-3.6

Phase 4 (Dashboard UI)
T-3.6 ──► T-4.1 ──► T-4.3
T-4.1 ──► T-4.2 ──► T-4.3
T-4.3 ──► T-4.4 ──► T-4.5

Phase 5 (Integration)
T-4.5 ──► T-5.1 ──► T-5.2 ──► T-5.3 ──► T-5.4
```

---

## Risk Mitigation Tasks (Optional)

### Task R.1: Docker Socket Alternative

**ID**: `T-R.1` | **Priority**: P3 | **Effort**: 3h | **Dependencies**: T-5.2

**Trigger**: Falls Wiki-Container keinen Docker-Zugriff haben darf.

**Alternative Implementation**:
1. Erstelle `backend_services/orchestrator/` Service
2. REST-API fuer Pipeline-Steuerung
3. Dieser Service hat Docker-Socket-Zugriff
4. PHP ruft Orchestrator-API statt Docker direkt

**Definition of Done**:
- [ ] Orchestrator-Service implementiert
- [ ] REST-API dokumentiert
- [ ] PHP nutzt Orchestrator statt Docker

---

### Task R.2: Local Fallback Mode

**ID**: `T-R.2` | **Priority**: P3 | **Effort**: 2h | **Dependencies**: T-5.2

**Trigger**: Falls Docker nicht verfuegbar ist.

**Implementation**:
- `PipelineOrchestrator::runStageLocal()`
- Direkter Python-Aufruf via `shell_exec()`
- Nur fuer Development/Testing

**Definition of Done**:
- [ ] Fallback-Methode implementiert
- [ ] Konfigurierbar via env.yaml
- [ ] Warnung in Logs wenn Fallback genutzt

---

## Completion Checklist

### Feature Complete Criteria

- [ ] Alle 29 Tasks abgeschlossen
- [ ] Alle Tests bestanden (T-2.6, T-2.7, T-2.8, T-3.6, T-4.5, T-5.1, T-5.2)
- [ ] Keine offenen P1 Bugs
- [ ] Dokumentation aktualisiert
- [ ] Branch merged in `master`

### Post-Merge Tasks

- [ ] Git tag: `v0.2.0-pipeline-orchestration`
- [ ] GitHub Release Notes
- [ ] specs/002-pipeline-orchestration/spec.md → Status: Completed
- [ ] Cleanup: Branch loeschen

---

## Notes

### Bekannte Limitierungen

1. **Kein WebSocket**: Status-Updates via Polling (5s), nicht real-time
2. **Kein Resume**: Abgebrochene Jobs muessen neu gestartet werden
3. **Single Job**: Nur ein Job gleichzeitig (by design)

### Future Improvements (Out of Scope)

- WebSocket fuer Real-time Updates
- Job Queue mit mehreren parallelen Jobs
- Scheduling (Cron-artig)
- Prometheus Metrics Export
