# Feature 002: Pipeline Orchestration

> **Status**: Draft | **Branch**: `002-pipeline-orchestration` | **Priority**: P1-Critical
> **Constitution**: v1.2.0 | **Created**: 2026-01-31

---

## Kontext

Dev Dito (Stack-G) verwaltet eine mehrstufige Wiki-Embedding-Pipeline, die bisher nur als
einzelne Skripte ausgefuehrt wurde. Diese Spezifikation definiert die Integration der
Pipeline-Module in ein orchestrierbares System mit DokuWiki Admin-Interface.

**Architektur-Referenz** (aus `sources_dev_dito.yaml`):

```
┌─────────────────────┐     ┌─────────────────────┐     ┌─────────────────────┐
│   STAGE 1: FETCH    │ ──► │  STAGE 2: EVALUATE  │ ──► │  STAGE 3: EMBED     │
│   Wiki Fetcher      │     │  Deep Analysis      │     │  Embeddings Creator │
│   (JSON-RPC API)    │     │  (LLM-gestuetzt)    │     │  (OpenAI/Local)     │
└─────────────────────┘     └─────────────────────┘     └─────────────────────┘
                                                                  │
                                                                  ▼
                                                        ┌─────────────────────┐
                                                        │   STAGE 4: DEPLOY   │
                                                        │   Qdrant Upload     │
                                                        │   (Vector DB)       │
                                                        └─────────────────────┘
```

**Laufende Docker-Services** (Stand: 2026-01-31):

| Container                   | Port | Status    | Stack   |
|-----------------------------|------|-----------|---------|
| dev-dito-wiki               | 8080 | healthy   | Stack-G |
| wiki-sandbox                | 8090 | healthy   | Stack-A |
| qdrant-main-vector-db       | 6333 | running   | Stack-D |
| semantic-search-wiki-core   | 3000 | unhealthy | Stack-H |
| keycloak-server             | 8081 | healthy   | Stack-B |

---

## Problem Statement

### Aktuelle Probleme

1. **Fragmentierte Ausfuehrung**: Pipeline-Stufen werden manuell einzeln gestartet
   (`python fetch_full_wiki_extended.py`, dann `python run_deep_evaluation.py`, etc.)
2. **Keine Statusuebersicht**: Kein zentraler Ort um zu sehen, welche Stufe wann zuletzt lief
3. **Keine Fehlerbehandlung**: Fehler in einer Stufe werden nicht erkannt oder geloggt
4. **Keine Output-Validierung**: Erfolgreich gefetchte Daten werden nicht automatisch geprueft
5. **Manuelle Konfiguration**: Jedes Modul hat eigene `env.yaml`, nicht zentral verwaltet

### Betroffene Nutzer

- **Primary User**: Wiki-Administrator (Jan/Imre)
- **Use Case**: LeoWiki-Inhalte in durchsuchbare Embeddings transformieren

---

## User Stories

### US-001: Pipeline-Status Dashboard (P1)

**Als** Wiki-Administrator  
**moechte ich** auf dem Dev Dito Dashboard sehen, welche Pipeline-Stufen verfuegbar sind
und wann sie zuletzt ausgefuehrt wurden,  
**damit ich** den aktuellen Stand der Embedding-Pipeline einschaetzen kann.

**Akzeptanzkriterien:**
- [ ] Dashboard zeigt alle 4 Pipeline-Stufen (Fetch, Evaluate, Embed, Deploy)
- [ ] Jede Stufe zeigt: Name, Beschreibung, letzter Lauf (Timestamp), Status
- [ ] Status-Farben: gruen (erfolgreich), gelb (nie gelaufen), rot (Fehler)
- [ ] Dashboard aktualisiert sich beim Laden der Seite

### US-002: Wiki Fetch via Admin-Interface (P1)

**Als** Wiki-Administrator  
**moechte ich** ueber das Admin-Interface einen Wiki-Fetch starten koennen,  
**damit ich** nicht mehr manuell Python-Skripte ausfuehren muss.

