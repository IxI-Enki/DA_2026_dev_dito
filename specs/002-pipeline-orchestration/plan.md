# Feature 002: Pipeline Orchestration - Implementation Plan

> **Status**: Draft | **Branch**: `002-pipeline-orchestration` | **Created**: 2026-01-31
> **Spec**: [spec.md](./spec.md) | **Constitution**: v1.2.0

---

## Executive Summary

Dieser Plan beschreibt die technische Implementierung der Pipeline-Orchestrierung fuer Dev Dito.
Die Kernidee: Bestehende Python-Skripte (aus `sources_dev_dito.yaml`) werden in Docker-Container
verpackt und ueber das DokuWiki Admin-Interface gesteuert.

**Keine neue Logik in Pipeline-Modulen** - nur Thin Wrappers (Constitution Article VII).

---

## Constitution Compliance Check

| Article | Requirement | Implementation |
|---------|-------------|----------------|
| I       | Schicht-Trennung | PHP→Docker exec (kein subprocess) |
| II      | JSON-Interface | Alle Module Output JSON/JSONL |
| II-B    | Zentrale Config | `/config/env.yaml` fuer alle Module |
| VII     | Thin Wrappers | Keine neue Business-Logik |

---

## Component Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              DokuWiki Plugin Layer                              │
├─────────────────────────────────────────────────────────────────────────────────┤
│  dokuwiki_plugin/                                                               │
│  ├── action.php          # AJAX-Handler: run_stage, pipeline_status, job_status│
│  ├── admin.php           # Dashboard UI mit Pipeline-Karten                     │
│  └── lib/                                                                       │
│      ├── ConfigLoader.php      # Liest settings.json                           │
│      ├── PipelineOrchestrator.php  # NEW: Docker exec + Job-Management         │
│      └── JobStatusManager.php      # NEW: Liest/Schreibt pipeline_runs.json    │
└─────────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       │ docker exec / REST API
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           Docker Module Layer (Stack-G)                         │
├─────────────────────────────────────────────────────────────────────────────────┤
│  backend_services/                                                              │
│  ├── docker-compose.yml        # ERWEITERT: Pipeline-Module                     │
│  ├── module_fetcher/           # NEW: Wiki Fetcher Container                    │
│  │   ├── Dockerfile                                                             │
│  │   ├── entrypoint.py         # Thin Wrapper um fetch_full_wiki_extended.py   │
│  │   └── requirements.txt                                                       │
│  ├── module_evaluator/         # NEW: Deep Evaluation Container                 │
│  │   ├── Dockerfile                                                             │
│  │   ├── entrypoint.py         # Thin Wrapper um run_deep_evaluation.py        │
│  │   └── requirements.txt                                                       │
│  ├── module_embedder/          # NEW: Embeddings Creator Container              │
│  │   ├── Dockerfile                                                             │
│  │   ├── entrypoint.py         # Thin Wrapper um main.py                       │
│  │   └── requirements.txt                                                       │
│  └── module_deployer/          # NEW: Qdrant Upload Container                   │
│      ├── Dockerfile                                                             │
│      ├── entrypoint.py         # Thin Wrapper um init_collection.py            │
│      └── requirements.txt                                                       │
└─────────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       │ Volume Mounts
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              Shared Volumes                                     │
├─────────────────────────────────────────────────────────────────────────────────┤
│  /config                        # Zentrale config/env.yaml                      │
│  /data                          # Pipeline Output (fetched/, evaluated/, ...)   │
│  /pipeline                      # Bestehende Pipeline-Skripte (read-only)       │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Technology Stack

| Component | Technology | Justification |
|-----------|------------|---------------|
| Admin UI | PHP + Vanilla JS | DokuWiki Standard, kein Build-Step |
| Docker Execution | `shell_exec('docker exec ...')` | Constitution Article I |
| Job Tracking | JSON File (`pipeline_runs.json`) | Einfach, kein DB noetig |
| Module Communication | Shared Volumes + Exit Codes | KISS Principle |
| Status Polling | AJAX (5s Interval) | Low Complexity |

---

## API Contracts

