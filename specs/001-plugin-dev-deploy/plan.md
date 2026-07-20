# Implementation Plan: DokuWiki Plugin Dev Dito - Development & Deployment

**Branch**: `001-plugin-dev-deploy` | **Date**: 2026-01-31 | **Spec**: [spec.md](./spec.md)  
**Input**: Feature specification from `/specs/001-plugin-dev-deploy/spec.md`

## Summary

Dev Dito ist eine DokuWiki Extension die als **Service Gateway** (HTTP-Client) zu externen
AI-Services fungiert. Das Plugin **verbindet sich mit** MCP Server (Stack-H), Qdrant (Stack-D)
und LLM Services - es **enthaelt diese nicht**. Dieses Feature etabliert:

1. **Zentrale Konfiguration** - EINE `config/env.yaml` fuer ALLE Komponenten
2. **Development-Infrastruktur** - Deployment vom Source zum Test-Wiki
3. **Wiki Fetcher Integration** - JSON-RPC API zum Quell-Wiki

**Architektur-Klarstellung (Constitution v1.2.0):**
- Dev Dito Plugin = HTTP-Client zu externen Services
- MCP Server = Separater Stack-H (nicht Teil von Dev Dito)
- **ALLE Konfiguration** in zentraler `config/env.yaml` (Article II-B)
- **KEINE hardcodierten Variablen** im Code

**Kernkomponenten:**
1. **Zentrale Config** - `config/env.yaml` + `config.py` Loader
2. PowerShell Deploy-Script mit PHP Syntax-Validierung
3. DokuWiki-konforme Plugin-Struktur (Action + Admin Plugin)
4. Wiki Fetcher mit JSON-RPC API Authentifizierung

## Technical Context

**Language/Version**: PHP 8.1+ (DokuWiki), PowerShell 7+ (Scripts)  
**Primary Dependencies**: DokuWiki Core APIs (`dokuwiki\Extension\*`)  
**Storage**: Dateisystem (keine Datenbank fuer Plugin selbst)  
**Testing**: Manuell im Browser + `php -l` Syntax-Check  
**Target Platform**: Windows 11 (Dev), Linux Docker Container (Prod)  
**Project Type**: DokuWiki Plugin (single project)  
**Performance Goals**: Deploy < 5 Sekunden, Plugin-Load < 100ms  
**Constraints**: Keine NPM/Composer Dependencies, nur PHP CLI + PowerShell

## Constitution Check

*GATE: Validated against `.specify/memory/constitution.md` (v1.2.0)*

| Article                             | Requirement                                                     | Status                                                         |
| ----------------------------------- | --------------------------------------------------------------- | -------------------------------------------------------------- |
| **I: Layered Module Architecture**  | DokuWiki Plugin kommuniziert nur via HTTP mit externen Services | ✅ Plugin ist HTTP-Client zu MCP (Stack-H), Qdrant (Stack-D)   |
| **II: JSON Interface Standard**     | JSON-RPC 2.0 fuer externe Service-Kommunikation                 | ✅ Implementiert in `action.php` (Client-seitig)               |
| **II-B: Centralized YAML Config**   | ALLE Config in `config/env.yaml`, KEINE hardcodierten Werte     | 🔧 ZU IMPLEMENTIEREN                                           |
| **IV: Language Standards**          | PHP PSR-12, `declare(strict_types=1)`                           | ✅ Alle PHP-Dateien konform                                    |
| **V: Pragmatic Documentation**      | README fuer Scripts, PLACEHOLDER_env.yaml als Template          | 🔧 ZU IMPLEMENTIEREN                                           |
| **VI: Secret Containment**          | Secrets in separaten Dateien, nicht in YAML                     | 🔧 ZU IMPLEMENTIEREN                                           |
| **VII: Integration Simplicity**     | Thin Wrapper, keine eigene Abstraktionen                        | ✅ Direkte DokuWiki API Nutzung                                |
| **VIII: Direct Framework Usage**    | DokuWiki APIs direkt nutzen                                     | ✅ `ActionPlugin`, `AdminPlugin` extends                       |

