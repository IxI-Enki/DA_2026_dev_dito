# Feature Specification: DokuWiki Plugin Dev Dito - Development & Deployment

**Feature Branch**: `001-plugin-dev-deploy`  
**Created**: 2026-01-31  
**Status**: Draft  
**Input**: User description: "DokuWiki Extension Development mit automatischem Deployment zum lokalen Test-Wiki"

## Kontext

Dev Dito ist eine DokuWiki Extension (Plugin) die als **Service Gateway** fungiert:

- **HTTP-Client** zu externen AI-Services (verbindet sich mit, enthaelt nicht):
  - MCP Server (Stack-H) - fuer semantische Suche
  - Qdrant (Stack-D) - fuer Health-Checks
  - Ollama/LMStudio (Stack-D) - fuer LLM-Status
- **Admin-Dashboard** fuer Service-Monitoring und -Konfiguration
- **Pipeline-Steuerung**: Fetcher, Evaluator, Embedder, Deploy
- **Zentrale Konfiguration**: EINE `config/env.yaml` fuer ALLE Komponenten

**Architektur-Hinweise (Constitution v1.2.0):**
> - Dev Dito ist Stack-G und **VERBINDET sich mit** externen Services
> - Der MCP Server ist **NICHT Teil** von Dev Dito (gehoert zu Stack-H)
> - **ALLE Konfiguration** in zentraler `config/env.yaml` (Article II-B)
> - **KEINE hardcodierten Variablen** im Code