**Akzeptanzkriterien:**
- [ ] "Fetch starten" Button im Dashboard
- [ ] Fetch verwendet zentrale `config/env.yaml` Konfiguration
- [ ] Progress-Anzeige waehrend des Fetchs (oder zumindest "laeuft...")
- [ ] Nach Abschluss: Anzahl gefetchter Pages/Media anzeigen
- [ ] Bei Fehler: Fehlermeldung im Dashboard anzeigen

### US-003: Fetch-Output Validierung (P2)

**Als** Wiki-Administrator  
**moechte ich** nach einem Fetch automatisch pruefen lassen, ob die Daten valide sind,  
**damit ich** Fehler fruehzeitig erkenne.

**Akzeptanzkriterien:**
- [ ] Nach Fetch: Automatische Validierung des Output-Ordners
- [ ] Checks: Mindestens 1 Page, Mindestens 1 Media, JSON-Dateien parsebar
- [ ] Validierungsergebnis wird im Dashboard angezeigt
- [ ] Warnung wenn Output leer oder korrupt

### US-004: Deep Evaluation via Admin-Interface (P2)

**Als** Wiki-Administrator  
**moechte ich** eine Deep Evaluation der gefetchten Daten starten koennen,  
**damit ich** deren RAG-Readiness analysieren kann.

**Akzeptanzkriterien:**
- [ ] "Evaluation starten" Button (erst nach erfolgreichem Fetch aktiviert)
- [ ] Evaluation verwendet LLM-Client (Ollama/LMStudio/OpenAI via Config)
- [ ] Nach Abschluss: Link zum generierten Report (Markdown)
- [ ] Geschaetzte Dauer/Kosten vor Start anzeigen

### US-005: Embeddings Creation via Admin-Interface (P2)

**Als** Wiki-Administrator  
**moechte ich** Embeddings aus den gefetchten Daten generieren koennen,  
**damit ich** sie in Qdrant hochladen kann.

**Akzeptanzkriterien:**
- [ ] "Embeddings erstellen" Button (erst nach erfolgreichem Fetch aktiviert)
- [ ] Wahl des Embedding-Models (aus Config: OpenAI, lokales Model)
- [ ] Progress-Anzeige: X/Y Dokumente verarbeitet
- [ ] Nach Abschluss: Anzahl Chunks, geschaetzte Kosten
- [ ] Output: `embedded_chunks.jsonl` im data-Verzeichnis

### US-006: Qdrant Deploy via Admin-Interface (P3)

**Als** Wiki-Administrator  
**moechte ich** die erstellten Embeddings in Qdrant hochladen koennen,  
**damit ich** sie fuer die Semantic Search verwenden kann.

**Akzeptanzkriterien:**
- [ ] "Deploy to Qdrant" Button (erst nach Embeddings aktiviert)
- [ ] Verbindungstest zu Qdrant vor Upload
- [ ] Progress: X/Y Chunks hochgeladen
- [ ] Nach Abschluss: Collection-Info (Anzahl Vectors, Dimension)
- [ ] Option: Alte Collection loeschen vs. inkrementelles Update

### US-007: Zentrale Pipeline-Konfiguration (P1)

**Als** Wiki-Administrator  
**moechte ich** alle Pipeline-Einstellungen an einem Ort konfigurieren,  
**damit ich** nicht in 4 verschiedenen `env.yaml` Dateien suchen muss.

**Akzeptanzkriterien:**
- [ ] Zentrale `config/env.yaml` im Repository-Root (existiert bereits)
- [ ] Pipeline-Module lesen aus zentraler Config (kein eigenes env.yaml mehr)
- [ ] DokuWiki Admin-Seite zeigt aktuelle Config-Werte (read-only)
- [ ] Config-Aenderungen erfordern Datei-Edit (kein Web-Editor)

---

## Functional Requirements

### FR-100: Pipeline Status API

