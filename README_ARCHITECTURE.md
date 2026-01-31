# Dev Dito - Multi-Stack Docker Architecture

> **Stand:** 2026-01-24  
> **Repository:** DA_2026_dev_dito  
> **Zweck:** Architektur-Referenz fuer AI-gestuetzte Entwicklung und SpecKit-Planung

---

## Inhaltsverzeichnis

- [Ueberblick](#ueberblick)
- [Stack-Zuordnung: Dev Dito](#stack-zuordnung-dev-dito)
- [Multi-Stack-Architektur (Gesamtsystem)](#multi-stack-architektur-gesamtsystem)
- [Shared Docker Network](#shared-docker-network)
- [Dev Dito Stack im Detail](#dev-dito-stack-im-detail)
- [Abhaengigkeiten zu anderen Stacks](#abhaengigkeiten-zu-anderen-stacks)
- [Vermeidung von Duplikaten](#vermeidung-von-duplikaten)
- [Entwicklungsrichtlinien](#entwicklungsrichtlinien)

---

## Ueberblick

Dieses Repository (`DA_2026_dev_dito`) ist **Stack-G** der modularen Multi-Stack-Docker-Architektur.

```
GESAMTSYSTEM: 9 Docker-Compose-Stacks (A-I)
              ↓
DEV DITO:     Stack-G (extension-dev-dito-services)
              + nutzt Stack-D (AI Core: Qdrant)
              + stellt Tools fuer Stack-H (MCP Servers) bereit
```

**Wichtig:** Jeder Stack ist ein separates `docker-compose.yml`. Alle kommunizieren ueber ein **shared Docker Network** (`external: true`).

---

## Stack-Zuordnung: Dev Dito

| Stack | Name | Dev Dito Beziehung |
|-------|------|-------------------|
| **Stack-G** | `extension-dev-dito-services` | **DIESES REPOSITORY** |
| Stack-D | `extensions-ai-core-services` | Dev Dito **nutzt** Qdrant aus Stack-D |
| Stack-H | `extension-mcp-servers-services` | Dev Dito **stellt** MCP Server bereit |
| Stack-I | `extension-leonidas-services` | Leonidas **konsumiert** Dev Dito Services |

---

## Multi-Stack-Architektur (Gesamtsystem)

```
<INFRASTRUCTURE_STACKS>
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │                    SHARED DOCKER NETWORK (external: true)                    │
  ├─────────────────────────────────────────────────────────────────────────────┤
  │                                                                             │
  │  ┌───────────────────┐   ┌───────────────────┐   ┌───────────────────────┐  │
  │  │ Stack-A           │   │ Stack-B           │   │ Stack-C               │  │
  │  │ wiki-sandbox      │   │ wiki-core-services│   │ extensions-additional │  │
  │  │                   │   │                   │   │                       │  │
  │  │ • wiki-instance   │   │ • keycloak-server │   │ • nginx-proxy         │  │
  │  │   (plain DokuWiki)│   │ • (redis-cache)   │   │ • redis-cache         │  │
  │  │                   │   │ • (php-fpm)       │   │ • scalekit-auth       │  │
  │  │                   │   │ • (nginx-proxy)   │   │ • n8n-workflows       │  │
  │  └───────────────────┘   └───────────────────┘   └───────────────────────┘  │
  │                                                                             │
  │  ┌───────────────────┐   ┌───────────────────┐   ┌───────────────────────┐  │
  │  │ Stack-D           │   │ Stack-E           │   │ Stack-F               │  │
  │  │ ai-core-services  │   │ ai-evaluation     │   │ observability         │  │
  │  │                   │   │                   │   │                       │  │
  │  │ • lmstudio/ollama │   │ • mlflow-server   │   │ • prometheus          │  │
  │  │ • qdrant-main-db  │   │ • ragas-server    │   │ • grafana             │  │
  │  │ • (qdrant-extra)  │   │ • prometheus      │   │                       │  │
  │  │                   │   │ • grafana         │   │                       │  │
  │  └───────────────────┘   └───────────────────┘   └───────────────────────┘  │
  │                                                                             │
  │  ┌───────────────────────────────────────────────────────────────────────┐  │
  │  │ Stack-G: extension-dev-dito-services [DIESES REPOSITORY]              │  │
  │  │                                                                       │  │
  │  │  dev-dito-core          Pipeline-Module (dev-dito-module-*)           │  │
  │  │  ┌────────────────┐     ┌──────────┐ ┌──────────┐ ┌──────────┐        │  │
  │  │  │ DokuWiki Plugin│     │ parser   │ │ embedder │ │ indexer  │        │  │
  │  │  │ + Admin Pages  │     │ (01)     │ │ (03)     │ │ (init)   │        │  │
  │  │  │ + Button UI    │     └──────────┘ └──────────┘ └──────────┘        │  │
  │  │  └────────────────┘                                                   │  │
  │  └───────────────────────────────────────────────────────────────────────┘  │
  │                                                                             │
  │  ┌───────────────────┐   ┌───────────────────────────────────────────────┐  │
  │  │ Stack-H           │   │ Stack-I                                       │  │
  │  │ mcp-servers       │   │ extension-leonidas-services                   │  │
  │  │                   │   │                                               │  │
  │  │ • semantic-search │   │ • leonidas-core (DokuWiki AI Chat Frontend)   │  │
  │  │   -wiki-core      │   │ • leonidas-module-helper                      │  │
  │  │ • (remote-mcp)    │   │                                               │  │
  │  └───────────────────┘   └───────────────────────────────────────────────┘  │
  │                                                                             │
  └─────────────────────────────────────────────────────────────────────────────┘
</INFRASTRUCTURE_STACKS>
```

---

## Shared Docker Network

**KRITISCH:** Alle Stacks muessen dasselbe externe Netzwerk verwenden!

```yaml
# In JEDEM docker-compose.yml:
networks:
  leonidas-network:
    external: true

# Netzwerk einmalig erstellen:
# docker network create leonidas-network
```

### Service Discovery

| Service | Container Name | Erreichbar via |
|---------|---------------|----------------|
| Qdrant (Stack-D) | `qdrant-main-vector-db` | `qdrant-main-vector-db:6333` |
| MCP Server (Stack-H) | `semantic-search-wiki-core` | `semantic-search-wiki-core:3000` |
| Keycloak (Stack-B) | `keycloak-server` | `keycloak-server:8080` |
| Wiki Sandbox (Stack-A) | `wiki-sandbox` | `wiki-sandbox:80` |
| Dev Dito Wiki (Stack-G) | `dev-dito-wiki` | `dev-dito-wiki:80` |

---

## Dev Dito Stack im Detail

### Stack-G Komponenten

```
<STACK_G name="extension-dev-dito-services">
  <CORE_SERVICE name="dev-dito-core">
    <type>DokuWiki Action Plugin</type>
    <location>./dokuwiki_plugin/</location>
    <responsibilities>
      - Admin-Seiten im Wiki (devdito:dashboard, devdito:services, etc.)
      - Button-UI fuer Service-Steuerung
      - AJAX-Endpoints fuer Backend-Kommunikation
    </responsibilities>
  </CORE_SERVICE>
  
  <PIPELINE_MODULES>
    <module name="01_wiki_fetcher" location="./pipeline/01_wiki_fetcher/">
      Holt Wiki-Inhalte via JSON-RPC API
    </module>
    <module name="02_deep_evaluation" location="./pipeline/02_deep_evaluation/">
      Analysiert und bewertet geholte Inhalte
    </module>
    <module name="03_embeddings_creator" location="./pipeline/03_embeddings_creator/">
      Erstellt Embeddings mit OpenAI text-embedding-3-large
    </module>
    <module name="04_deploy" location="./pipeline/04_deploy/">
      Transfer der Embeddings zum Remote-Server (Raspberry Pi)
    </module>
  </PIPELINE_MODULES>
  
  <BACKEND_SERVICES location="./backend_services/">
    <service name="wiki_dev_mcp_server">
      MCP Server (JSON-RPC) - wird in Stack-H deployed
    </service>
    <service name="qdrant_db">
      Qdrant Init-Container - initialisiert Collection in Stack-D's Qdrant
    </service>
  </BACKEND_SERVICES>
</STACK_G>
```

### docker-compose.yml (Stack-G)

```yaml
# backend_services/docker-compose.yml
version: '3.8'

services:
  # Qdrant Init - Laedt Embeddings in Stack-D's Qdrant
  qdrant_init:
    build: ./qdrant_db
    container_name: devdito_qdrant_init
    depends_on:
      - qdrant_db  # Aus Stack-D!
    environment:
      - QDRANT_HOST=qdrant-main-vector-db  # Stack-D Container
      - COLLECTION_NAME=wiki_embeddings
    volumes:
      - ../data/embeddings:/data/embeddings:ro
    networks:
      - leonidas-network

  # MCP Server - Semantic Search fuer Leonidas
  wiki_mcp_server:
    build: ./wiki_dev_mcp_server
    container_name: devdito_mcp_server
    ports:
      - "3000:3000"
    depends_on:
      - qdrant_db  # Aus Stack-D!
    environment:
      - QDRANT_HOST=qdrant-main-vector-db
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    networks:
      - leonidas-network

networks:
  leonidas-network:
    external: true
```

---

## Abhaengigkeiten zu anderen Stacks

### Dev Dito NUTZT (Dependencies)

| Stack | Service | Verwendung |
|-------|---------|-----------|
| **Stack-D** | `qdrant-main-vector-db` | Speichert Wiki-Embeddings |
| **Stack-D** | `lmstudio/ollama` | LLM fuer Evaluation (optional) |
| **Stack-B** | `keycloak-server` | Auth fuer Admin-Zugriff |

### Dev Dito STELLT BEREIT (Provides)

| Service | Consumer | Zweck |
|---------|----------|-------|
| `devdito_mcp_server` | Stack-H, Stack-I | MCP Tools (semantic_search) |
| `qdrant_init` | Stack-D | Initialisiert wiki_embeddings Collection |
| Pipeline Scripts | Manual/N8N | Wiki-Content-Processing |

### Abhaengigkeitsdiagramm

```
                    ┌─────────────────┐
                    │    Stack-D      │
                    │ qdrant-main-db  │
                    │ ollama/lmstudio │
                    └────────┬────────┘
                             │
              nutzt Qdrant   │   nutzt LLM (optional)
                             ▼
          ┌──────────────────────────────────────┐
          │           Stack-G (DEV DITO)          │
          │                                       │
          │  ┌─────────────┐  ┌────────────────┐  │
          │  │ Plugin      │  │ Pipeline       │  │
          │  │ (Admin UI)  │  │ (01-04)        │  │
          │  └─────────────┘  └────────────────┘  │
          │                                       │
          │  ┌─────────────┐  ┌────────────────┐  │
          │  │ MCP Server  │  │ Qdrant Init    │  │
          │  └──────┬──────┘  └────────────────┘  │
          └─────────┼─────────────────────────────┘
                    │
      stellt MCP    │   Tools bereit
                    ▼
          ┌─────────────────┐     ┌─────────────────┐
          │    Stack-H      │     │    Stack-I      │
          │ MCP Servers     │────▶│ Leonidas        │
          │ (Aggregation)   │     │ (AI Chat UI)    │
          └─────────────────┘     └─────────────────┘
```

---

## Vermeidung von Duplikaten

### NICHT DUPLIZIEREN - Diese Services existieren bereits

| Service | Existiert in | NICHT in Dev Dito |
|---------|-------------|-------------------|
| `qdrant_db` | Stack-D | Nur `qdrant_init` verwenden |
| `prometheus` | Stack-E, Stack-F | Nicht erneut erstellen |
| `grafana` | Stack-E, Stack-F | Nicht erneut erstellen |
| `keycloak` | Stack-B | Nur nutzen, nicht neu erstellen |
| `nginx` | Stack-B, Stack-C | Nur nutzen |

### Checkliste vor Implementierung

```
[ ] Service existiert bereits in anderem Stack?
    → JA: depends_on + network verbinden
    → NEIN: In Stack-G implementieren

[ ] Container-Name bereits vergeben?
    → Eindeutige Namen: devdito_* Praefix verwenden

[ ] Port bereits belegt?
    → docker ps pruefen
    → Alternativen Port waehlen oder Service teilen

[ ] Embedding-Pipeline laeuft bereits?
    → Pipeline-Module sind Scripts, keine dauerhaften Services
    → Koennen on-demand ausgefuehrt werden
```

---

## Entwicklungsrichtlinien

### Container Naming Convention

```
Stack-G Container:
  devdito_*           # Alle Dev Dito eigenen Container

Beispiele:
  devdito_qdrant_init
  devdito_mcp_server
  devdito_wiki (falls eigene Wiki-Instanz)
```

### Port-Zuweisung (Stack-G reserviert)

| Port | Service | Beschreibung |
|------|---------|--------------|
| 3000 | MCP Server | JSON-RPC Endpoint |
| 3001 | (Reserve) | Weitere MCP Endpoints |
| 8085 | (Reserve) | Dev Dito Admin API |

### Pfad-Konventionen

```
D:\_Repositories\_Diploma_Thesis_Repositories\dev_dito\
├── backend_services/          # Docker Services
├── dokuwiki_plugin/           # DokuWiki Plugin Code
├── pipeline/                  # Processing Pipeline
│   ├── 01_wiki_fetcher/
│   ├── 02_deep_evaluation/
│   ├── 03_embeddings_creator/
│   └── 04_deploy/
├── data/                      # Runtime Data (gitignored)
│   ├── embeddings/
│   ├── fetched_wiki/
│   └── evaluation_reports/
├── config/                    # Konfigurationsdateien
└── docs/                      # Dokumentation
```

### Environment Variables

```bash
# .env (gitignored)
OPENAI_API_KEY=sk-...
QDRANT_HOST=qdrant-main-vector-db
QDRANT_PORT=6333
COLLECTION_NAME=wiki_embeddings
MCP_SERVER_PORT=3000

# Remote Deploy
PI_HOST=192.168.x.x
PI_USER=pi
PI_DEPLOY_PATH=/home/pi/leonidas/embeddings
```

---

## Aktuell laufende Container

Stand: 2026-01-24

```
NAMES                       STATUS          PORTS
dev-dito-wiki               Up (healthy)    8080:80
wiki-sandbox                Up (healthy)    8090:80
semantic-search-wiki-core   Up (unhealthy)  3000:3000
qdrant-main-vector-db       Up              6333-6334
keycloak-server             Up (healthy)    8081:8080
```

**Hinweis:** `semantic-search-wiki-core` ist "unhealthy" - muss untersucht werden.

---

## Referenzen

- [Hauptarchitektur-Doku](./docs/architecture.md) - Detaillierte Komponentenbeschreibung
- [Pipeline Manager Plan](./planning/dev_dito_pipeline_manager.md) - Pipeline-Entwicklungsplan
- [Repository Setup Plan](./planning/dev_dito_repository_setup.md) - Initiales Setup

---

*Dokumentation fuer AI-gestuetzte Entwicklung und SpecKit-Planung*
