# Implementation Plan: DokuWiki Plugin Dev Dito - Development & Deployment

**Branch**: `001-plugin-dev-deploy` | **Date**: 2026-01-31 | **Spec**: [spec.md](./spec.md)  
**Input**: Feature specification from `/specs/001-plugin-dev-deploy/spec.md`

## Summary

Dev Dito ist eine DokuWiki Extension die als **Service Gateway** (HTTP-Client) zu externen
AI-Services fungiert. Das Plugin **verbindet sich mit** MCP Server (Stack-H), Qdrant (Stack-D)
und LLM Services - es **enthaelt diese nicht**. Dieses Feature etabliert die Development-
Infrastruktur: automatisiertes Deployment vom Source-Repository (`dokuwiki_plugin/`) zum
lokalen Test-Wiki (`plugins_dev/devdito/`).

**Architektur-Klarstellung (Constitution v1.1.0):**
- Dev Dito Plugin = HTTP-Client zu externen Services
- MCP Server = Separater Stack-H (nicht Teil von Dev Dito)
- `backend_services/` = Nur fuer lokale Entwicklung/Tests

**Kernkomponenten:**
1. PowerShell Deploy-Script mit PHP Syntax-Validierung
2. DokuWiki-konforme Plugin-Struktur (Action + Admin Plugin)
3. Asset-Management (CSS/JS minification)
4. Version-Synchronisation ueber alle Dateien

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

*GATE: Validated against `.specify/memory/constitution.md` (v1.1.0)*

| Article                            | Requirement                                                  | Status                                                       |
| ---------------------------------- | ------------------------------------------------------------ | ------------------------------------------------------------ |
| **I: Layered Module Architecture** | DokuWiki Plugin kommuniziert nur via HTTP mit externen Services | ✅ Plugin ist HTTP-Client zu MCP (Stack-H), Qdrant (Stack-D) |
| **II: JSON Interface Standard**    | JSON-RPC 2.0 fuer externe Service-Kommunikation              | ✅ Implementiert in `action.php` (Client-seitig)             |
| **IV: Language Standards**         | PHP PSR-12, `declare(strict_types=1)`                        | ✅ Alle PHP-Dateien konform                                  |
| **V: Pragmatic Documentation**     | README fuer Scripts                                          | ✅ `scripts/README.md` erstellt                              |
| **VI: Secret Containment**         | Keine Secrets in Code                                        | ✅ Service-URLs via DokuWiki Config                          |
| **VII: Integration Simplicity**    | Thin Wrapper, keine eigene Abstraktionen                     | ✅ Direkte DokuWiki API Nutzung                              |
| **VIII: Direct Framework Usage**   | DokuWiki APIs direkt nutzen                                  | ✅ `ActionPlugin`, `AdminPlugin` extends                     |

**Scope-Compliance (Constitution v1.1.0):**
- ✅ Plugin ist HTTP-Client (Service Gateway)
- ✅ MCP Server ist OUT OF SCOPE (gehoert zu Stack-H)
- ✅ Pipeline-Integration ist IN SCOPE (Admin-Interface zur Steuerung)

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
├── dokuwiki_plugin/                    # Plugin Source (EDITIERT HIER)
│   ├── plugin.info.txt                 # Plugin-Metadaten
│   ├── action.php                      # Action Plugin (742 LOC)
│   │   ├── register()                  # Event-Handler registrieren
│   │   ├── handleRegisterAssets()      # CSS/JS laden
│   │   ├── handleInjectPanel()         # Search-Panel UI
│   │   ├── handleAjax()                # AJAX Endpoints
│   │   ├── handlePingRequest()         # MCP Health Check
│   │   └── handleSearchRequest()       # Semantische Suche
│   ├── admin.php                       # Admin Plugin (463 LOC)
│   │   ├── html()                      # Dashboard rendern
│   │   ├── renderServiceStatusSection()# Service-Status Grid
│   │   ├── renderConfigurationSection()# Config-Tabelle
│   │   ├── testMcpServer()             # MCP Connection Test
│   │   └── testQdrant()                # Qdrant Connection Test
│   ├── conf/
│   │   ├── default.php                 # Defaults: enabled=1, mcp_url, position
│   │   └── metadata.php                # Schema: onoff, string, multichoice
│   ├── lang/
│   │   ├── de/                         # Deutsche Strings
│   │   │   ├── lang.php                # UI-Texte
│   │   │   └── settings.php            # Config-Labels
│   │   └── en/                         # Englische Strings
│   │       ├── lang.php
│   │       └── settings.php
│   ├── dist/                           # Kompilierte Assets
│   │   ├── devdito.min.css             # Spinner, Highlight, Print
│   │   └── devdito.min.js              # Panel UI, AJAX Search
│   ├── lib/                            # (leer, fuer zukuenftige Klassen)
│   └── logo.png                        # 72x72 Plugin-Logo
│
├── scripts/                            # Development Scripts
│   ├── deploy-plugin.ps1               # Deploy zum Test-Wiki ✅
│   └── README.md                       # Script-Dokumentation ✅
│
└── [Target Wiki - NICHT im Repo]
    D:\_Repositories\year_2025_26\SYP_2025_26\leonie\internal_leonidas\
    └── development\first_own_dokuwiki\
        └── plugins_dev\devdito\        # Deployment-Ziel
```

**Structure Decision**: Single DokuWiki Plugin mit zwei Plugin-Typen (Action + Admin).
Kein separates Frontend/Backend da DokuWiki selbst das Frontend ist.

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

## Configuration Schema

### DokuWiki Plugin Configuration

| Setting                  | Type        | Default                           | Description                        |
| ------------------------ | ----------- | --------------------------------- | ---------------------------------- |
| `devdito_enabled`        | onoff       | `1`                               | Plugin aktivieren/deaktivieren     |
| `devdito_mcp_url`        | string      | `http://wiki_dev_mcp_server:3000` | MCP Server URL (JSON-RPC Endpoint) |
| `devdito_panel_position` | multichoice | `right`                           | Panel-Position (left/right)        |

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

1. **Deploy-Verification**
   - [ ] `deploy-plugin.ps1` laeuft ohne Fehler
   - [ ] Alle 12 Dateien im Ziel-Verzeichnis
   - [ ] Version korrekt in Output

2. **Plugin-Funktionalitaet**
   - [ ] Admin-Menu "Dev Dito Core Setup" sichtbar
   - [ ] Dashboard zeigt Service-Status
   - [ ] "Test All Services" Button funktioniert
   - [ ] Search-Button in User Tools (eingeloggt)
   - [ ] Panel oeffnet/schliesst mit Toggle
   - [ ] Keyboard Shortcut Ctrl+Shift+F

3. **Error Handling**
   - [ ] Suche ohne MCP zeigt Fehler-Message
   - [ ] Suche ohne Login zeigt 401

### Automated Checks (in Deploy-Script)

- PHP Syntax: `php -l` fuer alle .php Dateien
- File Count: 12 Dateien erwartet
- Version: Aus plugin.info.txt extrahiert

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
1. `/tasks` Command ausfuehren fuer Task-Breakdown
2. Fehlende Scripts implementieren (bump-version.ps1)
3. User Story 2 (Asset Build) implementieren wenn noetig