| ID     | Requirement                                                        | Priority |
|--------|--------------------------------------------------------------------|----------|
| FR-101 | AJAX-Endpoint `/lib/exe/ajax.php?call=devdito_pipeline_status`     | P1       |
| FR-102 | Response enthaelt Status aller 4 Pipeline-Stufen als JSON          | P1       |
| FR-103 | Status-Objekt: `{stage, name, last_run, status, output_dir}`       | P1       |
| FR-104 | Status wird aus `data/logs/pipeline_runs.json` gelesen             | P1       |

### FR-200: Pipeline Execution API

| ID     | Requirement                                                        | Priority |
|--------|--------------------------------------------------------------------|----------|
| FR-201 | AJAX-Endpoint `/lib/exe/ajax.php?call=devdito_run_stage`           | P1       |
| FR-202 | Parameter: `stage` (fetch, evaluate, embed, deploy)                | P1       |
| FR-203 | Execution via `docker exec` zu `dev-dito-module-*` Containern      | P1       |
| FR-204 | Response: `{success, job_id, message}` (async, nicht blockierend)  | P1       |
| FR-205 | Execution-Log wird in `data/logs/` geschrieben                     | P2       |
| FR-206 | Job-Status abrufbar via `devdito_job_status&job_id=X`              | P1       |
| FR-207 | Background-Execution: Prozess laeuft weiter nach HTTP-Response     | P1       |

### FR-300: Pipeline Module Integration (Docker)

| ID     | Requirement                                                        | Priority |
|--------|--------------------------------------------------------------------|----------|
| FR-301 | Container: `dev-dito-module-fetcher` fuehrt Wiki Fetcher aus       | P1       |
| FR-302 | Container: `dev-dito-module-evaluator` fuehrt Deep Evaluation aus  | P2       |
| FR-303 | Container: `dev-dito-module-embedder` fuehrt Embeddings Creator aus| P2       |
| FR-304 | Container: `dev-dito-module-deployer` laedt in Qdrant hoch         | P3       |
| FR-305 | Alle Container mounten `/config` Volume fuer zentrale `env.yaml`   | P1       |
| FR-306 | Alle Container mounten `/data` Volume fuer Output                  | P1       |
| FR-307 | Container sind im `docker-compose.yml` von Stack-G definiert       | P1       |
| FR-308 | Fallback: Lokale Ausfuehrung wenn Container nicht laeuft           | P3       |

### FR-400: Configuration Integration

| ID     | Requirement                                                        | Priority |
|--------|--------------------------------------------------------------------|----------|
| FR-401 | Zentrale Config in `config/env.yaml` (bereits vorhanden)           | P1       |
| FR-402 | PHP liest Config via `ConfigLoader.php` aus `settings.json`        | P1       |
| FR-403 | Python-Module importieren `config.py` aus Repository-Root          | P1       |
| FR-404 | Fallback: Module-lokale Config wenn zentrale nicht verfuegbar      | P2       |

### FR-500: Qdrant Multi-Collection Support

| ID     | Requirement                                                        | Priority |
|--------|--------------------------------------------------------------------|----------|
| FR-501 | Default Collection: `wiki_embeddings` (Production)                 | P1       |
| FR-502 | Test Collection: `wiki_embeddings_test` (Embedding-Vergleiche)     | P2       |
| FR-503 | Deploy-Modus `replace`: Collection loeschen und neu erstellen      | P1       |
| FR-504 | Deploy-Modus `upsert`: Nur geaenderte Chunks aktualisieren         | P3       |
| FR-505 | Collection-Auswahl via Config oder UI-Parameter                    | P2       |
| FR-506 | Collection-Info im Dashboard (Anzahl Vectors, Dimension, Size)     | P2       |

---

## Non-Functional Requirements

### NFR-100: Performance

| ID      | Requirement                                                       |
|---------|-------------------------------------------------------------------|
| NFR-101 | Pipeline-Status-Abfrage < 500ms                                   |
| NFR-102 | Fetch-Timeout konfigurierbar (Default: 30s pro Request)           |
| NFR-103 | Embedding-Generation: Max 100 Dokumente parallel (OpenAI Rate Limit) |