### AJAX Endpoint: `devdito_pipeline_status`

**Request:**
```http
GET /lib/exe/ajax.php?call=devdito_pipeline_status
```

**Response:**
```json
{
  "stages": [
    {
      "id": "fetch",
      "name": "Wiki Fetcher",
      "description": "Fetcht LeoWiki via JSON-RPC API",
      "status": "success",
      "last_run": "2026-01-31T14:30:00Z",
      "duration_seconds": 1234,
      "output_dir": "data/fetched/fetched_at_20260131_143000",
      "stats": {
        "pages": 207,
        "media": 661
      }
    },
    {
      "id": "evaluate",
      "name": "Deep Evaluation",
      "description": "LLM-gestuetzte Inhaltsanalyse",
      "status": "never_run",
      "last_run": null,
      "output_dir": null
    },
    {
      "id": "embed",
      "name": "Embeddings Creator",
      "description": "Generiert Embeddings via OpenAI/lokales Model",
      "status": "never_run",
      "last_run": null
    },
    {
      "id": "deploy",
      "name": "Qdrant Deploy",
      "description": "Laedt Embeddings in Qdrant hoch",
      "status": "never_run",
      "last_run": null
    }
  ],
  "active_job": null,
  "qdrant_info": {
    "connected": true,
    "collection": "wiki_embeddings",
    "vectors": 3417,
    "dimension": 3072
  }
}
```

### AJAX Endpoint: `devdito_run_stage`

**Request:**
```http
POST /lib/exe/ajax.php?call=devdito_run_stage
Content-Type: application/json

{
  "stage": "fetch",
  "options": {
    "collection": "wiki_embeddings",
    "mode": "replace"
  }
}
```

**Response (Immediate):**
```json
{
  "success": true,
  "job_id": "fetch_20260131_143000",
  "message": "Fetch gestartet. Job-ID: fetch_20260131_143000"
}
```

### AJAX Endpoint: `devdito_job_status`

**Request:**
```http
GET /lib/exe/ajax.php?call=devdito_job_status&job_id=fetch_20260131_143000
```

**Response:**
```json
{
  "job_id": "fetch_20260131_143000",
  "stage": "fetch",
  "status": "running",
  "progress": {
    "current": 150,
    "total": 207,
    "message": "Fetching pages... 150/207"
  },
  "started_at": "2026-01-31T14:30:00Z",
  "logs_tail": [
    "[14:30:05] Fetching namespace: teacher",
    "[14:30:10] Fetched 50 pages",
    "[14:30:15] Fetching namespace: student"
  ]
}
```

---

## Docker Module Specification

### Module: `dev-dito-module-fetcher`

**Dockerfile:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy entrypoint (Thin Wrapper)
COPY entrypoint.py .

# Mount points:
#   /config  - Zentrale env.yaml
#   /data    - Output-Verzeichnis
#   /pipeline - Bestehende Skripte (read-only)

ENV PYTHONUNBUFFERED=1
ENV CONFIG_PATH=/config/env.yaml

ENTRYPOINT ["python", "entrypoint.py"]
```

**entrypoint.py (Thin Wrapper):**
```python
#!/usr/bin/env python3
"""
Thin Wrapper fuer Wiki Fetcher.
Laedt zentrale Config, fuehrt fetch_full_wiki_extended.py aus,
schreibt Status in pipeline_runs.json.

Constitution Article VII: Keine eigene Business-Logik!
"""
import sys
import json
import subprocess
from datetime import datetime
from pathlib import Path

# Paths
CONFIG_PATH = Path("/config/env.yaml")
DATA_PATH = Path("/data")
PIPELINE_PATH = Path("/pipeline/01_wiki_fetcher")
STATUS_FILE = DATA_PATH / "logs" / "pipeline_runs.json"

