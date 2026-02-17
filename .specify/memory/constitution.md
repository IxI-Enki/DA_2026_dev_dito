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

| Eigenschaft           | Wert                                                                                                             |
| --------------------- | ---------------------------------------------------------------------------------------------------------------- |
| **Projekt**           | Dev Dito - Wiki Embedding Pipeline & Service Addon                                                               |
| **Team**              | Jan Ritt (CIFT - Embedding/Retrieval/Auth/Deploy), Imre Obermüller (BIF - MCP Server/Transport/Tools)            |
| **Kontext**           | Diplomarbeit 2026, HTL Leonding                                                                                  |
| **Betreuer**          | Rainer Stropek                                                                                                   |
| **Stack**             | Python 3.11+ (Pipeline), PHP (DokuWiki Plugin), Docker/Docker Compose, FastAPI (Gateway)                         |
| **Deployment**        | Docker lokal (Windows 11) + Raspberry Pi (SSH Deploy), npm Package (MCP Server)                                  |
| **Zielgruppe**        | Wiki-Administrator (primaer Entwickler selbst), Claude Desktop (MCP Client)                                      |
| **Architektur-Rolle** | Stack-G in Multi-Stack Docker-Architektur (Stacks A-I)                                                           |
| **Forschungsfragen**  | FF1: Semantic vs Keyword Search, FF2: MCP Integration Standard, FF3: Embedding Model Comparison (German Content) |
| **Version**           | 1.4.0                                                                                                            |

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

**Mandate**: ALLE Konfigurationswerte werden in YAML-Dateien ausgelagert. Es gibt KEINE
hardcodierten Variablen im Code. Es wird zwischen zentraler Konfiguration und Modul-Konfiguration
unterschieden:

- **Zentrale Config** (`config/env.yaml`): Stack-weite Einstellungen (Ports, Hosts, Pfade)
- **Modul-Config** (`pipeline/NN_module/env.yaml`): Modul-spezifische Einstellungen die
  zentrale Werte ueberschreiben oder ergaenzen koennen

Jedes Modul folgt dem gleichen Pattern: Eine `config.py`/`config.php` laedt Werte aus `env.yaml`,
loest Platzhalter (`${var}`) auf und stellt typisierte Exports bereit.

**Known Config Violations (v1.4.0):**
- `pipeline/02_deep_evaluation/env.yaml`: Pfade zeigen auf Prototype-Location ausserhalb dev_dito → **Tier 1 Fix**
- `pipeline/04_embeddings_creator/env.yaml`: Lokale hardcodierte Pfade → Deferred (post-thesis)
- `pipeline/03_rag_preprocessing/env.yaml`: Lokale Config → Deferred (post-thesis)