### NFR-200: Reliability

| ID      | Requirement                                                       |
|---------|-------------------------------------------------------------------|
| NFR-201 | Pipeline-Fehler brechen nicht das gesamte Admin-Interface ab      |
| NFR-202 | Timeouts werden als Fehler geloggt, nicht als Absturz             |
| NFR-203 | Unvollstaendige Runs werden als "interrupted" markiert            |

### NFR-300: Security

| ID      | Requirement                                                       |
|---------|-------------------------------------------------------------------|
| NFR-301 | Pipeline-Execution nur fuer Admin-User (DokuWiki ACL)             |
| NFR-302 | Keine API-Keys im Browser-JavaScript                              |
| NFR-303 | Log-Dateien enthalten keine Secrets                               |

---

## Technical Constraints

### Constitution Compliance

| Article   | Constraint                                                           |
|-----------|----------------------------------------------------------------------|
| I         | Kein direkter PHP→Python Aufruf; Execution via Docker exec/HTTP API  |
| II        | JSON als Output aller Pipeline-Module                                |
| II-B      | Zentrale Config in `env.yaml`, keine hardcodierten Werte             |
| VII       | Thin Wrappers um bestehende Pipeline-Skripte, keine neue Logik       |

### Docker Stack Dependencies (aus Prompt.md)

| Stack   | Services                          | Relevanz fuer Pipeline           |
|---------|-----------------------------------|----------------------------------|
| Stack-G | dev-dito-wiki, dev-dito-module-*  | Pipeline-Execution               |
| Stack-D | qdrant-main-vector-db             | Embedding-Storage                |
| Stack-E | prometheus, grafana, mlflow       | Pipeline-Monitoring (optional)   |
| Stack-H | semantic-search-wiki-core         | Nutzt Pipeline-Output            |

### Infrastructure Dependencies

| Dependency              | Required For          | Status (2026-01-31)    |
|-------------------------|-----------------------|------------------------|
| DokuWiki (Stack-G)      | Admin Interface       | ✅ Running (8080)      |
| Qdrant (Stack-D)        | Deploy Stage          | ✅ Running (6333)      |
| OpenAI API              | Embeddings (optional) | ⚙️ Config required     |
| Ollama/LMStudio         | Evaluation (optional) | ⚙️ Config required     |
| Source Wiki (LeoWiki)   | Fetch Stage           | ✅ Accessible (HTTPS)  |
| Docker CLI              | Module Execution      | ✅ Available           |

---

## Data Flow (Docker-basiert)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Dev Dito Admin Dashboard (Browser)                       │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌──────────────────┐  │
│  │  FETCH  │  │ EVALUATE│  │  EMBED  │  │ DEPLOY  │  │ [Status] [Logs]  │  │
│  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘  └──────────────────┘  │
└───────┼────────────┼────────────┼────────────┼─────────────────────────────┘
        │            │            │            │         AJAX Polling (5s)
        ▼            ▼            ▼            ▼                ▲
┌──────────────────────────────────────────────────────────────┼──────────────┐
│                    Stack-G: dev-dito-wiki (PHP)              │              │
│  ┌─────────────────────────────────────────────────────────┐ │              │
│  │ action.php: devdito_run_stage, devdito_pipeline_status  │─┘              │
│  └─────────────────────────┬───────────────────────────────┘                │
│                            │ docker exec / HTTP API                         │
└────────────────────────────┼────────────────────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┬─────────────────┐
        ▼                    ▼                    ▼                 ▼
┌───────────────┐  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│  Stack-G:     │  │  Stack-G:     │  │  Stack-G:     │  │  Stack-G:     │
│  dev-dito-    │  │  dev-dito-    │  │  dev-dito-    │  │  dev-dito-    │
│  module-      │  │  module-      │  │  module-      │  │  module-      │
│  fetcher      │  │  evaluator    │  │  embedder     │  │  deployer     │
└───────┬───────┘  └───────┬───────┘  └───────┬───────┘  └───────┬───────┘
        │                  │                  │                  │
        ▼                  ▼                  ▼                  ▼