def update_status(job_id: str, status: str, **kwargs):
    """Update job status in pipeline_runs.json"""
    STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    runs = []
    if STATUS_FILE.exists():
        runs = json.loads(STATUS_FILE.read_text())
    
    # Find or create job entry
    job = next((r for r in runs if r["job_id"] == job_id), None)
    if not job:
        job = {"job_id": job_id, "stage": "fetch"}
        runs.append(job)
    
    job["status"] = status
    job["updated_at"] = datetime.now().isoformat()
    job.update(kwargs)
    
    STATUS_FILE.write_text(json.dumps(runs, indent=2))

def main():
    job_id = sys.argv[1] if len(sys.argv) > 1 else f"fetch_{datetime.now():%Y%m%d_%H%M%S}"
    
    update_status(job_id, "running", started_at=datetime.now().isoformat())
    
    try:
        # Run the actual fetcher script
        result = subprocess.run(
            ["python", str(PIPELINE_PATH / "fetch_full_wiki_extended.py")],
            cwd=str(PIPELINE_PATH),
            capture_output=True,
            text=True,
            env={
                "CONFIG_PATH": str(CONFIG_PATH),
                "OUTPUT_DIR": str(DATA_PATH / "fetched"),
                **os.environ
            }
        )
        
        if result.returncode == 0:
            update_status(job_id, "success", 
                          finished_at=datetime.now().isoformat(),
                          output=result.stdout[-1000:])  # Last 1000 chars
        else:
            update_status(job_id, "error",
                          finished_at=datetime.now().isoformat(),
                          error=result.stderr[-1000:])
            sys.exit(1)
            
    except Exception as e:
        update_status(job_id, "error", error=str(e))
        sys.exit(1)

if __name__ == "__main__":
    main()
```

---

## Docker Compose Extension

**backend_services/docker-compose.yml (Erweiterung):**

```yaml
version: '3.8'

services:
  # ... existing services (qdrant_db, wiki_mcp_server) ...

  # ==========================================================================
  # Pipeline Module: Wiki Fetcher
  # ==========================================================================
  module_fetcher:
    build:
      context: ./module_fetcher
      dockerfile: Dockerfile
    container_name: dev-dito-module-fetcher
    profiles: ["pipeline"]  # Nur starten wenn explizit aufgerufen
    volumes:
      - ../config:/config:ro
      - ../data:/data
      - ../pipeline/01_wiki_fetcher:/pipeline/01_wiki_fetcher:ro
    environment:
      - CONFIG_PATH=/config/env.yaml
    networks:
      - devdito_network

  # ==========================================================================
  # Pipeline Module: Deep Evaluator
  # ==========================================================================
  module_evaluator:
    build:
      context: ./module_evaluator
      dockerfile: Dockerfile
    container_name: dev-dito-module-evaluator
    profiles: ["pipeline"]
    volumes:
      - ../config:/config:ro
      - ../data:/data
      - ../pipeline/02_deep_evaluation:/pipeline/02_deep_evaluation:ro
    environment:
      - CONFIG_PATH=/config/env.yaml
      - OLLAMA_HOST=${OLLAMA_HOST:-ollama}
    networks:
      - devdito_network

  # ==========================================================================
  # Pipeline Module: Embeddings Creator
  # ==========================================================================
  module_embedder:
    build:
      context: ./module_embedder
      dockerfile: Dockerfile
    container_name: dev-dito-module-embedder
    profiles: ["pipeline"]
    volumes:
      - ../config:/config:ro
      - ../data:/data
      - ../pipeline/03_embeddings_creator:/pipeline/03_embeddings_creator:ro
    environment:
      - CONFIG_PATH=/config/env.yaml
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    networks:
      - devdito_network

  # ==========================================================================
  # Pipeline Module: Qdrant Deployer
  # ==========================================================================
  module_deployer:
    build:
      context: ./module_deployer
      dockerfile: Dockerfile
    container_name: dev-dito-module-deployer
    profiles: ["pipeline"]
    depends_on:
      qdrant_db:
        condition: service_healthy
    volumes:
      - ../config:/config:ro
      - ../data:/data
    environment:
      - CONFIG_PATH=/config/env.yaml
      - QDRANT_HOST=qdrant_db
      - QDRANT_PORT=6333
    networks:
      - devdito_network

networks:
  devdito_network:
    name: devdito_network