**Scope-Compliance (Constitution v1.2.0):**
- ✅ Plugin ist HTTP-Client (Service Gateway)
- ✅ MCP Server ist OUT OF SCOPE (gehoert zu Stack-H)
- ✅ Pipeline-Integration ist IN SCOPE (Admin-Interface zur Steuerung)
- 🔧 Zentrale Config ist IN SCOPE und MUSS implementiert werden

**Workflow Gates (aus Constitution):**

- [x] Mindestens eine User Story mit Akzeptanzkriterien ✅
- [x] Betroffene Schicht identifiziert: PHP Plugin Layer ✅
- [x] Docker-Services: Keine Aenderungen noetig ✅
- [x] Bestehende Pipeline-Skripte: Unveraendert ✅

## Project Structure

### Documentation (this feature)

```tree
specs/001-plugin-dev-deploy/
├── spec.md              # Feature-Spezifikation ✅
├── plan.md              # Dieser Plan ✅
└── tasks.md             # Phase 2 output (naechster Schritt)
```

### Source Code (repository root)

```tree
dev_dito/
│
├── config/                             # ★ ZENTRALE KONFIGURATION ★
│   ├── env.yaml                        # MASTER CONFIG (gitignored) 🔧
│   ├── PLACEHOLDER_env.yaml            # Template mit Dokumentation 🔧
│   ├── settings.json                   # Auto-generiert fuer PHP 🔧
│   └── secrets/                        # Alle Secrets (gitignored) 🔧
│       ├── json_rpc_api.token          # Wiki JSON-RPC API Key
│       ├── ssl.cert                    # SSL Zertifikat
│       └── openai.token                # OpenAI API Key
│
├── config.py                           # ★ ROOT-LEVEL CONFIG LOADER ★ 🔧
│                                       # Laedt env.yaml, generiert settings.json
│
├── dokuwiki_plugin/                    # Plugin Source
│   ├── plugin.info.txt                 # Plugin-Metadaten
│   ├── action.php                      # Action Plugin (742 LOC)
│   ├── admin.php                       # Admin Plugin (463 LOC)
│   ├── lib/
│   │   └── ConfigLoader.php            # Liest config/settings.json 🔧
│   ├── conf/
│   │   ├── default.php                 # DokuWiki UI-Settings only
│   │   └── metadata.php                # Schema fuer UI-Settings
│   ├── lang/                           # Sprachdateien
│   ├── dist/                           # Kompilierte Assets
│   └── logo.png                        # Plugin-Logo
│
├── pipeline/                           # Pipeline-Module
│   ├── 01_wiki_fetcher/                # Importiert: from config import ...
│   ├── 02_deep_evaluation/             # Importiert: from config import ...
│   ├── 03_embeddings_creator/          # Importiert: from config import ...
│   └── 04_deploy/                      # Importiert: from config import ...
│
├── scripts/                            # Development Scripts
│   ├── deploy-plugin.ps1               # Deploy zum Test-Wiki ✅
│   └── README.md                       # Script-Dokumentation ✅
│
└── [Target Wiki - NICHT im Repo]
    C:\path\to\legacy-stack\
    └── development\first_own_dokuwiki\
        └── plugins_dev\devdito\        # Deployment-Ziel
```

**Legende**: ✅ = existiert, 🔧 = muss erstellt werden

**Structure Decision**: Single DokuWiki Plugin mit zwei Plugin-Typen (Action + Admin).
Zentrale Config fuer ALLE Komponenten (Plugin + Pipeline).

## Component Architecture

### Plugin-Komponenten Diagramm