┌───────────────┐  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│  LeoWiki      │  │  Stack-D:     │  │  OpenAI API   │  │  Stack-D:     │
│  JSON-RPC     │  │  Ollama/      │  │  (external)   │  │  qdrant-main  │
│  (external)   │  │  LMStudio     │  │               │  │  -vector-db   │
└───────────────┘  └───────────────┘  └───────────────┘  └───────────────┘
                                                                 │
                                                                 ▼
                                                        ┌───────────────┐
                                                        │  Stack-H:     │
                                                        │  MCP Server   │
                                                        │  (Leonidas)   │
                                                        └───────────────┘
```

### Monitoring Integration (Stack-E/F)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Stack-E: extensions-ai-evaluation-services               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │  MLflow     │  │   RAGAS     │  │ Prometheus  │  │  Grafana    │        │
│  │  Tracking   │  │  Evaluation │  │  Metrics    │  │  Dashboards │        │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘        │
└─────────┼────────────────┼────────────────┼────────────────┼────────────────┘
          │                │                │                │
          └────────────────┴────────────────┴────────────────┘
                                    ▲
                         Metrics Export von Pipeline-Modulen
```

---

## Output Directories

```
dev_dito/
├── data/
│   ├── fetched/                    # Stage 1 Output (Wiki Content)
│   │   └── fetched_at_{timestamp}/
│   │       ├── pages/              # Page JSON files
│   │       ├── media/              # Media files
│   │       └── fetch_statistics.json
│   ├── evaluated/                  # Stage 2 Output (Analysis)
│   │   └── eval_{timestamp}/
│   │       ├── ANALYSIS_REPORT.md
│   │       └── preprocessing_strategies.yaml
│   ├── embeddings/                 # Stage 3 Output (Vectors)
│   │   └── embedded_chunks.jsonl
│   └── logs/                       # Pipeline Logs
│       └── pipeline_runs.json      # Status History
└── config/
    ├── env.yaml                    # Central Configuration
    └── settings.json               # Auto-generated for PHP
```

---

## Success Criteria

| ID     | Criterion                                                        | Target    |
|--------|------------------------------------------------------------------|-----------|
| SC-001 | Wiki Fetch via Dashboard funktioniert                            | 100%      |
| SC-002 | Fetch-Output wird validiert und Status angezeigt                 | 100%      |
| SC-003 | Alle 4 Pipeline-Stufen im Dashboard sichtbar                     | 100%      |
| SC-004 | Zentrale Config wird von allen Modulen gelesen                   | 100%      |
| SC-005 | Keine hardcodierten URLs/Tokens im Code                          | 100%      |
| SC-006 | Pipeline-Errors werden geloggt und im UI angezeigt               | 100%      |
| SC-007 | Embeddings koennen in Qdrant deployed werden                     | P3        |
| SC-008 | Docker-Module starten/stoppen via Dashboard                      | 100%      |
| SC-009 | Background-Jobs laufen ohne UI-Blockierung                       | 100%      |
| SC-010 | Job-Status wird via Polling aktualisiert                         | 100%      |
| SC-011 | Qdrant Collection-Info wird im Dashboard angezeigt               | P2        |

---

## Edge Cases

| Case | Description                               | Expected Behavior                         |
|------|-------------------------------------------|-------------------------------------------|
| E-01 | Source Wiki nicht erreichbar              | Timeout + Fehlermeldung, kein Absturz     |
| E-02 | OpenAI API Key fehlt                      | Fehler vor Start, nicht waehrend Embedding|
| E-03 | Qdrant nicht erreichbar                   | Health-Check-Fehler, Deploy-Button disabled|
| E-04 | Fetch laeuft bereits                      | "Pipeline laeuft bereits" Meldung         |
| E-05 | Leeres Fetch-Ergebnis (0 Pages)           | Warnung, Validierung schlaegt fehl        |
| E-06 | Disk voll waehrend Fetch                  | Fehler geloggt, partieller Output bleibt  |