```

---

## PHP Implementation

### PipelineOrchestrator.php

```php
<?php
declare(strict_types=1);

namespace dokuwiki\plugin\devdito\lib;

/**
 * PipelineOrchestrator - Executes pipeline stages via Docker
 * 
 * Constitution Article I: No direct PHP→Python calls
 * Constitution Article VII: Thin wrappers only
 */
class PipelineOrchestrator
{
    private const DOCKER_COMPOSE_PATH = '/path/to/backend_services';
    private const STAGES = [
        'fetch' => [
            'container' => 'dev-dito-module-fetcher',
            'name' => 'Wiki Fetcher',
            'description' => 'Fetcht LeoWiki via JSON-RPC API'
        ],
        'evaluate' => [
            'container' => 'dev-dito-module-evaluator',
            'name' => 'Deep Evaluation',
            'description' => 'LLM-gestuetzte Inhaltsanalyse'
        ],
        'embed' => [
            'container' => 'dev-dito-module-embedder',
            'name' => 'Embeddings Creator',
            'description' => 'Generiert Embeddings via OpenAI/lokales Model'
        ],
        'deploy' => [
            'container' => 'dev-dito-module-deployer',
            'name' => 'Qdrant Deploy',
            'description' => 'Laedt Embeddings in Qdrant hoch'
        ]
    ];
    
    /**
     * Start a pipeline stage as background job
     * 
     * @param string $stage Stage ID (fetch, evaluate, embed, deploy)
     * @param array $options Optional parameters
     * @return array{success: bool, job_id: string, message: string}
     */
    public function runStage(string $stage, array $options = []): array
    {
        if (!isset(self::STAGES[$stage])) {
            return ['success' => false, 'job_id' => '', 'message' => "Unknown stage: $stage"];
        }
        
        $jobId = $stage . '_' . date('Ymd_His');
        $container = self::STAGES[$stage]['container'];
        
        // Build docker command
        $cmd = sprintf(
            'docker compose -f %s/docker-compose.yml run --rm -d %s %s 2>&1',
            escapeshellarg(self::DOCKER_COMPOSE_PATH),
            escapeshellarg($container),
            escapeshellarg($jobId)
        );
        
        // Execute in background
        $output = [];
        $returnCode = 0;
        exec($cmd, $output, $returnCode);
        
        if ($returnCode !== 0) {
            return [
                'success' => false,
                'job_id' => $jobId,
                'message' => 'Failed to start container: ' . implode("\n", $output)
            ];
        }
        
        return [
            'success' => true,
            'job_id' => $jobId,
            'message' => self::STAGES[$stage]['name'] . " gestartet. Job-ID: $jobId"
        ];
    }
    
    /**
     * Get status of all pipeline stages
     * 
     * @return array Pipeline status
     */
    public function getStatus(): array
    {
        $statusManager = new JobStatusManager();
        $stages = [];
        
        foreach (self::STAGES as $id => $info) {
            $lastRun = $statusManager->getLastRun($id);
            
            $stages[] = [
                'id' => $id,
                'name' => $info['name'],
                'description' => $info['description'],
                'status' => $lastRun['status'] ?? 'never_run',
                'last_run' => $lastRun['finished_at'] ?? null,
                'duration_seconds' => $lastRun['duration'] ?? null,
                'output_dir' => $lastRun['output_dir'] ?? null,
                'stats' => $lastRun['stats'] ?? null
            ];
        }
        
        return [
            'stages' => $stages,
            'active_job' => $statusManager->getActiveJob(),
            'qdrant_info' => $this->getQdrantInfo()
        ];
    }
    