```sketch
┌───────────────────────────────────────────────────────────────────┐
│                        DokuWiki Core                              │
│  ┌─────────────┐  ┌─────────────────┐  ┌────────────────────────┐ │
│  │ EventSystem │  │ Extension Mgr   │  │ Configuration Manager  │ │
│  └──────┬──────┘  └────────┬────────┘  └───────────┬────────────┘ │
└─────────┼──────────────────┼──────────────────────┬┼──────────────┘
          │                  │                      ││
          │ register hooks   │ load plugins         ││ getConf()
          ▼                  ▼                      ▼│
┌────────────────────────────────────────────────────┼──────────────┐
│                  devdito Plugin (Stack-G)          │              │
│  ┌────────────────────────────────────────────────┐│              │
│  │               action.php                       ││              │
│  │  ┌──────────────────┐  ┌─────────────────────┐ ││              │
│  │  │ TPL_METAHEADER   │  │ AJAX_CALL_UNKNOWN   │ ││              │
│  │  │ → Load CSS/JS    │  │ → devdito_search    │ ││              │
│  │  │                  │  │ → devdito_ping      │ ││              │
│  │  └──────────────────┘  └──────────┬──────────┘ ││              │
│  │  ┌──────────────────┐             │            ││              │
│  │  │ TPL_ACT_RENDER   │             │ HTTP       ││              │
│  │  │ → Inject Panel   │             │ (Client)   ││              │
│  │  │ → Toggle Button  │             ▼            ││              │
│  │  └──────────────────┘                          ││              │
│  └────────────────────────────────────────────────┘│              │
│  ┌────────────────────────────────────────────────┐│              │
│  │               admin.php                        ││              │
│  │  ┌──────────────────────────────────────────┐  ││              │
│  │  │ Admin Dashboard (Service Gateway)        │  ││              │
│  │  │ ┌────────────┐ ┌────────────┐ ┌────────┐ │  ││              │
│  │  │ │MCP Status  │ │Qdrant Stat │ │DokuWiki│ │◄─┼┘ Config       │
│  │  │ │[Test]      │ │[Test]      │ │Running │ │  │               │
│  │  │ └────────────┘ └────────────┘ └────────┘ │  │               │
│  │  │ ┌──────────────────────────────────────┐ │  │               │
│  │  │ │ Configuration Table                  │ │  │               │
│  │  │ │ - devdito_enabled: on/off            │ │  │               │
│  │  │ │ - devdito_mcp_url: string            │ │  │               │
│  │  │ │ - devdito_panel_position: left/right │ │  │               │
│  │  │ └──────────────────────────────────────┘ │  │               │
│  │  └──────────────────────────────────────────┘  │               │
│  └────────────────────────────────────────────────┘               │
│  ┌────────────┐  ┌────────────┐  ┌────────────────┐               │
│  │ conf/      │  │ lang/      │  │ dist/          │               │
│  │ default    │  │ de/en      │  │ .min.css/.js   │               │
│  └────────────┘  └────────────┘  └────────────────┘               │
└───────────────────────────────────────────────────────────────────┘
                              │
                              │ HTTP Requests (file_get_contents)
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    EXTERNE SERVICES (nicht Teil von Dev Dito)       │
│  ┌─────────────────────┐  ┌─────────────────────┐                   │
│  │ MCP Server          │  │ Qdrant              │                   │
│  │ (Stack-H)           │  │ (Stack-D)           │                   │
│  │ Port 3000           │  │ Port 6333           │                   │
│  │ → semantic_search   │  │ → Health Check      │                   │
│  │ → ping              │  │ → Collection Info   │                   │
│  └─────────────────────┘  └─────────────────────┘                   │
└─────────────────────────────────────────────────────────────────────┘
```

### Deployment-Flow

```sketch
┌─────────────────────────────────────────────────────────┐
│                    deploy-plugin.ps1                    │
└─────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│ 1. Validate   │    │ 2. PHP Lint   │    │ 3. Copy Files │
│ Required Files│    │ php -l *.php  │    │ to Target     │
└───────┬───────┘    └───────┬───────┘    └───────┬───────┘
        │ FAIL               │ FAIL               │
        └────────► EXIT 1 ◄──┘                    │
                                                  ▼
                                         ┌───────────────┐
                                         │ 4. Verify     │
                                         │ Count & Size  │
                                         └───────┬───────┘
                                                 │
                                                 ▼
                                         ┌───────────────┐
                                         │ 5. Report     │
                                         │ Version Info  │
                                         └───────────────┘
```

### Zentrale Config-Architektur (Constitution Article II-B)

