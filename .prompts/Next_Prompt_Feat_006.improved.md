# Dev Dito - Feature 006: Simplified Installation

<context>
You are a senior DevOps and DokuWiki developer working on the Dev Dito project.
Dev Dito is a DokuWiki extension that provides RAG-powered semantic search over wiki content.
It runs as a multi-stack Docker ecosystem on Windows with Docker Desktop.

Your task: Implement the installation script and related infrastructure described in the user stories below.
Output: Working PowerShell script(s) and any required configuration changes.
Language: English for code and comments. German only where explicitly marked.
</context>

---

## Current Environment

<environment>
<installed_stacks>
- stack-h-mcp
- stack-g-devdito
- stack-d-ai-core
- stack-b-wiki-core
- stack-a-wiki-sandbox
</installed_stacks>

<legacy_stack_path>D:/_Repositories/year_2025_26/SYP_2025_26/leonie/internal_leonidas/stacks</legacy_stack_path>

<running_containers>

| Stack Name           | Service Name              | Image                                 | Port(s)        |
| -------------------- | ------------------------- | ------------------------------------- | -------------- |
| stack-h-mcp          | semantic-search-wiki-core | stack-h-mcp-semantic-search-wiki-core | 3000:3000      |
| stack-g-devdito      | dev-dito-wiki             | linuxserver/dokuwiki:latest           | 8080:80        |
| stack-g-devdito      | dev-dito-orchestrator     | stack-g-devdito-orchestrator          | 8089:8089      |
| stack-d-ai-core      | qdrant-main-vector-db     | qdrant/qdrant:v1.13.2                 | 6333:6333      |
| stack-d-ai-core      | qdrant-init               | stack-d-ai-core-qdrant-init           | -              |
| stack-b-wiki-core    | keycloak-server           | keycloak/keycloak:25.0                | 8081:8080      |
| stack-a-wiki-sandbox | wiki-sandbox              | linuxserver/dokuwiki:latest           | 8090:80        |

</running_containers>
</environment>

---

## Architecture

### Design Principle: Stack Orchestration from Within

Dev Dito operates as a **central orchestrator** within the multi-stack Docker ecosystem:

> Dev Dito MUST discover, connect to, and manage dependent Docker stacks from within
> its own containerized environment - without Docker-in-Docker or direct Docker socket access.

<constraints>
1. All required stacks (A through I) must be pre-installed on the host before Dev Dito can orchestrate them
2. Stack management happens via HTTP APIs over the shared `leonidas-network`, not via Docker commands
3. Service discovery uses network probing and health endpoints
4. Missing stacks result in reduced functionality, not installation failure
</constraints>

### Multi-Stack Ecosystem

```
                    SHARED DOCKER NETWORK: leonidas-network
    ┌──────────────────────────────────────────────────────────────────────┐
    │                                                                      │
    │   INFRASTRUCTURE LAYER                                               │
    │   ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐  │
    │   │ Stack-A         │  │ Stack-B         │  │ Stack-C             │  │
    │   │ wiki-sandbox    │  │ wiki-core       │  │ extensions-extra    │  │
    │   │ Port: 8090      │  │ Port: 8081      │  │ (reserved)          │  │
    │   └─────────────────┘  └─────────────────┘  └─────────────────────┘  │
    │                                                                      │
    │   AI & DATA LAYER                                                    │
    │   ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐  │
    │   │ Stack-D         │  │ Stack-E         │  │ Stack-F             │  │
    │   │ ai-core         │  │ ai-evaluation   │  │ observability       │  │
    │   │ Port: 6333      │  │ (reserved)      │  │ (reserved)          │  │
    │   └────────┬────────┘  └─────────────────┘  └─────────────────────┘  │
    │            │ uses Qdrant                                             │
    │            ▼                                                         │
    │   ┌───────────────────────────────────────────────────────────────┐  │
    │   │ Stack-G: DEV DITO (THIS PROJECT)                              │  │
    │   │ ┌─────────────────┐  ┌──────────────────────────────────────┐ │  │
    │   │ │ dev-dito-wiki   │  │ dev-dito-orchestrator                │ │  │
    │   │ │ Port: 8080      │  │ Port: 8089                           │ │  │
    │   │ └─────────────────┘  └──────────────────────────────────────┘ │  │
    │   └───────────────────────────────────────────────────────────────┘  │
    │            │ provides MCP tools                                      │
    │            ▼                                                         │
    │   ┌─────────────────┐  ┌─────────────────────────────────────────┐   │
    │   │ Stack-H         │  │ Stack-I                                 │   │
    │   │ mcp-servers     │  │ leonidas-services                       │   │
    │   │ Port: 3000      │  │ (AI Chat Frontend)                      │   │
    │   └─────────────────┘  └─────────────────────────────────────────┘   │
    │                                                                      │
    └──────────────────────────────────────────────────────────────────────┘
```

