# Feature Specification: DokuWiki Plugin Dev Dito - Development & Deployment

**Feature Branch**: `001-wiki-fetcher-integration`  
**Created**: 2026-01-31  
**Status**: Draft  
**Input**: User description: "DokuWiki Extension Development mit automatischem Deployment zum lokalen Test-Wiki"

## Kontext

Dev Dito ist eine DokuWiki Extension (Plugin) die:
- Service Gateway fuer AI Services (Ollama, LMStudio, Qdrant) bereitstellt
- Semantische Wiki-Suche via MCP Server ermoeglicht
- Admin-Dashboard fuer Service-Monitoring bietet

**Source**: `D:\_Repositories\_Diploma_Thesis_Repositories\dev_dito\dokuwiki_plugin\`  
**Target Wiki**: `C:\path\to\legacy-stack\development\first_own_dokuwiki`  
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

### Edge Cases

- Was passiert wenn Target-Wiki nicht laeuft? → Warning ausgeben, Dateien trotzdem kopieren
- Was passiert bei Syntax-Fehler in PHP? → phpcs/phplint vor Deploy ausfuehren
- Wie werden Konflikte mit bestehenden Dateien behandelt? → Immer ueberschreiben (Dev-Umgebung)
- Was passiert wenn `dist/` fehlt? → Build automatisch triggern oder Error mit Hinweis

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUSS PowerShell-Script `deploy-plugin.ps1` bereitstellen das Plugin korrekt deployed
- **FR-002**: System MUSS DokuWiki Plugin-Struktur exakt einhalten (siehe DokuWiki Plugin Guidelines)
- **FR-003**: System MUSS `plugin.info.txt` mit allen Pflichtfeldern haben: base, author, email, date, name, desc, url, version
- **FR-004**: System MUSS bei Deploy pruefen ob Ziel-Verzeichnis existiert
- **FR-005**: System MUSS Timestamps/Version fuer Cache-Busting unterstuetzen
- **FR-006**: System MUSS PHP Syntax-Check vor Deploy durchfuehren (`php -l`)
- **FR-007**: System MUSS Erfolgsmeldung mit geprueften Dateien ausgeben

### Non-Functional Requirements

- **NFR-001**: Deploy-Zeit unter 5 Sekunden
- **NFR-002**: Scripts muessen ohne Admin-Rechte laufen
- **NFR-003**: Keine externen Dependencies ausser PHP CLI

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

### Measurable Outcomes

- **SC-001**: Deploy-Script laeuft fehlerfrei durch in < 5 Sekunden
- **SC-002**: Plugin erscheint in DokuWiki Admin → Extension Manager
- **SC-003**: Admin-Dashboard ist erreichbar unter Admin → Dev Dito Core Setup
- **SC-004**: Search-Button erscheint fuer eingeloggte User
- **SC-005**: Keine PHP Errors/Warnings im DokuWiki Error-Log nach Deploy
- **SC-006**: `phpcs --standard=PSR12` zeigt keine Errors (Constitution Article IV)

## Referenzen

- [DokuWiki Plugin Development](https://www.dokuwiki.org/devel:plugins)
- [DokuWiki Plugin Structure](https://www.dokuwiki.org/devel:plugin_file_structure)
- [plugin.info.txt Format](https://www.dokuwiki.org/devel:plugin_info)
- [PSR-12 Coding Standard](https://www.php-fig.org/psr/psr-12/)