```sketch
┌─────────────────────────────────────────────────────────────────────────────┐
│                         config/env.yaml (MASTER)                            │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ APP:                                                                    │ │
│  │   name: dev_dito                                                       │ │
│  │   version: "0.1.0"                                                     │ │
│  │                                                                        │ │
│  │ PATHS:                                                                 │ │
│  │   root_dir: D:/_Repositories/_Diploma_Thesis_Repositories/dev_dito    │ │
│  │   config_dir: ${root_dir}/config                                      │ │
│  │   secrets_dir: ${config_dir}/secrets                                  │ │
│  │                                                                        │ │
│  │ SOURCE_WIKI:                           # JSON-RPC API zum Schul-Wiki  │ │
│  │   api:                                                                 │ │
│  │     url: https://leowiki.htl-leonding.ac.at/lib/exe/jsonrpc.php       │ │
│  │   authentication:                                                      │ │
│  │     token_file: ${secrets_dir}/json_rpc_api.token  ← Separate Datei   │ │
│  │   certificate: ${secrets_dir}/ssl.cert             ← Separate Datei   │ │
│  │                                                                        │ │
│  │ SERVICES:                              # Externe Service-Verbindungen │ │
│  │   mcp_server:                                                          │ │
│  │     url: http://wiki_dev_mcp_server:3000                              │ │
│  │   qdrant:                                                              │ │
│  │     host: qdrant_db                                                   │ │
│  │     port: 6333                                                        │ │
│  │                                                                        │ │
│  │ PIPELINE:                              # Fetcher/Embedder Settings    │ │
│  │   fetcher:                                                             │ │
│  │     timeout: 30                                                       │ │
│  │     exclude_namespaces: [playground, wiki]                            │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ Wird geladen von
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            config.py (Root-Level)                           │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │ def load_config():                                                      │ │
│  │     # 1. Load env.yaml                                                 │ │
│  │     # 2. Resolve ${var} placeholders                                   │ │
│  │     # 3. Load secrets from files                                       │ │
│  │     # 4. Generate settings.json for PHP                                │ │
│  │     return config                                                      │ │
│  │                                                                        │ │
│  │ # Typisierte Exports                                                   │ │
│  │ SOURCE_WIKI_URL = settings["SOURCE_WIKI"]["api"]["url"]                │ │
│  │ MCP_SERVER_URL = settings["SERVICES"]["mcp_server"]["url"]             │ │
│  │ QDRANT_HOST = settings["SERVICES"]["qdrant"]["host"]                   │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
          │                                           │
          │ Python Import                             │ Auto-generiert
          ▼                                           ▼
┌─────────────────────────┐              ┌─────────────────────────────────────┐
│   Pipeline-Module       │              │   config/settings.json              │
│ ┌─────────────────────┐ │              │ ┌─────────────────────────────────┐ │
│ │ from config import  │ │              │ │ {                               │ │
│ │   SOURCE_WIKI_URL,  │ │              │ │   "SERVICES": {                 │ │
│ │   QDRANT_HOST       │ │              │ │     "mcp_server": {             │ │
│ └─────────────────────┘ │              │ │       "url": "http://..."       │ │
│ • 01_wiki_fetcher       │              │ │     }                           │ │
│ • 02_deep_evaluation    │              │ │   }                             │ │
│ • 03_embeddings_creator │              │ │ }                               │ │
│ • 04_deploy             │              │ └─────────────────────────────────┘ │
└─────────────────────────┘              └─────────────────────────────────────┘
                                                      │
                                                      │ PHP liest JSON
                                                      ▼
                                         ┌─────────────────────────────────────┐
                                         │   dokuwiki_plugin/lib/ConfigLoader  │
                                         │ ┌─────────────────────────────────┐ │
                                         │ │ function getConfig(): array     │ │
                                         │ │   $json = file_get_contents(    │ │
                                         │ │     '../config/settings.json'   │ │
                                         │ │   );                            │ │
                                         │ │   return json_decode($json);    │ │
                                         │ └─────────────────────────────────┘ │
                                         └─────────────────────────────────────┘
```

## Configuration Schema

### Zentrale Configuration (config/env.yaml)