**Pattern (aus Wiki Fetcher uebernommen):**
```tree
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
- [ ] `pipeline/04_embeddings_creator/` hat Unit-Tests fuer Chunking und Embedding-Output-Format
- [ ] `dokuwiki_plugin/` HTTP-Client-Code hat Tests fuer JSON-RPC Request/Response-Format
- [ ] `evaluation/` dient als Referenz-Implementierung (56+ Tests fuer Metriken und Config)
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
separaten ADR-Dateien. `README.md` im Repository-Root und `docs/architecture.md` bleiben aktuell.

**Rationale**: Bei zwei Entwicklern und Diplomarbeits-Zeitdruck ist jede Minute
Dokumentation eine Minute weniger Implementierung. Inline-Dokumentation nahe am Code
bleibt eher aktuell als externe Dokumente.

**Enforcement**:
- [ ] Jedes Verzeichnis unter `pipeline/` hat ein `README.md`
- [ ] Alle Docker-Services in `backend_services/` haben ein `README.md`
- [ ] Oeffentliche Python-Funktionen haben Docstrings
- [ ] PHP-Klassen haben PHPDoc-Bloecke fuer oeffentliche Methoden
- [ ] `docs/architecture.md` spiegelt die aktuelle Stack-Zuordnung wider

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
- [ ] `docker-compose.yml` mit Test-Profile (`--profile test`) fuer isolierte Test-Infrastruktur
- [ ] Qdrant-Tests erstellen und loeschen eigene Test-Collections
- [ ] Plugin HTTP-Client-Tests validieren JSON-RPC Request/Response-Format gegen lokale Services
- [ ] OpenAI-Embedding-Aufrufe in Tests sind gemockt oder verwenden gecachte Responses
- [ ] Test-Datensatz ist ein definiertes Subset (max. 20 Wiki-Seiten)

**References**:
- [Qdrant Collections API](https://qdrant.tech/documentation/concepts/collections/)
- [pytest-docker](https://github.com/avast/pytest-docker)

---

### Article X: Evaluation-First Development

**Mandate**: Die Implementierung von Evaluations-Infrastruktur und Thesis-Metriken hat VORRANG
vor Infrastruktur-Refactorings. Evaluation-Skripte zur Generierung von Thesis-Tabellen und
-Grafiken (FF1/FF2/FF3) muessen lauffaehig sein, bevor das Gateway-Orchestrator-Refactoring
(DooD-Removal, docker compose run) durchgefuehrt wird. Thesis-Deliverables (J1-J8, I1-I5)
definieren die Prioritaet der Engineering-Tasks.

**Rationale**: Die Diplomarbeit wird nach wissenschaftlichen Ergebnissen bewertet, nicht nach
der Eleganz der Docker-Orchestrierung. Evaluation-Skripte liefern die Daten fuer Kapitel 6-7
der Thesis. Ein perfektes Gateway ohne auswertbare Daten ist wertlos fuer die Abgabe.

**Execution Mandate** (v1.4.0): Evaluation-Infrastruktur ohne ausgefuehrte Ergebnisse hat KEINEN
Thesis-Wert. Die Generierung von Ergebnis-Daten (`evaluation/results/`) hat ABSOLUTE PRIORITAET
gegenueber jeder weiteren Infrastruktur, Dokumentation oder Code-Bereinigung. Erst Ergebnisse,
dann Optimierung.

**Enforcement**:
- [ ] FF1-Keyword-Search-Baseline-Skript existiert und generiert MRR/Precision@5 Metriken
- [ ] J4-Chunk-Size-Evaluation-Skript erzeugt vergleichbare Outputs fuer 256/512/1024 Tokens
- [ ] J2/FF3-Model-Comparison-Framework kann beliebige Embedding-Modelle austauschen (Ollama, OpenAI, MTEB)
- [ ] Evaluation-Outputs sind in `evaluation/results/` versioniert und referenzierbar
- [ ] Infrastructure-Refactorings (DooD -> docker compose run) erfolgen ERST nach lauffaehiger Evaluation
- [ ] Jede Forschungsfrage (FF1, FF3) hat mindestens ein Ergebnis-JSON in `evaluation/results/`
- [ ] LaTeX-Tabellen werden aus tatsaechlichen Ergebnissen generiert, nicht aus Platzhaltern

**References**:
- Thesis Deliverables: `README_THESIS.md`
- MTEB Leaderboard: https://huggingface.co/spaces/mteb/leaderboard

---

### Article XI: Thesis Milestone Alignment

**Mandate**: Jede Engineering-Task muss mindestens einer Forschungsfrage (FF1-FF3) oder einem
Thesis-Deliverable (J1-J8, I1-I5) zugeordnet sein. Tasks ohne Thesis-Relevanz werden als
"Post-Thesis Enhancement" markiert und haben niedrigste Prioritaet. Der Milestone-Plan
(siehe Section "Thesis Alignment") definiert die zwingende Reihenfolge.

**Rationale**: Bei zwei Studenten mit 3 Monaten bis zur Abgabe (2026-05-30) ist jede Arbeitsstunde
kostbar. "Nice-to-have" Features wie DooD-Removal oder Guru-Architektur-Patterns sind nur
erlaubt, wenn sie direkt Thesis-Kapitel unterstuetzen.

**Enforcement**:
- [ ] Jede Spezifikation listet die zugehoerige Forschungsfrage im Header
- [ ] Tasks ohne FF-Zuordnung erhalten das Label "post-thesis"
- [ ] Der aktuelle Milestone (siehe Thesis Alignment Section) ist sichtbar im Dashboard
- [ ] Pull Requests referenzieren die Thesis-Deliverable-ID (z.B. "Closes #J4")

**References**:
- Thesis Milestone Overview: `README_THESIS.md`
- Deliverable Tracking: `docs/thesis/deliverables.md`

---

### Article XII: Resource Governance

**Mandate**: Resource Governance fuer Docker-Services in Stack-G ist in zwei Stufen gegliedert:

**Tier 1 — Sofort (v1.4.0):**
- ALLE Image-Versionen muessen explizit gepinnt sein (kein `:latest` Tag)
- Health-Checks muessen `start_period` fuer langsam startende Services definieren
- `.dockerignore` in jedem Build-Context

**Tier 2 — Nach Evaluation-Ergebnissen:**
- `deploy.resources.limits` (memory, cpus) kalibriert aus Profiling-Daten
- Qdrant: max 1GB RAM, Embedder: max 2GB, Gateway/Pipeline: max 512MB

**Rationale**: Dev Dito laeuft auf Entwickler-Laptops (Windows 11, 16-32GB RAM) und einem Raspberry Pi 5 (8GB).
Resource Limits ohne Profiling-Daten sind willkuerlich und koennen Evaluations blockieren (Article X Vorrang).
Gepinnte Versionen und Health-Checks sind hingegen risikolos und sofort umsetzbar.

**Enforcement**:
- [ ] Alle `image:` Tags enthalten explizite Versionsnummern (z.B. `qdrant/qdrant:v1.7.4`)
- [ ] Health-Checks fuer Services mit >10s Startzeit haben `start_period: 30s`
- [ ] Docker Compose Profiles (`pipeline`, `wiki`, `dev`) sind dokumentiert
- [ ] Resource Limits werden NACH Evaluation-Ausfuehrung anhand tatsaechlicher Nutzung kalibriert

**References**:
- [Docker Compose Resource Constraints](https://docs.docker.com/compose/compose-file/deploy/#resources)
- [Qdrant Memory Configuration](https://qdrant.tech/documentation/guides/configuration/)

---

### Article XIII: DooD Deprecation

**Mandate**: Docker-outside-of-Docker (DooD) ueber Docker-Socket-Mounting (`/var/run/docker.sock`)
ist als DEPRECATED markiert und wird in Phase 2 (post-Evaluation) entfernt. Der Gateway-Orchestrator
darf KEINE neuen DooD-basierten Features mehr implementieren. Die Migration zu `docker compose run`
fuer batch jobs erfolgt ERST nach Abschluss der Evaluation-Infrastruktur (Article X).

**Rationale**: DooD erzeugt Sicherheitsrisiken (Root-Zugriff auf Host-Docker), kompliziert das
Windows-Deployment und ist nicht noetig fuer run-to-completion Pipeline-Jobs. Der Overhead
des Refactorings ist jedoch nur gerechtfertigt, wenn die Evaluation-Skripte bereits produktiv sind.

**Enforcement**:
- [ ] Neue Pipeline-Module verwenden NICHT `docker.from_env()` oder `DockerClient()`
- [ ] Gateway-Orchestrator dokumentiert DooD-Usage als "DEPRECATED" in Code-Kommentaren
- [ ] Phase-2-Migration-Plan existiert in `docs/architecture/dood_removal.md`
- [ ] DooD-basierte Container-Starts loggen eine Deprecation-Warning

**References**:
- Docker Compose Run: https://docs.docker.com/compose/reference/run/
- Security Best Practices: https://cheatsheetseries.owasp.org/cheatsheets/Docker_Security_Cheat_Sheet.html

---

### Article XIV: Inter-Stack Communication

**Mandate**: ALLE Kommunikation zwischen Stack-G (dev-dito) und anderen Stacks (A-I) erfolgt
ausschliesslich via HTTP ueber das `leonidas-network` Docker-Netzwerk. Stack-G darf KEINE Volumes
von anderen Stacks mounten. Stack-G darf KEINE Container anderer Stacks starten oder stoppen.
Service-Discovery erfolgt via Docker Compose DNS-Namen (z.B. `http://qdrant:6333`, `http://mcp-server:3000`).