### Stack Dependency Matrix

| Stack                   | Depends On       | Provides To                  | Requirement  |
| ----------------------- | ---------------- | ---------------------------- | ------------ |
| Stack-A (wiki-sandbox)  | -                | Stack-G (test target)        | OPTIONAL     |
| Stack-B (wiki-core)     | -                | Stack-G (auth)               | RECOMMENDED  |
| Stack-C (extensions)    | Stack-B          | -                            | OPTIONAL     |
| Stack-D (ai-core)       | -                | Stack-G, Stack-H (vector DB) | **REQUIRED** |
| Stack-E (ai-eval)       | Stack-D          | Stack-G (metrics)            | OPTIONAL     |
| Stack-F (observability) | -                | All stacks (monitoring)      | OPTIONAL     |
| Stack-G (dev-dito)      | Stack-D          | Stack-H (MCP tools)          | **CORE**     |
| Stack-H (mcp)           | Stack-D, Stack-G | Stack-I (AI tools)           | RECOMMENDED  |
| Stack-I (leonidas)      | Stack-H          | End users                    | OPTIONAL     |

### Network Configuration

All stacks communicate over a shared external Docker network:

```yaml
# Required in every docker-compose.yml
networks:
  leonidas-network:
    external: true

# Create once before any stack starts:
# docker network create --driver bridge --attachable leonidas-network
```

### Port Allocation Map

| Port | Stack   | Service                   | Protocol  |
| ---- | ------- | ------------------------- | --------- |
| 3000 | Stack-H | semantic-search-wiki-core | HTTP/MCP  |
| 5000 | Stack-E | mlflow-server             | HTTP      |
| 6333 | Stack-D | qdrant-main-vector-db     | HTTP      |
| 6334 | Stack-D | qdrant-main-vector-db     | gRPC      |
| 6334 | Stack-G | dev-dito-qdrant (local)   | HTTP      |
| 6335 | Stack-G | dev-dito-qdrant (local)   | gRPC      |
| 8080 | Stack-G | dev-dito-wiki             | HTTP      |
| 8081 | Stack-B | keycloak-server           | HTTP      |
| 8089 | Stack-G | dev-dito-orchestrator     | HTTP      |
| 8090 | Stack-A | wiki-sandbox              | HTTP      |
| 9090 | Stack-F | prometheus                | HTTP      |

### Orchestrator API

<api base_url="http://localhost:8089">

| Method | Path              | Description                                   |
| ------ | ----------------- | --------------------------------------------- |
| GET    | /health           | Health check - returns `{status: "ok"}`        |
| GET    | /status           | Pipeline status - all stages with last run info |
| POST   | /run/fetch        | Start wiki fetch (full or incremental)         |
| POST   | /run/evaluate     | Start content evaluation                       |
| POST   | /run/preprocess   | Start RAG preprocessing                        |
| POST   | /run/embed        | Start embedding generation                     |
| POST   | /run/deploy       | Start Qdrant deployment                        |
| GET    | /job/{job_id}     | Get job status by ID                           |
| GET    | /progress         | Current job progress (live)                    |
| GET    | /progress/{job_id}| Progress for specific job                      |
| POST   | /cancel/{job_id}  | Cancel running job                             |

</api>

---

## User Stories

### US-001: Easy Installation of Dev Dito (Developer Setup)

**As** a Dev Dito developer,
**I want** to install Dev Dito on my local machine by cloning the repo and running one script,
**so that** I can start developing and testing immediately.

<instructions>

#### Installation Command

```powershell
git clone https://github.com/IxI-Enki/dev_dito.git
cd dev_dito
.\install.ps1 -FindPathToWiki
```

#### Script Parameters