| Section | Key | Type | Description |
| ------- | --- | ---- | ----------- |
| `APP` | `name` | string | Projektname ("dev_dito") |
| `APP` | `version` | string | Aktuelle Version |
| `PATHS` | `root_dir` | path | Repository-Root |
| `PATHS` | `config_dir` | path | `${root_dir}/config` |
| `PATHS` | `secrets_dir` | path | `${config_dir}/secrets` |
| `PATHS` | `output_dir` | path | `${root_dir}/output` |
| `SOURCE_WIKI.api` | `url` | url | JSON-RPC Endpoint des Quell-Wikis |
| `SOURCE_WIKI.api` | `base_url` | url | Base URL des Quell-Wikis |
| `SOURCE_WIKI.authentication` | `token_file` | path | Pfad zum API Token |
| `SOURCE_WIKI` | `certificate` | path | Pfad zum SSL Zertifikat |
| `SERVICES.mcp_server` | `url` | url | MCP Server URL |
| `SERVICES.mcp_server` | `timeout` | int | Request Timeout (Sekunden) |
| `SERVICES.qdrant` | `host` | string | Qdrant Hostname |
| `SERVICES.qdrant` | `port` | int | Qdrant Port |
| `SERVICES.qdrant` | `collection` | string | Collection Name |
| `SERVICES.openai` | `token_file` | path | Pfad zum OpenAI Token |
| `SERVICES.openai` | `embedding_model` | string | Embedding Model Name |
| `PIPELINE.fetcher` | `timeout` | int | Fetch Timeout |
| `PIPELINE.fetcher` | `exclude_namespaces` | list | Auszuschliessende Namespaces |
| `PIPELINE.embedder` | `chunk_size` | int | Chunk-Groesse |
| `PLUGIN` | `enabled` | bool | Plugin aktivieren |
| `PLUGIN` | `panel_position` | string | Panel-Position (left/right) |

### DokuWiki Plugin UI-Settings (conf/default.php)

Diese Settings sind NUR fuer die DokuWiki Admin UI - Werte werden aus `settings.json` ueberschrieben:

| Setting                  | Type        | Default | Description                    |
| ------------------------ | ----------- | ------- | ------------------------------ |
| `devdito_enabled`        | onoff       | `1`     | Plugin aktivieren (UI toggle)  |
| `devdito_panel_position` | multichoice | `right` | Panel-Position (UI selector)   |

### Deploy Script Configuration

| Variable           | Default                                   | Description                    |
| ------------------ | ----------------------------------------- | ------------------------------ |
| `$TargetWiki`      | `D:\_Repositories\...\first_own_dokuwiki` | Pfad zum Test-Wiki             |
| `$SkipSyntaxCheck` | `false`                                   | PHP Syntax-Check ueberspringen |

## API Contracts

### AJAX Endpoint: devdito_search

**Request:**
```http
POST /lib/exe/ajax.php?call=devdito_search
Content-Type: application/json

{
  "query": "Docker Setup",
  "limit": 5
}
```

**Response (Success):**
```json
{
  "ok": true,
  "query": "Docker Setup",
  "raw_content": "### 1. Seite (Score: 0.89)\n**Namespace:** ...",
  "latency_ms": 245
}
```

**Response (Error):**
```json
{
  "ok": false,
  "error": "mcp_url_not_configured",
  "latency_ms": 0
}
```

### AJAX Endpoint: devdito_ping

**Request:**
```http
POST /lib/exe/ajax.php?call=devdito_ping
```

**Response:**
```json
{
  "ok": true,
  "latency_ms": 42
}
```

### MCP Server (Outbound - EXTERNER Service)

Das Plugin ist ein **HTTP-Client** und kommuniziert mit dem **externen** MCP Server (Stack-H)
via JSON-RPC 2.0. Der MCP Server ist **nicht Teil** von Dev Dito.

**Target:** `$conf['devdito_mcp_url']` (default: `http://wiki_dev_mcp_server:3000`)

```json
{
  "jsonrpc": "2.0",
  "id": "devdito_search_1706713200",
  "method": "tools/call",
  "params": {
    "name": "semantic_wiki_search",
    "arguments": {
      "query": "Docker Setup",
      "top_k": 5
    }
  }
}
```

## File Dependencies

```tree
action.php
├── depends: dokuwiki\Extension\ActionPlugin
├── depends: dokuwiki\Extension\Event
├── depends: dokuwiki\Extension\EventHandler
├── calls: $this->getConf('devdito_*')
├── calls: file_get_contents() → MCP Server
└── outputs: HTML (Panel), JSON (AJAX)

admin.php
├── depends: dokuwiki\Extension\AdminPlugin
├── calls: $this->getConf('devdito_*')
├── calls: file_get_contents() → MCP/Qdrant
└── outputs: HTML (Dashboard)

dist/devdito.min.js
├── depends: DOKU_BASE (global)
├── reads: #devdito-panel, #devdito-toggle
└── calls: XMLHttpRequest → AJAX endpoints

conf/default.php
└── defines: $conf['devdito_*'] defaults

conf/metadata.php
└── defines: $meta['devdito_*'] schema
```