**Source**: `D:\_Repositories\_Diploma_Thesis_Repositories\dev_dito\dokuwiki_plugin\`  
**Target Wiki**: `D:\_Repositories\year_2025_26\SYP_2025_26\leonie\internal_leonidas\development\first_own_dokuwiki`  
**Target Path**: `plugins_dev\devdito\`

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Plugin Bundle & Deploy (Priority: P1)

Als Entwickler moechte ich das Plugin automatisch korrekt gepackt und im lokalen Test-Wiki installiert bekommen, um Aenderungen sofort testen zu koennen.

**Why this priority**: Ohne funktionierendes Deployment kann nichts getestet werden - Basis fuer alle weiteren Features.

**Independent Test**: Script ausfuehren, Wiki im Browser oeffnen, Plugin-Features pruefen.

**Acceptance Scenarios**:

1. **Given** Plugin-Source in `dokuwiki_plugin/`, **When** Deploy-Script ausgefuehrt wird, **Then** wird Plugin nach `plugins_dev/devdito/` kopiert mit:
   - Korrekter DokuWiki-Verzeichnisstruktur
   - Alle PHP-Dateien (`action.php`, `admin.php`)
   - Konfiguration (`conf/default.php`, `conf/metadata.php`)
   - Sprachdateien (`lang/de/`, `lang/en/`)
   - Assets (`dist/devdito.min.css`, `dist/devdito.min.js`)
   - Plugin-Info (`plugin.info.txt`)
   - Logo (`logo.png`)

2. **Given** Plugin deployed und Wiki laeuft, **When** Admin sich einloggt, **Then** erscheint "Dev Dito Core Setup" im Admin-Menu

3. **Given** Plugin deployed und Wiki laeuft, **When** User eingeloggt ist, **Then** erscheint "Wiki durchsuchen" Button in den User Tools

---

### User Story 2 - Build Assets (Priority: P2)

Als Entwickler moechte ich CSS/JS Assets automatisch minifiziert bekommen, damit das Plugin performant ist.

**Why this priority**: Assets muessen gebaut werden bevor Deploy - aber nicht bei jeder Aenderung noetig.

**Independent Test**: Build-Script ausfuehren, pruefen dass `dist/` Dateien aktualisiert wurden.

**Acceptance Scenarios**:

1. **Given** CSS/JS Source-Dateien existieren, **When** Build-Script ausgefuehrt wird, **Then** werden `dist/devdito.min.css` und `dist/devdito.min.js` erstellt

2. **Given** Build abgeschlossen, **When** Deploy ausgefuehrt wird, **Then** werden die neuen `dist/` Dateien mit deployed

---

### User Story 3 - Version Bump & Release (Priority: P3)

Als Entwickler moechte ich die Plugin-Version konsistent aktualisieren koennen, damit DokuWiki Cache-Busting funktioniert.

**Why this priority**: Wichtig fuer sauberes Release-Management, aber manuell machbar.

**Independent Test**: Version-Bump Script ausfuehren, pruefen dass alle Versionsnummern synchron sind.

**Acceptance Scenarios**:

1. **Given** aktuelle Version 0.1.0, **When** `bump-version.ps1 0.2.0` ausgefuehrt wird, **Then** wird Version aktualisiert in:
   - `plugin.info.txt` (Zeile `version`)
   - `action.php` (Konstante `VERSION`)
   - `admin.php` (Konstante `VERSION`)

---

### User Story 4 - Zentrale Konfiguration (Priority: P1)

Als Entwickler moechte ich ALLE Einstellungen an EINER Stelle konfigurieren, damit ich nicht mehrere Dateien editieren muss.

**Why this priority**: Basis-Architektur die VOR allen anderen Features stehen muss. Constitution Article II-B Compliance.

**Independent Test**: `config/env.yaml` editieren, alle Komponenten nutzen die neuen Werte.

**Acceptance Scenarios**:

1. **Given** zentrale `config/env.yaml` existiert, **When** ein Wert geaendert wird, **Then** nutzen ALLE Komponenten (Plugin, Pipeline, Docker) den neuen Wert

2. **Given** `config/env.yaml` mit Source-Wiki URL, **When** Wiki Fetcher laeuft, **Then** nutzt er die URL aus der zentralen Config

3. **Given** `config/env.yaml` mit MCP Server URL, **When** Plugin Search ausgefuehrt wird, **Then** nutzt es die URL aus der zentralen Config (via `settings.json`)

4. **Given** Secret-Dateien in `config/secrets/`, **When** Config geladen wird, **Then** werden Secrets aus separaten Dateien gelesen (nicht aus YAML direkt)

**Config-Struktur (Pflicht)**:

```
dev_dito/
├── config/                          # ZENTRALE CONFIG
│   ├── env.yaml                     # MASTER CONFIG (gitignored)
│   ├── PLACEHOLDER_env.yaml         # Template mit Dokumentation
│   ├── settings.json                # Auto-generiert fuer PHP
│   └── secrets/                     # Alle Secrets (gitignored)
│       ├── json_rpc_api.token       # Wiki JSON-RPC API Key
│       ├── ssl.cert                 # SSL Zertifikat
│       └── openai.token             # OpenAI API Key
├── config.py                        # Root-Level Config Loader
```

---

### User Story 5 - Wiki Fetcher Integration (Priority: P2)

Als Entwickler moechte ich das Schul-Wiki (LeoWiki) ueber JSON-RPC API fetchen koennen, konfiguriert ueber die zentrale Config.

**Why this priority**: Kern-Feature von Dev Dito, aber abhaengig von User Story 4 (Zentrale Config).

**Independent Test**: Fetcher-Script ausfuehren, Wiki-Inhalt wird in `output/` gespeichert.

**Acceptance Scenarios**:

1. **Given** `config/env.yaml` mit SOURCE_WIKI Einstellungen, **When** `python pipeline/01_wiki_fetcher/fetch.py` laeuft, **Then** wird das konfigurierte Wiki gefetcht

2. **Given** API Token in `config/secrets/json_rpc_api.token`, **When** Fetcher laeuft, **Then** authentifiziert er sich erfolgreich

3. **Given** SSL Zertifikat in `config/secrets/ssl.cert`, **When** Fetcher laeuft, **Then** nutzt er das Zertifikat fuer HTTPS

---

### Edge Cases

- Was passiert wenn Target-Wiki nicht laeuft? → Warning ausgeben, Dateien trotzdem kopieren
- Was passiert bei Syntax-Fehler in PHP? → phpcs/phplint vor Deploy ausfuehren
- Wie werden Konflikte mit bestehenden Dateien behandelt? → Immer ueberschreiben (Dev-Umgebung)
- Was passiert wenn `dist/` fehlt? → Build automatisch triggern oder Error mit Hinweis

## Requirements *(mandatory)*

### Functional Requirements - Deployment

- **FR-001**: System MUSS PowerShell-Script `deploy-plugin.ps1` bereitstellen das Plugin korrekt deployed
- **FR-002**: System MUSS DokuWiki Plugin-Struktur exakt einhalten (siehe DokuWiki Plugin Guidelines)
- **FR-003**: System MUSS `plugin.info.txt` mit allen Pflichtfeldern haben: base, author, email, date, name, desc, url, version
- **FR-004**: System MUSS bei Deploy pruefen ob Ziel-Verzeichnis existiert
- **FR-005**: System MUSS Timestamps/Version fuer Cache-Busting unterstuetzen
- **FR-006**: System MUSS PHP Syntax-Check vor Deploy durchfuehren (`php -l`)
- **FR-007**: System MUSS Erfolgsmeldung mit geprueften Dateien ausgeben

### Functional Requirements - Zentrale Konfiguration (Constitution Article II-B)

- **FR-100**: System MUSS zentrale `config/env.yaml` als EINZIGE Konfig-Quelle nutzen
- **FR-101**: System MUSS `config/PLACEHOLDER_env.yaml` als dokumentiertes Template bereitstellen
- **FR-102**: System MUSS `config.py` (Root-Level) bereitstellen das env.yaml laedt und typisierte Exports bietet
- **FR-103**: System MUSS `config/settings.json` auto-generieren fuer PHP-Komponenten
- **FR-104**: System MUSS Secrets in separaten Dateien (`config/secrets/`) speichern, NICHT in env.yaml
- **FR-105**: System MUSS Platzhalter (`${var}`) in env.yaml zur Laufzeit aufloesen
- **FR-106**: System DARF KEINE hardcodierten URLs, Pfade oder Ports im Code haben

### Functional Requirements - Wiki Fetcher

- **FR-200**: System MUSS Source-Wiki JSON-RPC URL aus zentraler Config lesen
- **FR-201**: System MUSS API Token aus `config/secrets/json_rpc_api.token` laden
- **FR-202**: System MUSS SSL Zertifikat aus `config/secrets/ssl.cert` nutzen
- **FR-203**: System MUSS Fetch-Output in konfigurierbares Output-Verzeichnis schreiben

### Non-Functional Requirements

- **NFR-001**: Deploy-Zeit unter 5 Sekunden
- **NFR-002**: Scripts muessen ohne Admin-Rechte laufen
- **NFR-003**: Keine externen Dependencies ausser PHP CLI und PyYAML
- **NFR-004**: Config-Dateien (env.yaml, secrets/*) MUESSEN in .gitignore sein

### DokuWiki Plugin Struktur (Pflicht)

```text
devdito/
├── plugin.info.txt          # PFLICHT: Plugin-Metadaten
├── action.php               # Action Plugin (Events)
├── admin.php                # Admin Plugin (Dashboard)
├── conf/
│   ├── default.php          # Default-Konfigurationswerte
│   └── metadata.php         # Konfigurationsschema
├── lang/
│   ├── de/
│   │   ├── lang.php         # Deutsche Uebersetzungen
│   │   └── settings.php     # Deutsche Settings-Labels
│   └── en/
│       ├── lang.php         # Englische Uebersetzungen
│       └── settings.php     # Englische Settings-Labels
├── dist/                    # Kompilierte Assets
│   ├── devdito.min.css
│   └── devdito.min.js
├── lib/                     # Hilfsklassen (optional)
└── logo.png                 # Plugin-Logo (72x72 PNG)
```

### Key Entities

- **PluginPackage**: Vollstaendiges Plugin-Bundle mit allen Dateien
- **DeployTarget**: Ziel-Wiki mit Pfad zu `lib/plugins/` oder `plugins_dev/`
- **BuildArtifact**: Generierte Dateien (minified CSS/JS)

## Success Criteria *(mandatory)*

### Measurable Outcomes - Deployment

- **SC-001**: Deploy-Script laeuft fehlerfrei durch in < 5 Sekunden
- **SC-002**: Plugin erscheint in DokuWiki Admin → Extension Manager
- **SC-003**: Admin-Dashboard ist erreichbar unter Admin → Dev Dito Core Setup
- **SC-004**: Search-Button erscheint fuer eingeloggte User
- **SC-005**: Keine PHP Errors/Warnings im DokuWiki Error-Log nach Deploy
- **SC-006**: `phpcs --standard=PSR12` zeigt keine Errors (Constitution Article IV)

### Measurable Outcomes - Zentrale Konfiguration

- **SC-100**: `config/env.yaml` existiert und ist vollstaendig dokumentiert
- **SC-101**: `config/PLACEHOLDER_env.yaml` existiert als Template
- **SC-102**: `python config.py` generiert `config/settings.json` ohne Fehler
- **SC-103**: `grep -r "http://" pipeline/` findet KEINE hardcodierten URLs (nur in Kommentaren)
- **SC-104**: `grep -r ":3000\|:6333\|:8080" pipeline/` findet KEINE hardcodierten Ports
- **SC-105**: `.gitignore` enthaelt `config/env.yaml`, `config/secrets/`, `*.token`, `*.cert`

### Measurable Outcomes - Wiki Fetcher

- **SC-200**: `python pipeline/01_wiki_fetcher/fetch.py --dry-run` liest Config korrekt
- **SC-201**: Fetcher authentifiziert sich erfolgreich gegen Source-Wiki

## Referenzen

- [DokuWiki Plugin Development](https://www.dokuwiki.org/devel:plugins)
- [DokuWiki Plugin Structure](https://www.dokuwiki.org/devel:plugin_file_structure)
- [plugin.info.txt Format](https://www.dokuwiki.org/devel:plugin_info)
- [PSR-12 Coding Standard](https://www.php-fig.org/psr/psr-12/)