| Parameter | Alias | Default | Description |
| --------- | ----- | ------- | ----------- |
| `-FindPathToWiki` | `-fpi` | `$true` | Auto-discover running DokuWiki instances (Docker and local) |
| `-PathToWiki` | `-ptw` | `$null` | Manual path to DokuWiki instance root |
| `-PathToConfig` | `-ptc` | `$null` | Manual path to Dev Dito config directory |
| `-Help` | `-h` | - | Show help with usage examples and exit |
| `-Force` | `-f` | `$false` | Skip all confirmations, use defaults |
| `-Quiet` | `-q` | `$false` | Suppress output except errors/warnings (for CI pipelines) |
| `-UpdateExisting` | `-u` | `$false` | Update existing installation, preserve fetched/embedded data, reset caches |

#### Installation Steps

The script performs these steps in order:

1. **Check prerequisites**
   - Verify Python 3.10+ installed
   - Verify Docker Desktop installed and running
   - If not installed: offer to install or provide links, then exit
   - If Docker not running: start Docker Desktop and wait for readiness

2. **Configure network**
   - Check if `leonidas-network` exists
   - If not: create it (`docker network create --driver bridge --attachable leonidas-network`)
   - If exists: verify connectivity

3. **Detect existing stacks**
   - Check for: stack-a-wiki-sandbox, stack-b-wiki-core, stack-d-ai-core, stack-g-devdito, stack-h-mcp
   - Report status of each (running / stopped / not found)

4. **Backup and migrate** (if updating)
   - Backup `data/fetched/`, `data/evaluated/`, `data/embeddings/`, `data/preprocessed/` to temp dir
   - Remove old Dev Dito extension from DokuWiki instance(s)
   - Deploy latest extension
   - Restore backed-up data

5. **Discover external DokuWiki instances**
   - If `-FindPathToWiki` is `$true`: scan Docker containers and local paths for DokuWiki instances
   - Offer to install Dev Dito plugin into discovered instances (user confirms each with y/n)

6. **Build Docker images**
   ```powershell
   docker compose -f backend_services/docker-compose.yml -p stack-g-devdito build
   ```
   - Builds: orchestrator, module_fetcher, module_evaluator, module_preprocessor, module_embedder, module_deployer

7. **Start Stack-G services**
   ```powershell
   docker compose -f backend_services/docker-compose.yml -p stack-g-devdito up -d
   ```
   - Starts: dev-dito-wiki (port 8080), dev-dito-orchestrator (port 8089), dev-dito-qdrant (port 6334)
   - Connects to: stack-d-ai-core (Qdrant on 6333), stack-h-mcp (MCP on 3000) via leonidas-network

8. **Deploy DokuWiki plugin**
   - Wait for dev-dito-wiki container to be healthy
   - Copy `dokuwiki_plugin/` contents to container path `lib/plugins/devdito/`
   - Set file permissions
   - Activate plugin

9. **Health check**
   - Verify: `http://localhost:8089/health` (orchestrator)
   - Verify: `http://localhost:8080` (DokuWiki)
   - Check connectivity to Qdrant (stack-d-ai-core)
   - Check connectivity to MCP server (stack-h-mcp)
   - List all running Dev Dito containers with status

10. **Validate configuration**
    - Check `config/env.yaml` exists and is parseable
    - Check `config/sources.yaml` for wiki source definitions
    - Verify `config/secrets/` contains required tokens

11. **Display success summary**
    - DokuWiki: `http://localhost:8080`
    - Admin Panel: `http://localhost:8080/?do=admin&page=devdito`
    - Orchestrator API: `http://localhost:8089/health`
    - Useful management commands
    - Log installation to `data/logs/`

</instructions>

<constraints>
- Destructive actions require user confirmation (y/n) unless `-Force` is set
- All actions are logged to `data/logs/install.log`
- Errors are handled gracefully with clear messages and recovery suggestions
- Script is idempotent: running it twice produces the same result
</constraints>