    /**
     * Get Qdrant collection info
     */
    private function getQdrantInfo(): array
    {
        $qdrantUrl = ConfigLoader::get('SERVICES.qdrant.host', 'qdrant_db');
        $qdrantPort = ConfigLoader::get('SERVICES.qdrant.port', 6333);
        $collection = ConfigLoader::get('SERVICES.qdrant.collection', 'wiki_embeddings');
        
        try {
            $response = file_get_contents(
                "http://$qdrantUrl:$qdrantPort/collections/$collection"
            );
            $data = json_decode($response, true);
            
            return [
                'connected' => true,
                'collection' => $collection,
                'vectors' => $data['result']['points_count'] ?? 0,
                'dimension' => $data['result']['config']['params']['vectors']['size'] ?? 0
            ];
        } catch (\Exception $e) {
            return [
                'connected' => false,
                'collection' => $collection,
                'error' => $e->getMessage()
            ];
        }
    }
}
```

### JobStatusManager.php

```php
<?php
declare(strict_types=1);

namespace dokuwiki\plugin\devdito\lib;

/**
 * JobStatusManager - Reads/writes pipeline_runs.json
 */
class JobStatusManager
{
    private const STATUS_FILE = DOKU_INC . 'data/devdito/logs/pipeline_runs.json';
    
    /**
     * Get all job runs
     */
    public function getAllRuns(): array
    {
        if (!file_exists(self::STATUS_FILE)) {
            return [];
        }
        
        $content = file_get_contents(self::STATUS_FILE);
        return json_decode($content, true) ?: [];
    }
    
    /**
     * Get last run for a specific stage
     */
    public function getLastRun(string $stage): ?array
    {
        $runs = $this->getAllRuns();
        
        // Filter by stage and get latest
        $stageRuns = array_filter($runs, fn($r) => $r['stage'] === $stage);
        usort($stageRuns, fn($a, $b) => ($b['started_at'] ?? '') <=> ($a['started_at'] ?? ''));
        
        return $stageRuns[0] ?? null;
    }
    
    /**
     * Get currently active job (if any)
     */
    public function getActiveJob(): ?array
    {
        $runs = $this->getAllRuns();
        
        foreach ($runs as $run) {
            if ($run['status'] === 'running') {
                return $run;
            }
        }
        
        return null;
    }
    
    /**
     * Get job by ID
     */
    public function getJob(string $jobId): ?array
    {
        $runs = $this->getAllRuns();
        
        foreach ($runs as $run) {
            if ($run['job_id'] === $jobId) {
                return $run;
            }
        }
        
        return null;
    }
}
```

---

## Admin UI Enhancement

### Dashboard Pipeline Card (admin.php addition)

```php
/**
 * Render Pipeline Orchestration Card
 */
private function renderPipelineCard(): void
{
    echo '<div class="devdito-card devdito-pipeline-card">';
    echo '<h2>Pipeline Orchestration</h2>';
    
    echo '<div id="devdito-pipeline-stages">';
    echo '<p class="devdito-loading">Lade Pipeline-Status...</p>';
    echo '</div>';
    
    echo '<script>
        document.addEventListener("DOMContentLoaded", function() {
            DevDitoPipeline.init();
        });
    </script>';
    
    echo '</div>';
}
```

### JavaScript: Pipeline Dashboard (dist/pipeline.js)

```javascript
/**
 * Dev Dito Pipeline Dashboard
 * Handles stage execution and status polling
 */