---

## Design Decisions (Resolved)

### DD-001: Async Execution mit Monitoring

**Entscheidung**: Pipeline-Stufen laufen als **Background-Jobs** mit Status-Polling.

**Begruendung** (aus Prompt.md):
- Stack-E (extensions-ai-evaluation-services) enthaelt Prometheus/Grafana fuer Monitoring
- Stack-F (extensions-observability-services) fuer Live-Verfolgung
- Lange Laufzeiten (Fetch: 5-30 Min, Embedding: 10-60 Min) blockieren sonst UI
- Dev Dito Dashboard zeigt Live-Status und Progress via AJAX-Polling

**Implementierung**:
- PHP startet Python-Prozess im Background (`nohup` / `&`)
- Status wird in `data/logs/pipeline_runs.json` geschrieben
- Dashboard pollt alle 5 Sekunden fuer Updates
- Optional: WebSocket fuer Echtzeit-Updates (spaeter)

### DD-002: Modulare Docker-Architektur

**Entscheidung**: Pipeline-Module laufen als **separate Docker-Services** in Stack-G.

**Begruendung** (aus Prompt.md Stack-G Spezifikation):
- Naming Convention: `dev-dito-module-[SERVICE-NAME]`
- Beispiele: `dev-dito-module-parser`, `dev-dito-module-embedder`, `dev-dito-module-indexer`
- Jedes Modul ist eigenstaendig startbar/stoppbar
- Dev Dito Plugin steuert diese Services via Docker CLI oder HTTP-API

**Stack-G Container-Planung**:
```
extension-dev-dito-services (Stack-G)
├── dev-dito-wiki          # DokuWiki mit Plugin (Port 8080)
├── dev-dito-module-fetcher    # Wiki Fetcher Service
├── dev-dito-module-evaluator  # Deep Evaluation Service
├── dev-dito-module-embedder   # Embeddings Creator Service
└── dev-dito-module-deployer   # Qdrant Upload Service
```

### DD-003: Qdrant Multi-Collection Strategie

**Entscheidung**: Eine **Haupt-Collection** + optionale **Test-Collections** fuer Embedding-Vergleiche.

**Begruendung** (aus Prompt.md Stack-D Spezifikation):
- `qdrant-main-vector-db`: Haupt-Qdrant fuer Semantic Search (Leonidas)
- Optionale `qdrant-database-[NAME]`: Fuer A/B-Tests verschiedener Embeddings
- Dev Dito muss beide Szenarien unterstuetzen

**Collections**:
| Collection | Zweck | Dimension |
|------------|-------|-----------|
| `wiki_embeddings` | Production (Semantic Search) | 3072 (OpenAI large) |
| `wiki_embeddings_test` | Embedding-Vergleiche | variabel |
| `wiki_embeddings_local` | Lokale Models (Ollama) | 384-1024 |

**Deploy-Modi**:
- `replace`: Collection loeschen und neu erstellen (Default fuer Tests)
- `upsert`: Nur geaenderte Chunks aktualisieren (Production)

---

## Related Specs

- [001-plugin-dev-deploy](../001-plugin-dev-deploy/spec.md) - Basis-Plugin und zentrale Config

---

## References

- [sources_dev_dito.yaml](D:/_Repositories/00_Die_Bibliothek/Prompts/sources_dev_dito.yaml) - Pipeline Overview
- [Constitution v1.2.0](../../.specify/memory/constitution.md) - Article II-B (Centralized Config)
- [Enterprise Plan](/path/to/legacy-stack/_ENTERPRISE__PLAN_/Prompt.md) - Stack-G Requirements
- [DokuWiki AJAX](https://www.dokuwiki.org/devel:ajax) - AJAX-Endpoint Development