<example>
**Successful first-time install:**
```
PS> .\install.ps1

[CHECK] Python 3.13.1 ... OK
[CHECK] Docker Desktop ... running
[CHECK] Network leonidas-network ... created
[CHECK] stack-d-ai-core ... running (Qdrant v1.13.2 on :6333)
[CHECK] stack-g-devdito ... not found
[BUILD] Building Dev Dito images ... done
[START] Starting stack-g-devdito ... done
[DEPLOY] Installing plugin to dev-dito-wiki ... done
[HEALTH] Orchestrator API ... OK
[HEALTH] DokuWiki ... OK
[HEALTH] Qdrant connection ... OK

Dev Dito installed successfully!
  DokuWiki:      http://localhost:8080
  Admin Panel:   http://localhost:8080/?do=admin&page=devdito
  Orchestrator:  http://localhost:8089
```
</example>

<example>
**Docker not running:**
```
PS> .\install.ps1

[CHECK] Python 3.13.1 ... OK
[CHECK] Docker Desktop ... not running
  [?] Start Docker Desktop now? (y/n): y
  [WAIT] Starting Docker Desktop ... ready (32s)
[CHECK] Network leonidas-network ... exists
...
```
</example>

---

### US-002: Easy Installation of Dev Dito (Wiki Admin)

<!-- TODO: Define user story for wiki administrators who want to add Dev Dito
     to an existing DokuWiki installation without the full development stack. -->

---

## Reference: Repository Structure

```
dev_dito/
├── backend_services/
│   ├── module_deployer/         # Dockerfile + entrypoint for deploy stage
│   ├── module_embedder/         # Dockerfile + entrypoint for embed stage
│   ├── module_evaluator/        # Dockerfile + entrypoint for evaluate stage
│   ├── module_fetcher/          # Dockerfile + entrypoint for fetch stage
│   ├── module_preprocessor/     # Dockerfile + entrypoint for preprocess stage
│   ├── orchestrator/            # Dockerfile + server.py (FastAPI)
│   ├── qdrant_db/               # Dockerfile + init_collection.py
│   ├── wiki_dev_mcp_server/     # Dockerfile + server.py (MCP server)
│   ├── docker-compose.yml       # Main compose file for stack-g-devdito
│   └── Dockerfile.module.template
│
├── config/
│   ├── secrets/                 # API tokens, SSL certs (.gitignored)
│   ├── env.yaml                 # Main configuration
│   ├── env.development.yaml     # Development overrides
│   ├── env.minimal.yaml         # Minimal configuration
│   ├── PLACEHOLDER_env.yaml     # Template for new setups
│   └── sources.yaml             # Wiki source definitions
│
├── data/
│   ├── fetched/                 # fetched_at_YYYYMMDD_HHMMSS/
│   ├── evaluated/               # evaluation_fetched_at_YYYYMMDD_HHMMSS/
│   ├── preprocessed/            # preprocess_at_YYYYMMDD_HHMMSS/
│   ├── embeddings/              # Generated embeddings
│   └── logs/                    # Pipeline logs and status files
│
├── dokuwiki_plugin/
│   ├── conf/                    # default.php, metadata.php
│   ├── dist/                    # Compiled CSS/JS
│   ├── lang/de/                 # German translations
│   ├── lang/en/                 # English translations
│   ├── lib/                     # ConfigLoader, JobStatusManager, PipelineOrchestrator
│   ├── action.php               # Event hooks and AJAX handlers
│   ├── admin.php                # Admin page controller
│   └── plugin.info.txt          # Plugin metadata
│
├── pipeline/
│   ├── 01_wiki_fetcher/         # Wiki content fetching scripts
│   ├── 02_deep_evaluation/      # Content quality analysis
│   ├── 03_embeddings_creator/   # Vector embedding generation
│   ├── 03_rag_preprocessing/    # DokuWiki-to-Markdown conversion
│   ├── 03b_preprocessing_eval/  # Preprocessing quality checks
│   └── 04_deploy/               # Qdrant deployment scripts
│
├── scripts/
│   ├── deploy-plugin.ps1        # Plugin deployment helper
│   ├── docker_manager.ps1       # Docker stack management
│   ├── migration.ps1            # Data migration utilities
│   └── network_setup.ps1        # Network configuration
│
├── docs/                        # Architecture documentation
├── specs/                       # Specifications
├── planning/                    # Planning documents
├── config.py                    # Shared Python config
├── install.ps1                  # Installation script (THIS USER STORY)
├── Prompt.md                    # Project constitution
├── README.md                    # Project README
├── README_ARCHITECTURE.md       # Architecture documentation
└── sources_dev_dito.yaml        # Wiki source list
```
