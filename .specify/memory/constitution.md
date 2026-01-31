# Dev Dito Constitution

> Dev Dito ist ein Service Gateway Addon fuer DokuWiki zur Verwaltung der Wiki-Embedding-Pipeline
> und externer AI-Services. Es integriert bestehende Pipeline-Module (Wiki Fetcher,
> Deep Evaluation, Embeddings Creator, Deploy) in eine steuerbare Einheit mit DokuWiki
> Admin-Interface. Dev Dito ist Stack-G einer 9-Stack Docker-Architektur.
>
> **Wichtige Architektur-Klarstellung:**
> - Dev Dito **VERBINDET sich mit** externen Services (MCP Server, Qdrant, LLM)
> - Dev Dito **ENTHAELT NICHT** den MCP Server (dieser ist Teil von Stack-H)
> - Das `backend_services/` Verzeichnis dient nur der lokalen Entwicklung/Tests
> - In Production laufen MCP Server, Qdrant etc. in separaten Stacks (D, H)
>
> Diese Constitution gilt ausschliesslich fuer das `dev_dito` Repository. Sie regelt die
> Integration bestehender Pipeline-Skripte, die DokuWiki-Plugin-Entwicklung und die
> Docker-Service-Konfiguration. Ueberarbeitung der Pipeline-Skripte selbst faellt nicht
> unter diesen Scope.

## Project Identity

| Eigenschaft           | Wert                                                                  |
| --------------------- | --------------------------------------------------------------------- |
| **Projekt**           | Dev Dito - Wiki Embedding Pipeline & Service Addon                    |
| **Team**              | Jan Ritt (IxI-Enki), Imre Obermüller                                  |
| **Kontext**           | Diplomarbeit 2026, HTL Leonding                                       |
| **Stack**             | Python 3.11+ (Pipeline), PHP (DokuWiki Plugin), Docker/Docker Compose |
| **Deployment**        | Docker lokal + Raspberry Pi (SSH Deploy)                              |
| **Zielgruppe**        | Wiki-Administrator (primaer Entwickler selbst)                        |
| **Architektur-Rolle** | Stack-G in Multi-Stack Docker-Architektur (Stacks A-I)                |
| **Version**           | 0.1.0-alpha                                                           |

---

## Core Principles

### Article I: Layered Module Architecture

**Mandate**: Dev Dito besteht aus drei strikt getrennten Schichten: DokuWiki Plugin (PHP),
Pipeline-Module (Python) und Backend Services (Docker). Schichten kommunizieren ausschliesslich
ueber HTTP-APIs oder Docker-Netzwerke. Kein direkter Aufruf ueber Sprachgrenzen hinweg
(kein `exec()`, kein `shell_exec()`, kein `subprocess` in Gegenrichtung).

**Rationale**: Die Trennung erlaubt es, Pipeline-Module unabhaengig zu entwickeln, zu testen
und zu deployen. Das DokuWiki Plugin bleibt ein reiner HTTP-Client gegenueber den Backend-Services.
Pipeline-Skripte koennen lokal oder in Docker ausgefuehrt werden, ohne dass das PHP-Plugin
davon wissen muss.

**Enforcement**:
- [ ] Kein `exec()`, `shell_exec()` oder `system()` in PHP-Code, das Python aufruft
- [ ] Kein `subprocess` in Python, das PHP aufruft
- [ ] Alle Schicht-Uebergaenge erfolgen ueber HTTP (REST, JSON-RPC) oder Docker CLI
- [ ] Pipeline-Module sind als eigenstaendige Python-Packages lauffaehig
- [ ] Backend Services sind ueber `docker-compose.yml` definiert und gestartet

