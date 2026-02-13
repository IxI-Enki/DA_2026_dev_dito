# Dev Dito & Leonidas - Architektur Dokumentation

> **Stand:** 2026-01-24  
> **Version:** 0.1.0-alpha  
> **Autor:** Jan Ritt (IxI-Enki)

---

## Inhaltsverzeichnis

- [Dev Dito \& Leonidas - Architektur Dokumentation](#dev-dito--leonidas---architektur-dokumentation)
  - [Inhaltsverzeichnis](#inhaltsverzeichnis)
  - [Uebersicht](#uebersicht)
    - [Rollen-Zusammenfassung](#rollen-zusammenfassung)
  - [Repository Struktur](#repository-struktur)
  - [Docker Container Architektur](#docker-container-architektur)
    - [Container Uebersicht](#container-uebersicht)
    - [docker-compose.yml Struktur](#docker-composeyml-struktur)
  - [Dev Dito - Service Addon](#dev-dito---service-addon)
    - [Zweck und Rolle](#zweck-und-rolle)
    - [Plugin Informationen](#plugin-informationen)
    - [Dev Dito Wiki-Seiten](#dev-dito-wiki-seiten)
    - [Funktionalitaet](#funktionalitaet)
  - [Leonidas - AI Chat Frontend](#leonidas---ai-chat-frontend)
    - [Zweck und Rolle](#zweck-und-rolle-1)
    - [Plugin Informationen](#plugin-informationen-1)
    - [Komponenten](#komponenten)
  - [MCP Server (von Dev Dito bereitgestellt)](#mcp-server-von-dev-dito-bereitgestellt)
    - [Server Informationen](#server-informationen)
    - [Verfuegbare Tools (fuer Leonidas)](#verfuegbare-tools-fuer-leonidas)
    - [Kommunikationsfluss](#kommunikationsfluss)
  - [Qdrant Vector Database (von Dev Dito bereitgestellt)](#qdrant-vector-database-von-dev-dito-bereitgestellt)
    - [Collection Schema](#collection-schema)
    - [Embedding Pipeline (Dev Dito Verantwortung)](#embedding-pipeline-dev-dito-verantwortung)
  - [Netzwerk-Kommunikation](#netzwerk-kommunikation)
  - [Konfigurationsreferenz](#konfigurationsreferenz)
    - [DokuWiki Admin Settings](#dokuwiki-admin-settings)
  - [Zusammenfassung der Architektur](#zusammenfassung-der-architektur)
  - [Changelog](#changelog)
    - [2026-01-24](#2026-01-24)

---

## Uebersicht

Dieses Dokument beschreibt die aktuelle Architektur des **Dev Dito** und **Leonidas** Systems.

**Wichtig:**
- **Dev Dito** = Service Addon mit eigenen Wiki-Seiten zur Verwaltung der Backend-Services
- **Leonidas** = Frontend-Plugin (AI Chat), das Dev Dito's Backend-Services nutzt

Dev Dito stellt die Backend-Infrastruktur bereit UND bietet ein interaktives Admin-Interface direkt im Wiki, ueber das Services per Button-Klick gesteuert, ueberwacht und evaluiert werden koennen.

```sketch
┌────────────────────────────────────────────────────────────────────────┐
│                         DokuWiki Installation                          │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                  Leonidas Plugin (Frontend)                      │  │
│  │                                                                  │  │
│  │  • Sidepanel mit Chat-UI        • LLM Anfragen/Antworten         │  │
│  │  • Streaming (SSE)              • Wiki-Kontext Integration       │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                     │                                  │
│                                     │ nutzt Backend-Services           │
│                                     ▼                                  │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │               Dev Dito Plugin (Service Addon)                    │  │
│  │                                                                  │  │
│  │  ┌────────────────────────────────────────────────────────────┐  │  │
│  │  │           EIGENE WIKI-SEITEN (Admin UI)                    │  │  │
│  │  │                                                            │  │  │
│  │  │  devdito:dashboard    - Uebersicht & Quick Actions         │  │  │
│  │  │  devdito:services     - [Start] [Stop] [Restart] Buttons   │  │  │
│  │  │  devdito:monitoring   - Live-Metriken & Graphen            │  │  │
│  │  │  devdito:embeddings   - [Re-Index] [Export] Pipeline       │  │  │
│  │  │  devdito:config       - API-Keys & Einstellungen           │  │  │
│  │  │  devdito:logs         - Live Logs & Debugging              │  │  │
│  │  └────────────────────────────────────────────────────────────┘  │  │
│  │                              │                                   │  │
│  │           steuert per Button │                                   │  │
│  │                              ▼                                   │  │
│  │  ┌────────────────────────────────────────────────────────────┐  │  │
│  │  │              Backend Services (Docker)                     │  │  │
│  │  │                                                            │  │  │
│  │  │  ┌───────────────┐ ┌───────────────┐ ┌───────────────┐     │  │  │
│  │  │  │ MCP Server    │ │  Qdrant DB    │ │ LLM Server    │     │  │  │
│  │  │  │ Port: 3000    │ │  Port: 6333   │ │ Port: 11434   │     │  │  │
│  │  │  │ [Start][Stop] │ │ [Start][Stop] │ │ [HealthCheck] │     │  │  │
│  │  │  └───────────────┘ └───────────────┘ └───────────────┘     │  │  │
│  │  └────────────────────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

### Rollen-Zusammenfassung

| Komponente              | Typ              | Verantwortlichkeit                                                    |
| ----------------------- | ---------------- | --------------------------------------------------------------------- |
| **Leonidas**            | Frontend Plugin  | AI Chat UI, Benutzer-Interaktion, LLM Kommunikation                   |
| **Dev Dito**            | Service Addon    | Wiki-Seiten mit Buttons zur Service-Steuerung, Monitoring, Evaluation |
| **wiki_dev_mcp_server** | Backend Service  | Semantische Suche via MCP (gesteuert durch Dev Dito)                  |
| **qdrant_db**           | Backend Service  | Vektor-Datenbank fuer Embeddings (gesteuert durch Dev Dito)           |
| **Ollama/LMStudio**     | Externer Service | LLM Inference (Health-Check durch Dev Dito)                           |

---

## Repository Struktur

<directory name="internal_leonidas" description="Hauptrepository fuer Leonidas DokuWiki Extension">
  <directory name="02_dev_dito" description="Dev Dito - Service Addon mit eigenen Wiki-Seiten">
    <file name="architecture_dev_dito.md" description="Diese Architekturdokumentation"/>
    <file name="dev_dito_icon.png" description="Plugin Icon"/>
    <directory name="_development_of_dev_dito" description="Entwicklungsquellen fuer Backend">
      <directory name="backend_services" description="Docker-Backend-Services (von Dev Dito verwaltet)">
        <directory name="embeddings" description="Vorberechnete Wiki-Embeddings">
          <file name="embedded_chunks.jsonl" description="Wiki-Chunks mit Vektoren (JSONL Format)"/>
        </directory>
        <directory name="qdrant_db" description="Qdrant Initialisierungs-Container">
          <file name="Dockerfile" description="Container-Build fuer Python-Init-Script"/>
          <file name="init_collection.py" description="Qdrant Collection Setup + Embedding Import"/>
          <file name="requirements.txt" description="Python Dependencies: qdrant-client"/>
        </directory>
        <directory name="wiki_dev_mcp_server" description="MCP Server fuer Leonidas">
          <file name="Dockerfile" description="Container-Build fuer FastAPI Server"/>
          <file name="server.py" description="JSON-RPC 2.0 MCP Server - stellt Tools fuer Leonidas bereit"/>
          <file name="requirements.txt" description="Python Dependencies: fastapi, qdrant-client, openai"/>
        </directory>
      </directory>
      <directory name="devdito" description="DokuWiki Plugin Source (Service Gateway UI)">
        <file name="action.php" description="Service Gateway Logik"/>
        <file name="admin.php" description="Admin-Interface fuer Backend-Konfiguration"/>
        <file name="plugin.info.txt" description="Plugin Metadaten"/>
      </directory>
    </directory>
    <directory name=".planing_dev_dito" description="Planungsdokumente"/>
    <directory name="final_full_dev_dito_extension_to_download_and_install_in_dokuwiki" description="Finales Plugin-Paket"/>
  </directory>
  
  <directory name="development/first_own_dokuwiki" description="Docker Compose Stack fuer DokuWiki">
    <file name="docker-compose.yml" description="Haupt Docker Compose - startet alle Backend-Services"/>
    <file name="docker-compose.ci.yml" description="CI/CD Konfiguration"/>
    <directory name="plugins_dev" description="Entwicklungs-Plugins (gemounted in Container)">
      <directory name="leonidas" description="Leonidas - AI Chat Frontend Plugin">
        <file name="action.php" description="Frontend-Logik: Sidepanel, Chat-UI, Streaming"/>
        <file name="plugin.info.txt" description="Plugin Metadaten"/>
        <directory name="lib" description="PHP Bibliotheken fuer LLM-Kommunikation">
          <file name="MCPToolProxy.php" description="Verbindung zu Dev Dito's MCP Server"/>
          <file name="LLMClient.php" description="LLM Provider Abstraction (nutzt Dev Dito Backend)"/>
          <file name="LLMOrchestrator.php" description="Request Orchestration"/>
          <file name="StreamingHandler.php" description="SSE Response Streaming"/>
          <file name="ResponseFormatter.php" description="Antwort-Formatierung"/>
          <file name="ConfigLoader.php" description="YAML Config Loading"/>
        </directory>
        <directory name="conf" description="Konfiguration">
          <file name="default.php" description="Standard-Einstellungen"/>
          <file name="metadata.php" description="Admin UI Schema"/>
          <directory name="yaml" description="YAML Konfigurationsdateien">
            <file name="prompts.yaml" description="System-Prompts fuer LLM"/>
            <file name="keywords.yaml" description="Keyword Definitions"/>
            <file name="namespaces.yaml" description="Wiki Namespace Mapping"/>
          </directory>
        </directory>
        <directory name="tests" description="PHPUnit Tests"/>
        <directory name="e2e" description="Playwright E2E Tests"/>
        <directory name="benchmarks" description="Performance Benchmarks"/>
      </directory>
      <directory name="devdito" description="Dev Dito - Backend Service Gateway Plugin">
        <file name="action.php" description="Service Gateway: Health Checks, Status, Metriken"/>
        <file name="admin.php" description="Admin-Interface: Backend-Konfiguration, API-Keys"/>
        <file name="plugin.info.txt" description="Plugin Metadaten"/>
        <directory name="conf" description="Konfiguration fuer Backend-Services">
          <file name="default.php" description="Standard-Einstellungen (Service URLs, etc.)"/>
          <file name="metadata.php" description="Admin UI Schema"/>
        </directory>
        <directory name="lang" description="Sprachdateien"/>
      </directory>
      <directory name="htlthemesettings" description="HTL Theme Settings Plugin">
        <file name="action.php" description="Theme-Switching Logik"/>
        <file name="plugin.info.txt" description="Plugin Metadaten"/>
      </directory>
      <directory name="templates" description="DokuWiki Templates">
        <directory name="htl_leonidas_dark" description="HTL Dark Theme"/>
        <directory name="htl_leonidas_light" description="HTL Light Theme"/>
      </directory>
    </directory>
    <directory name="scripts" description="Hilfs-Scripts"/>
    <directory name="seeds" description="Initialisierungsdaten"/>
  </directory>
</directory>

---

## Docker Container Architektur

### Container Uebersicht

| Container             | Image                         | Ports      | Rolle              | Verwaltet durch |
| --------------------- | ----------------------------- | ---------- | ------------------ | --------------- |
| `dokuwiki`            | `linuxserver/dokuwiki:latest` | 8080:80    | DokuWiki + Plugins | -               |
| `keycloak`            | `keycloak/keycloak:25.0`      | 8081:8080  | OAuth2/OIDC        | -               |
| `qdrant_db`           | `qdrant/qdrant:v1.13.2`       | 6333, 6334 | Vector Database    | **Dev Dito**    |
| `qdrant_init`         | Custom Build                  | -          | Embedding-Import   | **Dev Dito**    |
| `wiki_dev_mcp_server` | Custom Build                  | 3000:3000  | MCP Server         | **Dev Dito**    |

**Hinweis:** Die Backend-Services (qdrant_db, wiki_dev_mcp_server) werden von **Dev Dito** bereitgestellt und verwaltet. **Leonidas** nutzt diese Services ueber Dev Dito's Gateway.

### docker-compose.yml Struktur

```yaml
services:
  # ====================================================
  # DokuWiki - Haupt-Webanwendung
  # Enthaelt Leonidas (Frontend) und Dev Dito (Gateway)
  # ====================================================
  dokuwiki:
    image: lscr.io/linuxserver/dokuwiki:latest
    container_name: dokuwiki
    volumes:
      # Leonidas Plugin (Frontend - AI Chat)
      - D:/_Repositories/year_2025_26/SYP_2025_26/leonie/internal_leonidas/development/first_own_dokuwiki/plugins_dev/leonidas:/config/dokuwiki/lib/plugins/leonidas
      # Dev Dito Plugin (Service Addon)
      - D:/_Repositories/year_2025_26/SYP_2025_26/leonie/internal_leonidas/development/first_own_dokuwiki/plugins_dev/devdito:/config/dokuwiki/lib/plugins/devdito
      # Theme Settings
      - D:/_Repositories/year_2025_26/SYP_2025_26/leonie/internal_leonidas/development/first_own_dokuwiki/plugins_dev/htlthemesettings:/config/dokuwiki/lib/plugins/htlthemesettings
    ports:
      - "${PORT}:80"  # Default: 8080

  # ====================================================
  # BACKEND SERVICES (von Dev Dito bereitgestellt)
  # ====================================================

  # Qdrant - Vector Database fuer semantische Suche
  qdrant_db:
    image: qdrant/qdrant:v1.13.2
    container_name: qdrant_db
    ports:
      - "6333:6333"  # REST API
      - "6334:6334"  # gRPC

  # Qdrant Init - Einmaliger Embedding-Import
  qdrant_init:
    build:
      context: D:/_Repositories/year_2025_26/SYP_2025_26/leonie/internal_leonidas/02_dev_dito/_development_of_dev_dito/backend_services/qdrant_db
    container_name: qdrant_init
    environment:
      - QDRANT_HOST=qdrant_db
      - COLLECTION_NAME=wiki_embeddings
      - EMBEDDINGS_FILE=/data/embeddings/embedded_chunks.jsonl
    volumes:
      - D:/_Repositories/year_2025_26/SYP_2025_26/leonie/internal_leonidas/02_dev_dito/_development_of_dev_dito/backend_services/embeddings:/data/embeddings:ro

  # MCP Server - Stellt Tools fuer Leonidas bereit
  wiki_dev_mcp_server:
    build:
      context: D:/_Repositories/year_2025_26/SYP_2025_26/leonie/internal_leonidas/02_dev_dito/_development_of_dev_dito/backend_services/wiki_dev_mcp_server
    container_name: wiki_dev_mcp_server
    environment:
      - QDRANT_HOST=qdrant_db
      - COLLECTION_NAME=wiki_embeddings
      - OPENAI_API_KEY=${OPENAI_API_KEY}
    ports:
      - "3000:3000"

volumes:
  qdrant_storage:
```

---

## Dev Dito - Service Addon

### Zweck und Rolle

**Dev Dito ist ein Service Addon** - ein zusaetzliches DokuWiki-Plugin, das:

1. **Backend-Services bereitstellt** - Qdrant, MCP Server, Embedding-Pipeline (Docker)
2. **Eigene Wiki-Seiten hat** - Admin-Interface direkt im Wiki
3. **Interaktive Steuerung bietet** - Services per Button-Klick starten/stoppen/ueberwachen
4. **Leonidas unterstuetzt** - Stellt die Backend-Infrastruktur bereit, die Leonidas nutzt

### Plugin Informationen

```text
base    devdito
author  Jan Ritt (IxI-Enki)
email   jan.ritt@htl-leonding.ac.at
name    Dev Dito - Service Gateway Extension
desc    Service Gateway for AI services (Ollama, LMStudio, Qdrant).
        Manages connections, API keys, health checks, metrics visualization,
        and wiki content processing pipelines.
version 0.1.0-alpha
```

### Dev Dito Wiki-Seiten

Dev Dito erstellt eigene Seiten im DokuWiki, ueber die Administratoren die Backend-Services verwalten koennen:

<wiki_pages namespace="devdito">
  <page name="devdito:dashboard" title="Dev Dito Dashboard">
    <description>Hauptseite mit Uebersicht aller Services und deren Status</description>
    <features>
      <feature>Live-Status aller Backend-Services (gruen/rot Indikatoren)</feature>
      <feature>Quick-Action Buttons fuer haeufige Operationen</feature>
      <feature>Letzte Aktivitaeten und Logs</feature>
    </features>
  </page>
  
  <page name="devdito:services" title="Service Management">
    <description>Detaillierte Verwaltung der einzelnen Backend-Services</description>
    <buttons>
      <button action="start_qdrant">Qdrant starten</button>
      <button action="stop_qdrant">Qdrant stoppen</button>
      <button action="restart_qdrant">Qdrant neustarten</button>
      <button action="start_mcp">MCP Server starten</button>
      <button action="stop_mcp">MCP Server stoppen</button>
      <button action="restart_mcp">MCP Server neustarten</button>
      <button action="health_check_all">Alle Services pruefen</button>
    </buttons>
  </page>
  
  <page name="devdito:monitoring" title="Monitoring & Metriken">
    <description>Echtzeit-Ueberwachung und Metriken-Visualisierung</description>
    <features>
      <feature>Latenz-Graphen (MCP Server, Qdrant, LLM)</feature>
      <feature>Request-Counter und Durchsatz</feature>
      <feature>Error-Rate und Fehler-Logs</feature>
      <feature>Resource-Nutzung (CPU, Memory)</feature>
    </features>
  </page>
  
  <page name="devdito:embeddings" title="Embedding Pipeline">
    <description>Verwaltung der Wiki-Embeddings fuer semantische Suche</description>
    <buttons>
      <button action="reindex_all">Kompletter Re-Index</button>
      <button action="reindex_namespace">Namespace neu indexieren</button>
      <button action="check_coverage">Index-Abdeckung pruefen</button>
      <button action="export_embeddings">Embeddings exportieren</button>
    </buttons>
    <info>
      <field>Anzahl indexierter Seiten</field>
      <field>Anzahl Chunks in Qdrant</field>
      <field>Letzter Index-Zeitpunkt</field>
      <field>Fehlende Seiten</field>
    </info>
  </page>
  
  <page name="devdito:config" title="Konfiguration">
    <description>API-Keys, URLs und weitere Einstellungen</description>
    <sections>
      <section name="API Keys">OpenAI Key, andere Provider</section>
      <section name="Service URLs">Qdrant, MCP, LLM Server URLs</section>
      <section name="Timeouts">Request-Timeouts fuer alle Services</section>
      <section name="Logging">Log-Level, Log-Rotation</section>
    </sections>
  </page>
  
  <page name="devdito:logs" title="Logs & Debugging">
    <description>Service-Logs und Debug-Informationen</description>
    <features>
      <feature>Live Log-Stream (WebSocket)</feature>
      <feature>Log-Filter nach Service/Level</feature>
      <feature>Log-Download (JSON/Text)</feature>
      <feature>Debug-Modus aktivieren/deaktivieren</feature>
    </features>
  </page>
</wiki_pages>

### Funktionalitaet

<component name="devdito" type="service-addon">
  <description>
    Dev Dito ist ein Service Addon fuer DokuWiki. Es stellt Backend-Services
    bereit und bietet ein interaktives Admin-Interface direkt im Wiki, ueber
    das Services per Button-Klick gesteuert und ueberwacht werden koennen.
  </description>
  
  <responsibilities>
    <responsibility name="Backend Provisioning">
      Stellt alle Backend-Services bereit (Docker Container)
    </responsibility>
    <responsibility name="Interactive Control">
      Services per Button-Klick starten, stoppen, neustarten
    </responsibility>
    <responsibility name="Real-time Monitoring">
      Live-Status, Metriken und Logs direkt im Wiki
    </responsibility>
    <responsibility name="Evaluation Tools">
      Performance-Tests, Health-Checks, Coverage-Reports
    </responsibility>
    <responsibility name="Content Pipeline">
      Wiki-Export, Chunking, Embedding-Generierung, Qdrant-Import
    </responsibility>
  </responsibilities>
  
  <backend_services>
    <service name="qdrant_db" type="vector-database">
      <description>Vector-Datenbank fuer Wiki-Embeddings</description>
      <controls>start, stop, restart, health-check, clear-data</controls>
    </service>
    <service name="wiki_dev_mcp_server" type="mcp-server">
      <description>JSON-RPC Server mit MCP Tools</description>
      <controls>start, stop, restart, health-check, list-tools</controls>
    </service>
    <service name="ollama" type="llm-server" external="true">
      <description>Lokaler LLM Server (extern)</description>
      <controls>health-check, list-models, test-query</controls>
    </service>
    <service name="lmstudio" type="llm-server" external="true">
      <description>LM Studio API (extern)</description>
      <controls>health-check, list-models, test-query</controls>
    </service>
  </backend_services>
  
  <button_actions>
    <action name="start_service" description="Service starten">
      Startet einen Backend-Service (Docker Container)
    </action>
    <action name="stop_service" description="Service stoppen">
      Stoppt einen laufenden Service
    </action>
    <action name="restart_service" description="Service neustarten">
      Restart mit Cleanup
    </action>
    <action name="health_check" description="Health Check">
      Prueft ob Service erreichbar und funktional ist
    </action>
    <action name="view_logs" description="Logs anzeigen">
      Zeigt aktuelle Logs des Services
    </action>
    <action name="run_benchmark" description="Benchmark ausfuehren">
      Performance-Test mit Metriken
    </action>
    <action name="reindex" description="Re-Index">
      Wiki-Seiten neu in Qdrant indexieren
    </action>
  </button_actions>
  
  <configuration>
    <setting name="devdito_enabled" type="onoff" default="1">
      Service Addon aktivieren/deaktivieren
    </setting>
    <setting name="devdito_mcp_url" type="string" default="http://wiki_dev_mcp_server:3000">
      URL des MCP Servers
    </setting>
    <setting name="devdito_qdrant_url" type="string" default="http://qdrant_db:6333">
      URL der Qdrant Vector Database
    </setting>
    <setting name="devdito_llm_url" type="string" default="http://host.docker.internal:11434">
      URL des LLM Servers (Ollama/LMStudio)
    </setting>
    <setting name="devdito_auto_healthcheck" type="onoff" default="1">
      Automatische Health-Checks im Hintergrund
    </setting>
    <setting name="devdito_log_level" type="multichoice" default="info">
      Log-Level: debug, info, warn, error
    </setting>
  </configuration>
</component>

---

## Leonidas - AI Chat Frontend

### Zweck und Rolle

**Leonidas ist das Frontend-Plugin**, das:

1. **Chat-UI bereitstellt** - Sidepanel mit Chat-Interface
2. **LLM kommuniziert** - Sendet Anfragen, streamt Antworten
3. **Dev Dito's Backend nutzt** - MCP Tools, Qdrant Suche
4. **Wiki-Kontext integriert** - ACL-aware Antworten

### Plugin Informationen

```text
base    leonidas
author  HTL Leonding
email   dev@htl-leonding.ac.at
name    Leonidas Plugin
desc    AI-powered Sidepanel-Chat with MCP integration and ACL-aware responses
version 0.1.0-alpha
```

### Komponenten

<component name="leonidas" type="frontend-plugin">
  <description>
    Leonidas ist das AI Chat Frontend Plugin fuer DokuWiki. Es bietet ein
    Sidepanel mit Chat-Interface und nutzt die Backend-Services, die von
    Dev Dito bereitgestellt werden.
  </description>
  
  <dependencies>
    <dependency name="Dev Dito" required="true">
      Leonidas benoetigt Dev Dito's Backend-Services (MCP Server, Qdrant)
    </dependency>
    <dependency name="LLM Server" required="true">
      Ollama oder LMStudio (konfiguriert ueber Dev Dito)
    </dependency>
  </dependencies>
  
  <library name="MCPToolProxy">
    <file>lib/MCPToolProxy.php</file>
    <purpose>
      Verbindet sich mit Dev Dito's MCP Server (wiki_dev_mcp_server).
      Ruft Tools wie semantic_wiki_search auf.
    </purpose>
    <methods>
      <method name="discover_tools()">Tools vom MCP Server auflisten</method>
      <method name="invoke_tool($name, $args)">Tool ausfuehren</method>
      <method name="get_openai_format()">Tools im OpenAI Format</method>
    </methods>
  </library>
  
  <library name="LLMClient">
    <file>lib/LLMClient.php</file>
    <purpose>
      Kommuniziert mit LLM Servern (Ollama, LMStudio).
      URLs werden ueber Dev Dito konfiguriert.
    </purpose>
  </library>
  
  <library name="StreamingHandler">
    <file>lib/StreamingHandler.php</file>
    <purpose>
      Server-Sent Events (SSE) fuer Echtzeit-Streaming von LLM-Antworten.
    </purpose>
  </library>
  
  <library name="LLMOrchestrator">
    <file>lib/LLMOrchestrator.php</file>
    <purpose>
      Koordiniert den Request-Flow:
      1. Wiki-Kontext extrahieren
      2. MCP Tools aufrufen (via Dev Dito)
      3. LLM Query ausfuehren
      4. Antwort streamen
    </purpose>
  </library>
  
  <configuration>
    <setting name="leonidas_llm_provider" type="multichoice" default="ollama">
      LLM Provider: ollama, lmstudio
    </setting>
    <setting name="leonidas_llm_url" type="string" default="http://host.docker.internal:11434">
      URL des LLM Servers (Fallback, primaer ueber Dev Dito)
    </setting>
    <setting name="leonidas_mcp_url" type="string" default="http://wiki_dev_mcp_server:3000">
      MCP Server URL (von Dev Dito bereitgestellt)
    </setting>
    <setting name="leonidas_enable_streaming" type="onoff" default="1">
      SSE Streaming aktivieren
    </setting>
  </configuration>
</component>

---

## MCP Server (von Dev Dito bereitgestellt)

### Server Informationen

```python
# wiki_dev_mcp_server/server.py
# Dieser Server wird von Dev Dito bereitgestellt und verwaltet
name = "wiki-semantic-search-mcp"
version = "1.0.0"
protocol = "JSON-RPC 2.0"
transport = "HTTP POST"
port = 3000
```

### Verfuegbare Tools (fuer Leonidas)

<mcp_server name="wiki_dev_mcp_server" provided_by="Dev Dito">
  <tool name="semantic_wiki_search">
    <description>
      Semantische Suche im Wiki. Wird von Leonidas aufgerufen,
      um relevante Wiki-Inhalte fuer den Chat-Kontext zu finden.
    </description>
    <input_schema>
      {
        "type": "object",
        "properties": {
          "query": {"type": "string", "description": "Suchanfrage"},
          "top_k": {"type": "integer", "default": 5},
          "namespace_filter": {"type": "string", "description": "Optional"}
        },
        "required": ["query"]
      }
    </input_schema>
  </tool>
  
  <tool name="faceted_search">
    <description>
      Facettensuche - Alternative Suchmethode fuer Leonidas.
    </description>
  </tool>
</mcp_server>

### Kommunikationsfluss

```sketch
┌──────────────┐     Chat Query      ┌──────────────┐
│   Browser    │ ─────────────────▶  │   Leonidas   │
│   (User)     │                     │   (Frontend) │
└──────────────┘                     └──────┬───────┘
                                            │
                                            │ 1. Tool Call Request
                                            ▼
                               ┌────────────────────────┐
                               │  Dev Dito MCP Proxy    │
                               │  (MCPToolProxy.php)    │
                               └────────────┬───────────┘
                                            │
                                            │ 2. JSON-RPC
                                            ▼
                               ┌────────────────────────┐
                               │  wiki_dev_mcp_server   │
                               │  (Port 3000)           │
                               │  PROVIDED BY DEV DITO  │
                               └────────────┬───────────┘
                                            │
                                            │ 3. Vector Search
                                            ▼
                               ┌────────────────────────┐
                               │      qdrant_db         │
                               │  PROVIDED BY DEV DITO  │
                               └────────────────────────┘
```

---

## Qdrant Vector Database (von Dev Dito bereitgestellt)

### Collection Schema

```python
collection_name = "wiki_embeddings"
vector_dimension = 3072  # text-embedding-3-large
distance_metric = "Cosine"
```

### Embedding Pipeline (Dev Dito Verantwortung)

Die Embedding-Pipeline wird von Dev Dito verwaltet:

1. **Wiki-Export**: DokuWiki Seiten als Text exportieren
2. **Chunking**: Text in Abschnitte aufteilen (~512 Tokens)
3. **Embedding**: OpenAI `text-embedding-3-large` Modell
4. **Storage**: Vektoren + Metadaten in Qdrant speichern
5. **Re-Index**: Manuell ueber Dev Dito Admin-Interface

---

## Netzwerk-Kommunikation

```sketch
┌─────────────────────────────────────────────────────────────────────────┐
│                       Docker Network: default                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────┐       HTTP/AJAX       ┌────────────────────────────┐  │
│  │   Browser    │ ─────────────────────▶│     dokuwiki (8080)        │  │
│  │   (User)     │                       │  ┌──────────────────────┐  │  │
│  └──────────────┘                       │  │  Leonidas (Frontend) │  │  │
│                                         │  └──────────┬───────────┘  │  │
│                                         │             │              │  │
│                                         │  ┌──────────▼───────────┐  │  │
│                                         │  │  Dev Dito (Gateway)  │  │  │
│                                         │  └──────────┬───────────┘  │  │
│                                         └─────────────┼──────────────┘  │
│                                                       │                 │
│                        ┌──────────────────────────────┼──────────────┐  │
│                        │  DEV DITO BACKEND SERVICES   │              │  │
│                        │                              ▼              │  │
│                        │           ┌─────────────────────────────┐   │  │
│                        │           │  wiki_dev_mcp_server (3000) │   │  │
│                        │           └─────────────┬───────────────┘   │  │
│                        │                         │                   │  │
│                        │                         ▼                   │  │
│                        │           ┌─────────────────────────────┐   │  │
│                        │           │  qdrant_db (6333, 6334)     │   │  │
│                        │           └─────────────────────────────┘   │  │
│                        └─────────────────────────────────────────────┘  │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │  keycloak (8081) - OAuth2/OIDC fuer Authentifizierung             │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘

External (Host Network):
  - Ollama LLM Server: host.docker.internal:11434 (konfiguriert via Dev Dito)
  - LM Studio: host.docker.internal:1234 (konfiguriert via Dev Dito)
  - OpenAI API: api.openai.com (fuer Embeddings, API-Key via Dev Dito)
```

---

## Konfigurationsreferenz

### DokuWiki Admin Settings

| Plugin       | Setting                     | Default                             | Rolle                  |
| ------------ | --------------------------- | ----------------------------------- | ---------------------- |
| **devdito**  | `devdito_enabled`           | `1`                                 | Gateway aktivieren     |
| **devdito**  | `devdito_mcp_url`           | `http://wiki_dev_mcp_server:3000`   | MCP Server URL         |
| **devdito**  | `devdito_qdrant_url`        | `http://qdrant_db:6333`             | Qdrant URL             |
| **devdito**  | `devdito_llm_url`           | `http://host.docker.internal:11434` | LLM Server URL         |
| **leonidas** | `leonidas_llm_provider`     | `ollama`                            | LLM Provider           |
| **leonidas** | `leonidas_mcp_url`          | `http://wiki_dev_mcp_server:3000`   | MCP URL (von Dev Dito) |
| **leonidas** | `leonidas_enable_streaming` | `1`                                 | SSE aktivieren         |

---

## Zusammenfassung der Architektur

```sketch
┌─────────────────────────────────────────────────────────────────┐
│                         BENUTZER                                │
│                            │                                    │
│            ┌───────────────┴───────────────┐                    │
│            ▼                               ▼                    │
│  ┌─────────────────────┐      ┌─────────────────────────────┐   │
│  │     LEONIDAS        │      │        DEV DITO             │   │
│  │  (Frontend Plugin)  │      │    (Service Addon)          │   │
│  │                     │      │                             │   │
│  │  • Chat-Sidepanel   │      │  WIKI-SEITEN:               │   │
│  │  • LLM Kommunikation│      │  • devdito:dashboard        │   │
│  │  • Streaming (SSE)  │      │  • devdito:services         │   │
│  │  • Wiki-Kontext     │      │  • devdito:monitoring       │   │
│  │                     │      │  • devdito:embeddings       │   │
│  │  nutzt Backend ─────┼─────▶│  • devdito:config           │   │
│  │                     │      │  • devdito:logs             │   │
│  └─────────────────────┘      │                             │   │
│                               │  BUTTONS:                   │   │
│                               │  [Start] [Stop] [Restart]   │   │
│                               │  [Health Check] [Re-Index]  │   │
│                               │  [Export] [View Logs]       │   │
│                               └──────────────┬──────────────┘   │
│                                              │                  │
│                               steuert per    │ Button-Klick     │
│                                              ▼                  │
│                               ┌─────────────────────────────┐   │
│                               │    Backend Services         │   │
│                               │                             │   │
│                               │ MCP Server ◄──► Qdrant DB   │   │
│                               │      ▲              ▲       │   │
│                               │      │              │       │   │
│                               │ Ollama/LMStudio  Embeddings │   │
│                               └─────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Changelog

### 2026-01-24

- **Dokumentation korrigiert**: Dev Dito als **Service Addon** mit eigenen Wiki-Seiten beschrieben
- **Wiki-Seiten dokumentiert**: devdito:dashboard, devdito:services, devdito:monitoring, etc.
- **Button-Aktionen definiert**: Start/Stop/Restart, Health-Check, Re-Index, Export
- **Rollen geklaert**:
  - Leonidas = Frontend Plugin (AI Chat UI)
  - Dev Dito = Service Addon (Backend-Steuerung per Button-Klick im Wiki)
- **devdito**: Plugin umbenannt von `dev_dito` zu `devdito` (DokuWiki Naming Convention)
- **htlthemesettings**: Plugin umbenannt von `htl_theme_settings` zu `htlthemesettings`
- **Docker**: Backend-Services klar als "von Dev Dito gesteuert" markiert

---

*Dokumentation generiert am 2026-01-24*