**Cross-Stack-Ownership:**
- **Stack-D (ai-core)**: Qdrant, Ollama, LMStudio → Dev Dito ist HTTP-Client
- **Stack-E (eval-benchmarks)**: RAGAS Evaluation → Dev Dito sendet Test-Daten via HTTP
- **Stack-H (mcp-servers)**: MCP Server (Imre's Domain) → Dev Dito ist JSON-RPC-Client
- **Stack-A (wiki-sandbox)**: DokuWiki Plugin → Ruft Dev Dito Gateway auf (Port 8089)

**Rationale**: Tight Coupling zwischen Stacks (shared volumes, Container-Management) macht
unabhaengige Entwicklung unmoeglich und verhindert, dass Jan und Imre parallel arbeiten koennen.
HTTP-basierte Schnittstellen erlauben es, Stacks auf separaten Hosts zu deployen (z.B. Qdrant
auf dem Pi, Gateway auf Laptop).

**Enforcement**:
- [ ] `docker-compose.yml` in Stack-G enthaelt KEINE `volumes_from` oder externe Volume-Mounts
- [ ] Kein `docker exec`, `docker start` oder `docker stop` auf Container ausserhalb Stack-G
- [ ] Alle inter-stack API-Calls verwenden Docker DNS-Namen oder konfigurierbare URLs
- [ ] Stack-G exponiert nur Port 8089 (Gateway) an `leonidas-network`
- [ ] Service-Dependencies sind in `docker-compose.yml` ueber `depends_on` dokumentiert

**References**:
- Docker Compose Networking: https://docs.docker.com/compose/networking/
- Multi-Stack Architecture: `README_ARCHITECTURE.md`

---

## Workflow Governance

### /specify Gate

Bevor eine Spezifikation genehmigt wird, muss sie enthalten:
- [ ] Mindestens eine User Story mit Akzeptanzkriterien (Given/When/Then)
- [ ] Identifikation der betroffenen Schicht(en): Plugin, Pipeline, Backend Service
- [ ] Auflistung der betroffenen Docker-Services und deren Konfigurationsaenderungen
- [ ] Abgrenzung: Was aendert sich NICHT (bestehende Pipeline-Skripte bleiben unveraendert, es sei denn explizit anders angegeben)
- [ ] **NEU**: Thesis-Zuordnung (FF1-FF3, J1-J8, I1-I5) oder "post-thesis" Label

### /plan Gate

Bevor ein Plan genehmigt wird, muss er nachweisen:
- [ ] Keine Verletzung von Article I (Schicht-Trennung)
- [ ] Keine neuen Abstraktionsschichten ohne Begruendung (Article VII, VIII)
- [ ] Betroffene Docker-Services sind in `README_ARCHITECTURE.md` dokumentiert
- [ ] Keine neuen Secrets ohne Placeholder-Dateien (Article VI)
- [ ] **NEU**: Resource Limits (Article XII) fuer neue Services definiert
- [ ] **NEU**: Inter-Stack-Dependencies (Article XIV) dokumentiert

### /tasks Gate

Aufgaben muessen folgende Constraints erfuellen:
- [ ] Eine Aufgabe betrifft maximal eine Schicht (PHP ODER Python ODER Docker)
- [ ] Abhaengigkeiten zwischen Aufgaben sind explizit markiert
- [ ] Jede Aufgabe hat ein klares "Done"-Kriterium
- [ ] **NEU**: Thesis-Deliverable-ID ist im Task-Titel referenziert

### /implement Gate

Nach der Implementierung muessen folgende Checks bestehen:
- [ ] `ruff check` und `black --check` fuer geaenderte Python-Dateien
- [ ] `phpcs --standard=PSR12` fuer geaenderte PHP-Dateien
- [ ] Unit-Tests fuer kritische Logik bestehen (Article III)
- [ ] Docker-Services starten und Health-Checks bestehen
- [ ] Keine Secrets im Diff (`git diff` enthaelt keine API-Keys oder Tokens)
- [ ] **NEU**: Keine `:latest` Image-Tags in `docker-compose.yml` (Article XII)
- [ ] **NEU**: Keine neuen DooD-Features (Article XIII)

---

## Thesis Alignment

### Forschungsfragen (Research Questions)

| ID  | Frage                                            | Zuständig | Methodik                                      | Deliverables    |
| --- | ------------------------------------------------ | --------- | --------------------------------------------- | --------------- |
| FF1 | Semantic Search vs Keyword Search (MRR, P@5)     | Jan       | Keyword baseline + Vector search comparison   | J1 (corpus), J6 |
| FF2 | MCP als Integration-Standard fuer Wissensquellen | Imre      | MCP vs REST/OData/GraphQL protocol comparison | I1-I5           |
| FF3 | Best Embedding Model fuer German Wiki Content    | Jan       | Model comparison (Ollama, OpenAI, MTEB)       | J2, J3, J5      |

### Jan's Deliverables (CIFT - Chapter 6: Retrieval & Deployment)

| ID  | Deliverable                                 | Status | Depends On | Target Milestone |
| --- | ------------------------------------------- | ------ | ---------- | ---------------- |
| J1  | Test Corpus (50 Q&A pairs, ground truth)    | ✅      | -          | 2026-02-10       |
| J2  | Embedding Model Comparison Framework        | ⚙️      | J1         | 2026-03-15       |
| J3  | DokuWiki Markup Parser → Clean Text Chunks  | ✅      | -          | 2025-11-15       |
| J4  | Chunk Size Impact (256/512/1024 tokens)     | ⚙️      | J1, J3     | 2026-03-15       |
| J5  | Vector DB Collection Schema (Qdrant)        | ✅      | -          | 2025-11-15       |
| J6  | Hybrid Search vs Dense Retrieval (FF1)      | ⚙️      | J1, J5     | 2026-03-15       |
| J7  | OAuth2/RBAC via ScaleKit                    | ✅      | -          | 2026-02-20       |
| J8  | Docker Container + npm Package (MCP Server) | 🔜      | I3, I4     | 2026-03-30       |

### Imre's Deliverables (BIF - Chapter 5: MCP Protocol & Tools)

| ID  | Deliverable                                  | Status | Depends On | Target Milestone |
| --- | -------------------------------------------- | ------ | ---------- | ---------------- |
| I1  | MCP Server (JSON-RPC 2.0)                    | ✅      | -          | 2025-12-20       |
| I2  | MCP Tools (search, fetch, list)              | ✅      | I1         | 2026-01-25       |
| I3  | Transport: stdio vs HTTP-streamable          | ✅      | I1         | 2026-02-20       |
| I4  | Role-Dependent Search Tools                  | ✅      | I2, J7     | 2026-02-20       |
| I5  | Client Compatibility Matrix (Claude, VSCode) | 🔜      | I3         | 2026-03-30       |

### Milestone Timeline

| Datum      | Milestone                     | Deliverables   | Critical Path                     |
| ---------- | ----------------------------- | -------------- | --------------------------------- |
| 2025-11-15 | ✅ Vector DB Schema + Chunking | J3, J5         | Basis fuer alle Evaluations       |
| 2025-12-20 | ✅ MCP Server (stdio)          | I1             | Imre's Grundstein                 |
| 2026-01-25 | ✅ Semantic Search Integrated  | I2             | FF2 Baseline                      |
| 2026-02-20 | ✅ HTTP Streamable Transport   | I3, I4, J7     | Production-Ready MCP              |
| 2026-03-15 | 🔜 Evaluation Infrastructure   | J1, J2, J4, J6 | **FF1/FF3 Auswertung** (PRIORITY) |
| 2026-03-30 | 🔜 npm Package + Docker Image  | J8, I5         | Deployment Deliverables           |
| 2026-04-15 | 🔜 Thesis Writing Start        | -              | Kapitel 1-4 (Theory)              |
| 2026-05-15 | 🔜 Thesis Review (Stropek)     | -              | Full Draft                        |
| 2026-05-30 | 🔜 Thesis Submission           | -              | **HARD DEADLINE**                 |

**Status-Legende:** ✅ = Abgeschlossen | ⚙️ = Code Complete / Ergebnisse ausstehend | 🔜 = Geplant

**Hinweis J6 (v1.4.0):** Aktuell nur Dense Search implementiert. Hybrid Search (BM25 payload index)
entweder implementieren ODER als Limitation dokumentieren und in Future Work verweisen.

### Current Gaps (MUST Address)

1. **Evaluation Execution** (J2/J4/J6): Skripte existieren, aber KEINE Ergebnis-JSONs generiert
2. **FF1 Keyword Baseline**: Skript existiert (`eval_keyword_baseline.py`), muss ausgefuehrt werden
3. **Thesis Writing**: Jan + Imre muessen Kapitel 1-4 (Theorie) JETZT beginnen → 40 Seiten pro Person

**Resolution Priority (Article X Execution Mandate):**
1. Evaluation-Skripte ausfuehren → Ergebnis-JSONs generieren (FF1, FF3)
2. LaTeX-Tabellen aus Ergebnissen exportieren (US5)
3. Thesis-Kapitel 6-7 mit echten Daten schreiben
4. Phase 2 (DooD Removal, Config Consolidation) → Post-Thesis Enhancement

---

## Graceful Error Management

Pipeline-Fehler werden wie folgt behandelt:
- **Logging**: Jeder Fehler wird mit Kontext (Modul, Input, Fehlermeldung) geloggt
- **Kein harter Abbruch**: Ein fehlgeschlagener Pipeline-Schritt bricht nicht die gesamte Pipeline ab
- **Kein komplexes Retry**: Keine automatische Wiederholungslogik -- bei Fehlern wird der Schritt uebersprungen und im Log vermerkt
- **Manueller Re-Run**: Fehlgeschlagene Schritte werden manuell ueber das Admin-Interface oder CLI neu gestartet

---

## Naming Conventions

| Kontext                | Convention               | Beispiel                                         |
| ---------------------- | ------------------------ | ------------------------------------------------ |
| Docker Container       | `devdito_*` Praefix      | `devdito_mcp_server`, `devdito_qdrant_init`      |
| Pipeline-Module        | `NN_name` Nummerierung   | `01_wiki_fetcher`, `02_deep_evaluation`          |
| Python Packages        | `snake_case`             | `embeddings_creator`, `wiki_fetcher`             |
| PHP Klassen            | `PascalCase`             | `ServiceGateway`, `AdminPanel`                   |
| DokuWiki Seiten        | `devdito:name` Namespace | `devdito:dashboard`, `devdito:services`          |
| Docker Ports (Stack-G) | 3000-3001, 8085-8089     | Gateway: 8089, MCP: 3000, Reserve: 3001          |
| Evaluation Scripts     | `eval_*` Praefix         | `eval_keyword_baseline.py`, `eval_chunk_size.py` |

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
- **NEU**: Evaluation-Skripte fuer FF1/FF3 (Keyword Baseline, Model Comparison, Chunk Size)
- **NEU**: Test-Corpus-Generierung (J1) mit Ground-Truth Q&A Paaren
- **NEU**: RAGAS-Integration fuer Retrieval-Metriken (MRR, NDCG@10, Precision@5)

### Out of Scope
- **MCP Server Entwicklung** → Gehoert zu Stack-H (extension-mcp-servers-services)
- **Qdrant Server Setup** → Gehoert zu Stack-D (extensions-ai-core-services)
- **LLM Server Setup** (Ollama/LMStudio) → Gehoert zu Stack-D
- Ueberarbeitung der bestehenden Pipeline-Skripte (`research/techstack/` Verzeichnis)
- Leonidas ChatBot Plugin Entwicklung → Gehoert zu Stack-I (separates Projekt)
- Keycloak Konfiguration → Gehoert zu Stack-B
- Andere Stacks (A-F, H-I) ausser deren dokumentierte Schnittstellen
- **Guru-Architektur-Patterns** (services/src/core/adapters/) fuer Module <500 LOC
- **DooD-basierte neue Features** (deprecated per Article XIII)

---

## Known Violations Register (v1.4.0)

Intentionally-deferred violations. Verhindert dass Agents bereits akzeptierte technische Schulden
erneut triagieren.

| Article | Violation                                        | Status                 | Target             |
| ------- | ------------------------------------------------ | ---------------------- | ------------------ |
| II-B    | `02_deep_evaluation/env.yaml` Prototype-Pfade    | Fix Scheduled (Tier 1) | 2026-02-28         |
| II-B    | `04_embeddings_creator/env.yaml` hardcoded paths | Deferred               | Post-thesis        |
| II-B    | `03_rag_preprocessing/env.yaml` local config     | Deferred               | Post-thesis        |
| VII     | `module_deployer/entrypoint.py` 377 LOC          | Accepted               | Post-thesis        |
| XII     | Keine Resource Limits auf Services               | Accepted (Tier 2)      | Nach Eval-Results  |

### Dead Code Policy

Verzeichnisse die weder von `docker-compose.yml` referenziert, noch von Python importiert,
noch in `docs/` dokumentiert sind, MUESSEN geloescht werden. Bereits geloescht (v1.4.0):
- `backend_services/qdrant_db/`, `wiki_dev_mcp_server/`, `embeddings/`
- `pipeline/02_deep_evaluation/check_models.py`, `cleanup_strategies.py`

---

## Governance

Diese Constitution ist das verbindliche Referenzdokument fuer alle Entwicklungsentscheidungen
im `dev_dito` Repository. Bei Widerspruechen zwischen Constitution und anderem Code oder
Dokumentation gilt die Constitution.

### Constitution Hierarchy

Die Articles folgen einer Prioritaetsordnung: Hoehere Articles ueberschreiben niedrigere bei Konflikten.

**Priority Order:**
1. **Article X** (Evaluation-First) + **Article XI** (Thesis Alignment) → OBERSTE PRIORITAET
2. Articles I-IX (Core Engineering Principles)
3. Articles XII-XIV (Infrastructure Governance)

**Beispiel-Konflikt-Resolution:**
- Article VII ("Integration Simplicity") verbietet neue Abstraktionen
- Article X ("Evaluation-First") fordert Evaluation-Framework
- **Resolution**: Evaluation-Framework wird gebaut (Article X > Article VII), ABER als Thin Wrapper implementiert (Article VII bleibt anwendbar innerhalb des Frameworks)

### Amendments

Aenderungen an der Constitution erfordern:
1. Dokumentation der Aenderung mit Datum und Begruendung im Amendment Log
2. Zustimmung beider Teammitglieder
3. Aktualisierung der Versionsnummer

---

## Amendment Log

| Datum      | Version | Aenderung                                            | Begruendung                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| ---------- | ------- | ---------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 2026-01-31 | 1.0.0   | Initiale Constitution erstellt                       | Grundlage fuer Spec-Kit-basierte Entwicklung                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| 2026-01-31 | 1.1.0   | MCP Server Zuordnung korrigiert                      | MCP Server gehoert zu Stack-H (nicht Stack-G). Dev Dito ist Service Gateway (Client), nicht MCP Server (Provider). Architektur-Klarstellung hinzugefuegt. Scope Boundaries aktualisiert.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| 2026-01-31 | 1.2.0   | Article II-B: Centralized YAML Config                | ALLE Konfiguration in YAML auslagern, KEINE hardcodierten Variablen. Wiki Fetcher config.py Pattern als Standard fuer alle Module.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| 2026-02-12 | 1.3.0   | Thesis-Driven Governance + Expert Debate Integration | **Articles X-XIV hinzugefuegt**: Evaluation-First Development, Thesis Milestone Alignment, Resource Governance, DooD Deprecation, Inter-Stack Communication. **Thesis Alignment Section**: Forschungsfragen FF1-FF3, Jan's Deliverables J1-J8, Imre's Deliverables I1-I5, Milestone Timeline, Current Gaps. **Project Identity erweitert**: Betreuer (Stropek), Forschungsfragen, Rollentrennung (Jan=CIFT/Imre=BIF). **Workflow Gates erweitert**: Thesis-Zuordnung (FF/Deliverable-ID) mandatory. **Scope Boundaries erweitert**: Evaluation-Skripte, Test-Corpus, RAGAS-Integration. **Constitution Hierarchy**: Prioritaetsordnung Articles X/XI > I-IX > XII-XIV. Grundlage: 4 Runden Expert Debate (Architektur-Entscheidungen), Spec-Kit Best Practices, Thesis Requirements (40 Seiten/Person, Abgabe 2026-05-30). |
| 2026-02-13 | 1.4.0   | Expert Review Amendments + Execution Mandate         | **Art X**: Execution Mandate hinzugefuegt — Ergebnis-Generierung hat absolute Prioritaet. **Art XI**: Deliverable-Status aktualisiert (J1=Complete, J2/J4/J6=Code Complete, Gaps aktualisiert). **Art II-B**: Config-Reality — Zentral vs Modul-Config unterschieden, Known Violations dokumentiert. **Art III**: Stale `qdrant_db/` Referenz durch `evaluation/` Referenz ersetzt. **Art V**: `README_ARCHITECTURE.md` → `docs/architecture.md`. **Art IX**: `docker-compose.test.yml` → `--profile test`. **Art XII**: Tier-Split (Tier 1 sofort: Pinning+Healthchecks, Tier 2 nach Profiling: Resource Limits). **Neu**: Known Violations Register + Dead Code Policy. Grundlage: 3-Experten-Review (Docker, Software Architect, Thesis Expert) + Spec-Kit Architect Cross-Review. |

---

**Version**: 1.4.0 | **Ratified**: 2026-02-13 | **Last Amended**: 2026-02-13