## Security Considerations

| Concern               | Mitigation                                             |
| --------------------- | ------------------------------------------------------ |
| AJAX ohne Auth        | `isUserLoggedIn()` Check in `handleAjax()`             |
| Admin-Zugriff         | `forAdminOnly()` returns `true` in admin.php           |
| XSS in Search Results | `hsc()` fuer alle User-Inputs, `escapeHtml()` in JS    |
| MCP URL Injection     | Regex-Validierung in metadata.php: `/^https?:\/\/.+/`  |
| SSRF via MCP URL      | Nur von Admin konfigurierbar, Docker-Netzwerk isoliert |

## Performance Considerations

| Metric         | Target  | Current | Notes                     |
| -------------- | ------- | ------- | ------------------------- |
| Deploy Time    | < 5s    | ~2s     | ✅ Erreicht               |
| Plugin Load    | < 100ms | ~20ms   | ✅ Nur Event-Registration |
| Search Latency | < 500ms | ~250ms  | Abhaengig von MCP/Qdrant  |
| Panel Open     | < 100ms | ~50ms   | CSS transition            |

## Testing Strategy

### Manual Testing Checklist

1. **Zentrale Config (User Story 4)**
   - [ ] `config/env.yaml` existiert und ist vollstaendig
   - [ ] `config/PLACEHOLDER_env.yaml` existiert als Template
   - [ ] `python config.py` generiert `config/settings.json`
   - [ ] Keine hardcodierten URLs/Ports in Pipeline-Code
   - [ ] Secrets in `config/secrets/` sind gitignored

2. **Wiki Fetcher (User Story 5)**
   - [ ] `python pipeline/01_wiki_fetcher/fetch.py --dry-run` liest zentrale Config
   - [ ] Authentifizierung gegen Quell-Wiki funktioniert
   - [ ] SSL Zertifikat wird korrekt geladen

3. **Deploy-Verification (User Story 1)**
   - [ ] `deploy-plugin.ps1` laeuft ohne Fehler
   - [ ] Alle Dateien im Ziel-Verzeichnis
   - [ ] Version korrekt in Output

4. **Plugin-Funktionalitaet**
   - [ ] Admin-Menu "Dev Dito Core Setup" sichtbar
   - [ ] Dashboard zeigt Service-Status
   - [ ] Plugin liest URLs aus `settings.json` (nicht hardcoded)
   - [ ] Search-Button in User Tools (eingeloggt)

5. **Error Handling**
   - [ ] Suche ohne MCP zeigt Fehler-Message
   - [ ] Fehlende Config-Datei zeigt klare Fehlermeldung

### Automated Checks

- **Config Validation**: `python config.py --validate`
- **No Hardcoding**: `grep -r "http://" pipeline/` findet nur Kommentare
- **PHP Syntax**: `php -l` fuer alle .php Dateien
- **Gitignore Check**: `git status` zeigt keine Secrets

## Complexity Tracking

Keine Constitution-Violations - Feature ist straightforward:

| Aspect         | Complexity         | Justification             |
| -------------- | ------------------ | ------------------------- |
| Plugin-Typen   | 2 (Action + Admin) | Standard DokuWiki Pattern |
| Config-Options | 3                  | Minimale Konfiguration    |
| AJAX-Endpoints | 2                  | Search + Ping             |
| Scripts        | 1                  | Nur deploy-plugin.ps1     |

## Next Steps

Nach Plan-Approval:

1. **`/tasks` Command ausfuehren** fuer detaillierten Task-Breakdown
2. **Zentrale Config erstellen** (User Story 4 - P1):
   - `config/env.yaml` + `PLACEHOLDER_env.yaml`
   - `config.py` Root-Level Loader
   - `config/secrets/` Verzeichnis
3. **Pipeline-Module umstellen** auf zentrale Config
4. **Wiki Fetcher Integration** (User Story 5 - P2)
5. Deployment Scripts finalisieren