const DevDitoPipeline = {
    pollInterval: null,
    
    init: function() {
        this.loadStatus();
        this.startPolling();
    },
    
    loadStatus: function() {
        fetch(DOKU_BASE + 'lib/exe/ajax.php?call=devdito_pipeline_status')
            .then(r => r.json())
            .then(data => this.renderStages(data))
            .catch(e => this.renderError(e));
    },
    
    renderStages: function(data) {
        const container = document.getElementById('devdito-pipeline-stages');
        let html = '<div class="devdito-pipeline-grid">';
        
        data.stages.forEach((stage, index) => {
            const statusClass = this.getStatusClass(stage.status);
            const canRun = this.canRunStage(stage, index, data);
            
            html += `
                <div class="devdito-stage-card ${statusClass}">
                    <div class="devdito-stage-header">
                        <span class="devdito-stage-number">${index + 1}</span>
                        <h3>${stage.name}</h3>
                    </div>
                    <p class="devdito-stage-desc">${stage.description}</p>
                    <div class="devdito-stage-status">
                        <span class="devdito-status-badge ${statusClass}">
                            ${this.getStatusLabel(stage.status)}
                        </span>
                        ${stage.last_run ? `<span class="devdito-last-run">
                            Zuletzt: ${new Date(stage.last_run).toLocaleString('de-DE')}
                        </span>` : ''}
                    </div>
                    ${stage.stats ? this.renderStats(stage.stats) : ''}
                    <button 
                        class="devdito-btn devdito-btn-run"
                        ${!canRun ? 'disabled' : ''}
                        onclick="DevDitoPipeline.runStage('${stage.id}')"
                    >
                        ${stage.status === 'running' ? 'Laeuft...' : 'Starten'}
                    </button>
                </div>
            `;
        });
        
        html += '</div>';
        
        // Qdrant Info
        if (data.qdrant_info) {
            html += this.renderQdrantInfo(data.qdrant_info);
        }
        
        container.innerHTML = html;
    },
    
    runStage: function(stageId) {
        fetch(DOKU_BASE + 'lib/exe/ajax.php?call=devdito_run_stage', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ stage: stageId })
        })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                alert(data.message);
                this.loadStatus();
            } else {
                alert('Fehler: ' + data.message);
            }
        });
    },
    
    startPolling: function() {
        this.pollInterval = setInterval(() => this.loadStatus(), 5000);
    },
    
    getStatusClass: function(status) {
        return {
            'success': 'status-success',
            'error': 'status-error',
            'running': 'status-running',
            'never_run': 'status-pending'
        }[status] || 'status-pending';
    },
    
    getStatusLabel: function(status) {
        return {
            'success': 'Erfolgreich',
            'error': 'Fehler',
            'running': 'Laeuft...',
            'never_run': 'Nie ausgefuehrt'
        }[status] || status;
    },
    
    canRunStage: function(stage, index, data) {
        // Can't run if already running
        if (data.active_job) return false;
        
        // Fetch can always run
        if (stage.id === 'fetch') return true;
        
        // Other stages need previous stage to be successful
        const prevStage = data.stages[index - 1];
        return prevStage && prevStage.status === 'success';
    },
    
    renderStats: function(stats) {
        let html = '<div class="devdito-stage-stats">';
        for (const [key, value] of Object.entries(stats)) {
            html += `<span><strong>${key}:</strong> ${value}</span>`;
        }
        html += '</div>';
        return html;
    },
    
    renderQdrantInfo: function(info) {
        return `
            <div class="devdito-qdrant-info">
                <h3>Qdrant Collection</h3>
                <p>
                    <span class="${info.connected ? 'status-success' : 'status-error'}">
                        ${info.connected ? '● Verbunden' : '● Nicht verbunden'}
                    </span>
                </p>
                ${info.connected ? `
                    <p><strong>Collection:</strong> ${info.collection}</p>
                    <p><strong>Vectors:</strong> ${info.vectors.toLocaleString()}</p>
                    <p><strong>Dimension:</strong> ${info.dimension}</p>
                ` : `<p class="error">${info.error}</p>`}
            </div>
        `;
    },
    
    renderError: function(error) {
        document.getElementById('devdito-pipeline-stages').innerHTML = 
            `<p class="devdito-error">Fehler beim Laden: ${error.message}</p>`;
    }
};
```

---

## File Structure (New/Modified)

```
dev_dito/
├── backend_services/
│   ├── docker-compose.yml          # MODIFIED: Add pipeline modules
│   ├── module_fetcher/             # NEW
│   │   ├── Dockerfile
│   │   ├── entrypoint.py
│   │   └── requirements.txt
│   ├── module_evaluator/           # NEW
│   │   ├── Dockerfile
│   │   ├── entrypoint.py
│   │   └── requirements.txt
│   ├── module_embedder/            # NEW
│   │   ├── Dockerfile
│   │   ├── entrypoint.py
│   │   └── requirements.txt
│   └── module_deployer/            # NEW
│       ├── Dockerfile
│       ├── entrypoint.py
│       └── requirements.txt
├── data/
│   ├── fetched/                    # Stage 1 output
│   ├── evaluated/                  # Stage 2 output
│   ├── embeddings/                 # Stage 3 output
│   └── logs/
│       └── pipeline_runs.json      # NEW: Job status tracking
├── dokuwiki_plugin/
│   ├── action.php                  # MODIFIED: Add AJAX handlers
│   ├── admin.php                   # MODIFIED: Add pipeline card
│   ├── dist/
│   │   └── pipeline.js             # NEW: Pipeline dashboard JS
│   └── lib/
│       ├── ConfigLoader.php        # EXISTS
│       ├── PipelineOrchestrator.php # NEW
│       └── JobStatusManager.php     # NEW
└── config/
    └── env.yaml                    # EXISTS (already centralized)