**References**:
- [DokuWiki Plugin Development](https://www.dokuwiki.org/devel:plugins)
- [Docker Compose Networking](https://docs.docker.com/compose/networking/)

---

### Article II: JSON Interface Standard

**Mandate**: JSON ist das einzige Datenaustauschformat zwischen allen Komponenten. Die
MCP-Server-Kommunikation erfolgt via JSON-RPC 2.0. REST-Endpoints akzeptieren und liefern
`application/json`. Pipeline-Module lesen JSON/JSONL als Input und schreiben JSON/JSONL
als Output. Konfigurationsdateien verwenden YAML nur fuer statische Konfiguration, niemals
fuer Runtime-Datenaustausch.

**Rationale**: Ein einheitliches Austauschformat reduziert Parsing-Komplexitaet und
vereinfacht Debugging. JSON ist nativ in Python, PHP und JavaScript verfuegbar und wird
von Qdrant und OpenAI APIs bereits verwendet.

**Enforcement**:
- [ ] Alle HTTP-Endpoints setzen `Content-Type: application/json`
- [ ] MCP Server implementiert JSON-RPC 2.0 Spezifikation
- [ ] Pipeline-Output ist JSON oder JSONL (eine JSON-Zeile pro Dokument)
- [ ] Keine XML-, CSV- oder Protobuf-Schnittstellen zwischen Komponenten
- [ ] YAML ausschliesslich fuer `docker-compose.yml`, `env.yaml` und statische Config

**References**:
- [JSON-RPC 2.0 Specification](https://www.jsonrpc.org/specification)
- [Qdrant REST API](https://qdrant.tech/documentation/interfaces/#rest-api)
- [OpenAI API Reference](https://platform.openai.com/docs/api-reference)

---

### Article II-B: Centralized YAML Configuration (No Hardcoding)

**Mandate**: ALLE Konfigurationswerte werden in YAML-Dateien (`config/env.yaml`) ausgelagert.
Es gibt KEINE hardcodierten Variablen im Code. Jedes Modul (Pipeline, Plugin, Service) folgt
dem gleichen Pattern wie der Wiki Fetcher: Eine zentrale `config.py`/`config.php` laedt
Werte aus `env.yaml`, loest Platzhalter (`${var}`) auf und stellt typisierte Exports bereit.

**Pattern (aus Wiki Fetcher uebernommen):**
```
module/
├── config/
│   ├── env.yaml              # Aktive Konfiguration (in .gitignore)
│   ├── PLACEHOLDER_env.yaml  # Template mit Dokumentation
│   ├── settings.json         # Auto-generiert aus env.yaml
│   └── *.token, *.cert       # Secrets (in .gitignore)
└── config.py                 # Laedt env.yaml, exportiert typisierte Werte
```

**Rationale**: Der Wiki Fetcher demonstriert das ideale Config-Pattern:
- Alle Werte zentral und dokumentiert
- Platzhalter fuer Pfad-Aufloesung (`${root_dir}/config`)
- Secrets in separaten Dateien (nicht in YAML)
- Auto-generiertes `settings.json` fuer Debugging
- Type-sichere Exports im Code

**Enforcement**:
- [ ] Kein String-Literal im Code, das eine URL, einen Pfad oder einen Port enthaelt
- [ ] Jedes Modul hat `config/env.yaml` und `config/PLACEHOLDER_env.yaml`
- [ ] Python-Module haben `config.py` mit `load_config()` Funktion
- [ ] PHP-Dateien lesen Config ueber DokuWiki `$conf[]` ODER eigene `config.php`
- [ ] Alle `.yaml`, `.token`, `.cert`, `.key` Dateien in `.gitignore`
- [ ] Docker-Services nutzen `${VARIABLE}` Syntax in `docker-compose.yml`

**Standard-Struktur fuer env.yaml:**
```yaml
APP:
  name: module_name
  version: "1.0.0"

PATHS:
  root_dir: /path/to/module
  config_dir: ${root_dir}/config
  output_dir: ${root_dir}/output

API:
  url: https://example.com/api
  authentication:
    type: bearer
    token_file: ${config_dir}/api.token
  certificate: ${config_dir}/ssl.cert

# Module-spezifische Einstellungen...
```

**References**:
- Wiki Fetcher config.py: `pipeline/01_wiki_fetcher/config.py`
- [PyYAML Documentation](https://pyyaml.org/wiki/PyYAMLDocumentation)
- [12-Factor App Config](https://12factor.net/config)

---

### Article III: Critical-Path Unit Testing

**Mandate**: Unit-Tests sind fuer kritische Logik erforderlich: Embedding-Pipeline
(Chunking, Embedding-Generierung), HTTP-Client-Integration (MCP-Aufrufe, Qdrant-Health-Checks)
und Pipeline-Orchestrierung. Nicht-kritische Hilfsfunktionen, UI-Code und Konfigurationslogik
erfordern keine Tests. Health-Checks fuer Docker-Services sind als Smoke-Tests implementiert.

**Rationale**: Vollstaendige Testabdeckung waere fuer eine Diplomarbeit mit zwei Entwicklern
unverhältnismaessig. Tests dort, wo Fehler schwer zu diagnostizieren sind (Embedding-Qualitaet,
Vektor-Dimensionen, HTTP-Timeouts), liefern den hoechsten Nutzen.

**Enforcement**:
- [ ] `pipeline/03_embeddings_creator/` hat Unit-Tests fuer Chunking und Embedding-Output-Format
- [ ] `dokuwiki_plugin/` HTTP-Client-Code hat Tests fuer JSON-RPC Request/Response-Format
- [ ] `backend_services/qdrant_db/` hat Tests fuer Collection-Schema-Validierung (lokale Dev)
- [ ] Docker-Services definieren `healthcheck` in `docker-compose.yml`
- [ ] Tests sind mit `pytest` (Python) bzw. `phpunit` (PHP) ausfuehrbar

**References**:
- [pytest Documentation](https://docs.pytest.org/)
- [PHPUnit Documentation](https://docs.phpunit.de/)

---

### Article IV: Language Standards

**Mandate**: Python-Code folgt PEP 8, erzwungen durch `ruff` (Linting) und `black`
(Formatting). PHP-Code folgt PSR-12, erzwungen durch `phpcs`. Type Hints sind in Python
fuer alle Funktionssignaturen erforderlich. PHP verwendet strikte Typisierung
(`declare(strict_types=1)`) in allen neuen Dateien.

**Rationale**: Einheitliche Formatierung eliminiert Style-Diskussionen im Zwei-Personen-Team
und macht Code-Reviews effizienter. Type Hints verbessern die IDE-Unterstuetzung und
reduzieren Runtime-Fehler bei der Integration zwischen Pipeline-Modulen.

**Enforcement**:
- [ ] `ruff check` und `black --check` laufen ohne Fehler auf allen Python-Dateien
- [ ] `phpcs --standard=PSR12` laeuft ohne Fehler auf allen PHP-Dateien
- [ ] Alle Python-Funktionen haben Type Hints fuer Parameter und Return-Werte
- [ ] Neue PHP-Dateien beginnen mit `declare(strict_types=1)`

**References**:
- [PEP 8](https://peps.python.org/pep-0008/)
- [Ruff Linter](https://docs.astral.sh/ruff/)
- [Black Formatter](https://black.readthedocs.io/)
- [PSR-12](https://www.php-fig.org/psr/psr-12/)
- [PHP Strict Types](https://www.php.net/manual/en/language.types.declarations.php#language.types.declarations.strict)

---

### Article V: Pragmatic Documentation

**Mandate**: Dokumentation dient der Entwicklung, nicht der Vollstaendigkeit. Jedes
Pipeline-Modul hat ein `README.md` mit Zweck, Input/Output-Format und Aufrufbeispiel.
Komplexe Architekturentscheidungen werden als Kommentare im Code dokumentiert, nicht in
separaten ADR-Dateien. `README.md` und `README_ARCHITECTURE.md` im Repository-Root
bleiben aktuell.

**Rationale**: Bei zwei Entwicklern und Diplomarbeits-Zeitdruck ist jede Minute
Dokumentation eine Minute weniger Implementierung. Inline-Dokumentation nahe am Code
bleibt eher aktuell als externe Dokumente.

**Enforcement**:
- [ ] Jedes Verzeichnis unter `pipeline/` hat ein `README.md`
- [ ] Alle Docker-Services in `backend_services/` haben ein `README.md`
- [ ] Oeffentliche Python-Funktionen haben Docstrings
- [ ] PHP-Klassen haben PHPDoc-Bloecke fuer oeffentliche Methoden
- [ ] `README_ARCHITECTURE.md` spiegelt die aktuelle Stack-Zuordnung wider

**References**:
- [Google Python Docstring Guide](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings)
- [PHPDoc Reference](https://docs.phpdoc.org/guide/references/phpdoc/index.html)

---

### Article VI: Secret Containment

**Mandate**: Secrets (API Keys, Tokens, Passwoerter) werden NIEMALS direkt in `env.yaml`
gespeichert. Stattdessen referenziert `env.yaml` separate Secret-Dateien (siehe Article II-B):

```yaml
# RICHTIG: Token in separater Datei
authentication:
  token_file: ${config_dir}/api.token    # ← Datei enthaelt nur den Token

# FALSCH: Token direkt in YAML
authentication:
  token: "sk-abc123..."                   # ← NIE SO!
```

Placeholder-Dateien (`PLACEHOLDER_*.yaml`, `PLACEHOLDER_*.token`) dokumentieren die
benoetigten Werte ohne echte Secrets. Secrets werden niemals in Source Code, Commit
Messages oder Log-Output geschrieben.

**Rationale**: Das Repository ist privat, aber API-Keys (OpenAI, DokuWiki JSON-RPC, SSH)
duerfen trotzdem nicht im Git-Verlauf landen. Separate Token-Dateien ermoeglichen
einfaches Rotieren ohne YAML-Aenderung.

**Enforcement**:
- [ ] `.gitignore` enthaelt `*.env`, `env.yaml`, `*.token`, `*.cert`, `*.key`
- [ ] Kein Secret-Wert in Python/PHP Source Code (kein hardcodierter API-Key)
- [ ] Placeholder-Dateien existieren fuer jede Secret-Konfiguration
- [ ] Log-Output maskiert Secret-Werte (keine API-Keys in Logfiles)
- [ ] `docker-compose.yml` referenziert Secrets ueber `${VARIABLE}` Syntax

**References**:
- [Docker Compose Environment Variables](https://docs.docker.com/compose/environment-variables/)
- [OWASP Secrets Management](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)

---

### Article VII: Integration Simplicity Gate

**Mandate**: Dev Dito integriert bestehende Pipeline-Module als Thin Wrappers. Ein Modul-Wrapper
darf maximal Konfiguration laden, das Original-Skript aufrufen und den Output weiterleiten.
Neue Abstraktionsschichten ueber bestehende Funktionalitaet erfordern eine dokumentierte
Begruendung. Die Anzahl der Docker-Services in Stack-G bleibt auf das Minimum beschraenkt,
das fuer die Funktionalitaet noetig ist.

**Rationale**: Die Pipeline-Skripte existieren bereits und funktionieren. Dev Dito soll sie
integrieren, nicht neu erfinden. Jede Abstraktionsschicht ist eine potenzielle Fehlerquelle
und erhoehter Wartungsaufwand fuer ein Zwei-Personen-Team.

**Enforcement**:
- [ ] Modul-Wrapper enthalten keine eigene Business-Logik (nur Config + Delegation)
- [ ] Kein neuer Docker-Service ohne dokumentierten Zweck in `README.md`
- [ ] Pipeline-Module behalten ihre originale Aufruf-Schnittstelle
- [ ] Neue Abstraktionen (Klassen, Interfaces) erfordern einen Kommentar mit Begruendung

**References**:
- [YAGNI Principle](https://martinfowler.com/bliki/Yagni.html)
- [Thin Wrapper Pattern](https://wiki.c2.com/?ThinWrapper)

---

### Article VIII: Direct Framework Usage

**Mandate**: Framework-Features werden direkt verwendet, ohne eigene Wrapper-Schichten.
DokuWiki Plugin API, FastAPI, Qdrant Client und OpenAI Client werden so eingesetzt, wie
ihre Dokumentation es vorsieht. Eigene Abstraktionen ueber Framework-Klassen sind nur
erlaubt, wenn die selbe Logik an drei oder mehr Stellen dupliziert wuerde.

**Rationale**: Wrapper um Frameworks erzeugen eine zweite API, die gelernt und gewartet
werden muss. Bei einem Projekt mit begrenzter Lebensdauer (Diplomarbeit) ueberwiegt der
Vorteil direkter Framework-Nutzung.

**Enforcement**:
- [ ] Kein eigener HTTP-Client-Wrapper -- `requests` (Python) und `curl`/DokuWiki HTTP (PHP) direkt verwenden
- [ ] Kein eigener Qdrant-Abstraction-Layer -- `qdrant_client` direkt verwenden
- [ ] Kein eigener OpenAI-Wrapper -- `openai` Python Client direkt verwenden
- [ ] Duplikation-Schwelle: Erst ab 3 identischen Aufrufen eine Helper-Funktion extrahieren

**References**:
- [Qdrant Python Client](https://python-client.qdrant.tech/)
- [OpenAI Python Client](https://github.com/openai/openai-python)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)

---

### Article IX: Realistic Integration Testing

**Mandate**: Integration-Tests laufen gegen echte Docker-Services, nicht gegen Mocks.
Qdrant-Tests verwenden eine Test-Collection im laufenden Qdrant-Container. HTTP-Client-Tests
im Plugin senden echte Requests gegen lokale Dev-Services. Pipeline-Integration-Tests
verwenden einen reduzierten Datensatz (10-20 Seiten statt des gesamten Wikis).
OpenAI-API-Aufrufe in Tests verwenden einen Mock oder gecachte Responses, um Kosten zu vermeiden.

**Rationale**: Dev Dito ist ein Integrationsprojekt -- die meisten Fehler entstehen an den
Schnittstellen zwischen Komponenten, nicht innerhalb einzelner Funktionen. Mocks fuer
Docker-Services verschleiern genau die Fehler, die in Produktion auftreten.

**Enforcement**:
- [ ] `docker-compose.yml` oder separates `docker-compose.test.yml` fuer Test-Umgebung
- [ ] Qdrant-Tests erstellen und loeschen eigene Test-Collections
- [ ] Plugin HTTP-Client-Tests validieren JSON-RPC Request/Response-Format gegen lokale Services
- [ ] OpenAI-Embedding-Aufrufe in Tests sind gemockt oder verwenden gecachte Responses
- [ ] Test-Datensatz ist ein definiertes Subset (max. 20 Wiki-Seiten)

**References**:
- [Qdrant Collections API](https://qdrant.tech/documentation/concepts/collections/)
- [pytest-docker](https://github.com/avast/pytest-docker)

---

## Workflow Governance

### /specify Gate

Bevor eine Spezifikation genehmigt wird, muss sie enthalten:
- [ ] Mindestens eine User Story mit Akzeptanzkriterien (Given/When/Then)
- [ ] Identifikation der betroffenen Schicht(en): Plugin, Pipeline, Backend Service
- [ ] Auflistung der betroffenen Docker-Services und deren Konfigurationsaenderungen
- [ ] Abgrenzung: Was aendert sich NICHT (bestehende Pipeline-Skripte bleiben unveraendert, es sei denn explizit anders angegeben)

### /plan Gate

Bevor ein Plan genehmigt wird, muss er nachweisen:
- [ ] Keine Verletzung von Article I (Schicht-Trennung)
- [ ] Keine neuen Abstraktionsschichten ohne Begruendung (Article VII, VIII)
- [ ] Betroffene Docker-Services sind in `README_ARCHITECTURE.md` dokumentiert
- [ ] Keine neuen Secrets ohne Placeholder-Dateien (Article VI)

### /tasks Gate

Aufgaben muessen folgende Constraints erfuellen:
- [ ] Eine Aufgabe betrifft maximal eine Schicht (PHP ODER Python ODER Docker)
- [ ] Abhaengigkeiten zwischen Aufgaben sind explizit markiert
- [ ] Jede Aufgabe hat ein klares "Done"-Kriterium

### /implement Gate

Nach der Implementierung muessen folgende Checks bestehen:
- [ ] `ruff check` und `black --check` fuer geaenderte Python-Dateien
- [ ] `phpcs --standard=PSR12` fuer geaenderte PHP-Dateien
- [ ] Unit-Tests fuer kritische Logik bestehen (Article III)
- [ ] Docker-Services starten und Health-Checks bestehen
- [ ] Keine Secrets im Diff (`git diff` enthaelt keine API-Keys oder Tokens)

---

## Graceful Error Management

Pipeline-Fehler werden wie folgt behandelt:
- **Logging**: Jeder Fehler wird mit Kontext (Modul, Input, Fehlermeldung) geloggt
- **Kein harter Abbruch**: Ein fehlgeschlagener Pipeline-Schritt bricht nicht die gesamte Pipeline ab
- **Kein komplexes Retry**: Keine automatische Wiederholungslogik -- bei Fehlern wird der Schritt uebersprungen und im Log vermerkt
- **Manueller Re-Run**: Fehlgeschlagene Schritte werden manuell ueber das Admin-Interface oder CLI neu gestartet

---

## Naming Conventions

| Kontext                | Convention               | Beispiel                                    |
| ---------------------- | ------------------------ | ------------------------------------------- |
| Docker Container       | `devdito_*` Praefix      | `devdito_mcp_server`, `devdito_qdrant_init` |
| Pipeline-Module        | `NN_name` Nummerierung   | `01_wiki_fetcher`, `02_deep_evaluation`     |
| Python Packages        | `snake_case`             | `embeddings_creator`, `wiki_fetcher`        |
| PHP Klassen            | `PascalCase`             | `ServiceGateway`, `AdminPanel`              |
| DokuWiki Seiten        | `devdito:name` Namespace | `devdito:dashboard`, `devdito:services`     |
| Docker Ports (Stack-G) | 3000-3001, 8085          | MCP Server: 3000, Reserve: 3001             |

---

## Scope Boundaries

### In Scope
- DokuWiki Plugin Entwicklung (Admin-Interface, Service-Dashboard, AJAX-Endpoints)
- Integration der Pipeline-Module als Thin Wrappers (Fetcher, Evaluator, Embedder, Deploy)
- Pipeline-Orchestrierung via Admin-Interface (Start, Stop, Monitor)
- HTTP-Client-Integration zu externen Services (MCP Server, Qdrant, LLM)
- Docker-Service-Konfiguration fuer **Stack-G** (docker-compose.yml, Dockerfiles)
- Lokale Entwicklungs-Services in `backend_services/` (NUR fuer lokale Tests)
- SSH Deploy zum Raspberry Pi

### Out of Scope
- **MCP Server Entwicklung** → Gehoert zu Stack-H (extension-mcp-servers-services)
- **Qdrant Server Setup** → Gehoert zu Stack-D (extensions-ai-core-services)
- **LLM Server Setup** (Ollama/LMStudio) → Gehoert zu Stack-D
- Ueberarbeitung der bestehenden Pipeline-Skripte (`research/techstack/` Verzeichnis)
- Leonidas ChatBot Plugin Entwicklung → Gehoert zu Stack-I (separates Projekt)
- Keycloak Konfiguration → Gehoert zu Stack-B
- Andere Stacks (A-F, H-I) ausser deren dokumentierte Schnittstellen

---

## Governance

Diese Constitution ist das verbindliche Referenzdokument fuer alle Entwicklungsentscheidungen
im `dev_dito` Repository. Bei Widerspruechen zwischen Constitution und anderem Code oder
Dokumentation gilt die Constitution.

### Amendments

Aenderungen an der Constitution erfordern:
1. Dokumentation der Aenderung mit Datum und Begruendung im Amendment Log
2. Zustimmung beider Teammitglieder
3. Aktualisierung der Versionsnummer

---

## Amendment Log

| Datum      | Version | Aenderung                            | Begruendung                                                                                                                                                                              |
| ---------- | ------- | ------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 2026-01-31 | 1.0.0   | Initiale Constitution erstellt       | Grundlage fuer Spec-Kit-basierte Entwicklung                                                                                                                                             |
| 2026-01-31 | 1.1.0   | MCP Server Zuordnung korrigiert      | MCP Server gehoert zu Stack-H (nicht Stack-G). Dev Dito ist Service Gateway (Client), nicht MCP Server (Provider). Architektur-Klarstellung hinzugefuegt. Scope Boundaries aktualisiert. |
| 2026-01-31 | 1.2.0   | Article II-B: Centralized YAML Config | ALLE Konfiguration in YAML auslagern, KEINE hardcodierten Variablen. Wiki Fetcher config.py Pattern als Standard fuer alle Module. |

---

**Version**: 1.2.0 | **Ratified**: 2026-01-31 | **Last Amended**: 2026-01-31