```

---

## Security Considerations

| Concern | Mitigation |
|---------|------------|
| Docker Socket Access | Wiki container hat keinen Docker-Socket-Zugriff; Orchestration via separates Skript oder API |
| API Key Exposure | Secrets nur in Container-Env, nie in Browser-JS |
| Command Injection | Alle User-Inputs werden escaped (`escapeshellarg`) |
| Admin-Only Access | DokuWiki ACL check vor jeder Pipeline-Operation |
| Log Sanitization | Secrets werden aus Logs maskiert |

**Alternative zu `docker exec` vom Wiki-Container:**

Falls der Wiki-Container keinen Docker-Zugriff haben soll (Prompt.md Constraint):
1. **Option A**: REST-API auf jedem Modul-Container (Port 3001-3004)
2. **Option B**: Orchestrator-Service (z.B. `dev-dito-orchestrator`) mit Docker-Zugriff
3. **Option C**: Lokale Python-Execution als Fallback (FR-308)

**Empfehlung**: Option B - separater Orchestrator-Container mit Docker-Socket

---

## Deployment Steps

### Phase 1: Module Container Setup

1. Erstelle `backend_services/module_fetcher/`
2. Erstelle `backend_services/module_evaluator/`
3. Erstelle `backend_services/module_embedder/`
4. Erstelle `backend_services/module_deployer/`
5. Erweitere `docker-compose.yml`
6. Teste Container einzeln: `docker compose run module_fetcher test_job`

### Phase 2: PHP Integration

1. Erstelle `lib/PipelineOrchestrator.php`
2. Erstelle `lib/JobStatusManager.php`
3. Erweitere `action.php` um AJAX-Handler
4. Teste: `/lib/exe/ajax.php?call=devdito_pipeline_status`

### Phase 3: Dashboard UI

1. Erstelle `dist/pipeline.js`
2. Erweitere `admin.php` um Pipeline-Card
3. Teste: `?do=admin&page=devdito`
4. Teste kompletten Flow: Fetch → Validate → Status-Update

### Phase 4: Integration Tests

1. Full Pipeline Run (Fetch → Deploy)
2. Error Handling (Network-Fehler, Timeout)
3. Concurrent Job Prevention
4. Qdrant Collection Verification

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Docker-Zugriff aus Wiki-Container | Medium | High | Orchestrator-Container oder lokaler Fallback |
| Lange Laufzeiten blockieren UI | Low | Medium | Background-Jobs + Polling implementiert |
| Incomplete Fetch/Embed | Medium | Medium | Status tracking + Resume-Funktion |
| Config-Desync | Low | Medium | Zentrale env.yaml + settings.json Sync |

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Fetch via Dashboard | 100% funktional | Manueller Test |
| Status-Update Latency | < 1s | Polling-Intervall |
| Background-Job Reliability | > 95% | 20 Test-Runs |
| Config-Zentralisierung | 100% | Code-Review |

---

## References

- [DokuWiki AJAX Development](https://www.dokuwiki.org/devel:ajax)
- [Docker Compose Profiles](https://docs.docker.com/compose/profiles/)
- [Qdrant REST API](https://qdrant.tech/documentation/interfaces/#rest-api)
- [sources_dev_dito.yaml](D:/_Repositories/00_Die_Bibliothek/Prompts/sources_dev_dito.yaml)
- [Prompt.md Stack-G](/path/to/legacy-stack/_ENTERPRISE__PLAN_/Prompt.md)
