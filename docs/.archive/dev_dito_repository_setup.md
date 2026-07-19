---
name: Dev Dito Repository Setup
overview: Neues eigenstaendiges GitHub Repository fuer Dev Dito unter D:\_Repositories\_Diploma_Thesis_Repositories\dev_dito mit allen Pipeline-Komponenten, DokuWiki Plugin und Dokumentation.
todos:
  - id: create-repo-structure
    content: Repository-Verzeichnisstruktur unter D:\_Repositories\_Diploma_Thesis_Repositories\dev_dito erstellen
    status: completed
  - id: copy-wiki-fetcher
    content: Wiki Fetcher Scripts von techstack/dokuwiki/fetcher_json_rpc_api/script/ kopieren (NUR mature)
    status: completed
  - id: copy-deep-evaluation
    content: Deep Evaluation Scripts von techstack/dokuwiki/fetched_data_evaluation/script/ kopieren
    status: completed
  - id: copy-embeddings-creator
    content: Embeddings Creator von techstack/qdrant/embeddings_creator/ kopieren (NICHT .archived_*)
    status: completed
  - id: copy-backend-services
    content: Backend Services von 02_dev_dito/_development_of_dev_dito/backend_services/ kopieren
    status: completed
  - id: copy-dokuwiki-plugin
    content: DokuWiki Plugin von 02_dev_dito/_development_of_dev_dito/devdito/ kopieren
    status: completed
  - id: copy-docs-planning
    content: Dokumentation (architecture.md) und Planung (pipeline_manager.md) kopieren
    status: in_progress
  - id: create-new-files
    content: "Neue Dateien erstellen: README.md, docker-compose.yml, deploy scripts, .gitignore"
    status: pending
  - id: update-paths-configs
    content: Pfade in allen config.py und env.yaml Dateien auf neues Repository anpassen
    status: pending
  - id: init-git-github
    content: Git initialisieren und GitHub Repository IxI-Enki/DA_2026_dev_dito (privat) erstellen
    status: pending
  - id: cleanup-internal-leonidas
    content: 02_dev_dito aus legacy-wiki-repo entfernen, docker-compose.yml anpassen
    status: pending
---

# Dev Dito - Eigenstaendiges Repository

## Ziel-Repository

```path
D:\_Repositories\_Diploma_Thesis_Repositories\dev_dito\
```

GitHub Repository: `IxI-Enki/DA_2026_dev_dito` (privat, neu zu erstellen)

---

## Repository Struktur

```tree
dev_dito/
├── README.md                          # Projekt-Uebersicht
├── LICENSE
├── .gitignore
├── .github/
│   └── workflows/                     # CI/CD
│
├── docs/                              # Dokumentation
│   ├── architecture.md                # Von 02_dev_dito/architecture_dev_dito.md
│   ├── pipeline_manager.md            # Von .cursor/plans/dev_dito_pipeline_manager
│   └── setup_guide.md
│
├── config/                            # Zentrale Konfiguration
│   ├── sources.yaml                   # Von sources_dev_dito.yaml
│   └── env.example.yaml
│
├── pipeline/                          # Embedding Pipeline Scripts
│   ├── 01_wiki_fetcher/               # Wiki Content Fetcher
│   │   ├── fetch_full_wiki_extended.py
│   │   ├── api_client.py
│   │   ├── config.py
│   │   ├── extract_links_from_html.py
│   │   ├── media_cache.py
│   │   ├── resume_fetch.py
│   │   └── requirements.txt
│   │
│   ├── 02_deep_evaluation/            # Content Evaluation
│   │   ├── run_deep_evaluation.py
│   │   ├── analyzers/
│   │   │   ├── content_classifier.py
│   │   │   ├── document_deep_analyzer.py
│   │   │   ├── temporal_analyzer.py
│   │   │   └── ...
│   │   ├── core/
│   │   │   ├── file_handler.py
│   │   │   └── llm_client.py
│   │   ├── generators/
│   │   │   └── strategy_generator.py
│   │   ├── config.py
│   │   └── requirements.txt
│   │
│   ├── 03_embeddings_creator/         # Embedding Generation
│   │   ├── main.py
│   │   ├── pipeline.py
│   │   ├── embedder.py
│   │   ├── content_aware_chunker.py
│   │   ├── document_loader.py
│   │   ├── config.py
│   │   ├── env.yaml
│   │   └── requirements.txt
│   │
│   └── 04_deploy/                     # SSH Transfer Scripts
│       ├── transfer_to_pi.py          # NEU
│       ├── verify_transfer.py         # NEU
│       └── config.yaml
│
├── backend_services/                  # Docker Backend Services
│   ├── docker-compose.yml             # NEU: Standalone compose
│   ├── qdrant_db/
│   │   ├── Dockerfile
│   │   ├── init_collection.py
│   │   └── requirements.txt
│   ├── wiki_dev_mcp_server/
│   │   ├── Dockerfile
│   │   ├── server.py
│   │   └── requirements.txt
│   └── embeddings/
│       └── README.md                  # Platzhalter fuer JSONL
│
├── dokuwiki_plugin/                   # DokuWiki Plugin "devdito"
│   ├── action.php
│   ├── admin.php
│   ├── plugin.info.txt
│   ├── logo.png
│   ├── conf/
│   │   ├── default.php
│   │   └── metadata.php
│   ├── lang/
│   │   ├── de/
│   │   └── en/
│   └── lib/                           # NEU: Pipeline Integration
│       ├── PipelineManager.php
│       └── SSHManager.php
│
├── data/                              # Output Verzeichnisse
│   ├── fetched/                       # Wiki Fetch Output
│   ├── evaluated/                     # Evaluation Results
│   ├── embeddings/                    # Generated Embeddings
│   └── logs/                          # Pipeline Logs
│
└── planning/                          # Planung & Archiv
    ├── dev_dito_pipeline_manager.md   # Von .cursor/plans/
    └── archive/
        └── 02_dev_dito_original/      # Backup von legacy-wiki-repo
```

---

## Quell-Mapping (Was wird wohin kopiert)

### Mature Versions (NUR diese kopieren)

| Quelle                                                   | Ziel                                      | Status |
| -------------------------------------------------------- | ----------------------------------------- | ------ |
| `techstack/dokuwiki/fetcher_json_rpc_api/script/`        | `pipeline/01_wiki_fetcher/`               | MATURE |
| `techstack/dokuwiki/fetched_data_evaluation/script/`     | `pipeline/02_deep_evaluation/`            | MATURE |
| `techstack/qdrant/embeddings_creator/script/`            | `pipeline/03_embeddings_creator/`         | MATURE |
| `techstack/qdrant/embeddings_creator/config/env.yaml`    | `pipeline/03_embeddings_creator/env.yaml` | MATURE |
| `02_dev_dito/_development_of_dev_dito/backend_services/` | `backend_services/`                       | MATURE |
| `02_dev_dito/_development_of_dev_dito/devdito/`          | `dokuwiki_plugin/`                        | MATURE |
| `02_dev_dito/architecture_dev_dito.md`                   | `docs/architecture.md`                    | MATURE |
| `.cursor/plans/dev_dito_pipeline_manager_*.md`           | `planning/`                               | PLAN   |
| `sources_dev_dito.yaml`                                  | `config/sources.yaml`                     | CONFIG |

### NICHT kopieren (Duplikate/Alte Versionen)

| Pfad                                                                      | Grund                                |
| ------------------------------------------------------------------------- | ------------------------------------ |
| `techstack/qdrant/.archived_scripts/`                                     | Alte Version                         |
| `techstack/qdrant/.archived_embedded_chunks/`                             | Alte Outputs                         |
| `techstack/dokuwiki/testing_json_rpc_api_dokuwiki__by_ai_(insufficient)/` | Markiert als "insufficient"          |
| `techstack/dokuwiki/fetcher_json_rpc_api/script/fetch_full_wiki.py`       | Aeltere Version (extended ist neuer) |

---

## Neue Dateien zu erstellen

### 1. Repository Root

**README.md:**

```markdown
# Dev Dito - Wiki Embedding Pipeline & Service Addon

Service Addon fuer DokuWiki zur Verwaltung der Wiki-Embedding-Pipeline.

## Features
- Wiki Content Fetching via JSON-RPC API
- Deep Content Evaluation
- OpenAI Embeddings (text-embedding-3-large, 3072 dim)
- Qdrant Vector Database Integration
- SSH Deploy to Raspberry Pi

## Quick Start
...
```

### 2. Standalone docker-compose.yml

```yaml
# backend_services/docker-compose.yml
version: '3.8'

services:
  qdrant_db:
    image: qdrant/qdrant:v1.13.2
    container_name: devdito_qdrant
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - qdrant_storage:/qdrant/storage

  qdrant_init:
    build: ./qdrant_db
    container_name: devdito_qdrant_init
    depends_on:
      - qdrant_db
    environment:
      - QDRANT_HOST=qdrant_db
      - COLLECTION_NAME=wiki_embeddings
    volumes:
      - ../data/embeddings:/data/embeddings:ro

  wiki_mcp_server:
    build: ./wiki_dev_mcp_server
    container_name: devdito_mcp_server
    ports:
      - "3000:3000"
    depends_on:
      - qdrant_db
    environment:
      - QDRANT_HOST=qdrant_db
      - OPENAI_API_KEY=${OPENAI_API_KEY}

volumes:
  qdrant_storage:
```

### 3. Deploy Scripts (NEU)

**pipeline/04_deploy/transfer_to_pi.py**

**pipeline/04_deploy/verify_transfer.py**

---

## Beziehung zu legacy-wiki-repo

Nach der Auslagerung:

- **dev_dito Repository**: Eigenstaendiges Projekt
- **legacy-wiki-repo**: Behaelt nur `leonidas` Plugin + Themes
- **Verbindung**: Gemeinsames Docker Network wenn beide laufen
- **Kein Submodule**: Komplett getrennte Repositories

### In legacy-wiki-repo zu aendern

1. `docker-compose.yml`: Dev Dito Services entfernen (werden separat gestartet)
2. `02_dev_dito/`: Verzeichnis entfernen oder durch README mit Link ersetzen
3. Dokumentation aktualisieren

---

## Ausfuehrungsschritte

1. **Repository erstellen**
   ```powershell
   mkdir D:\_Repositories\_Diploma_Thesis_Repositories\dev_dito
   cd D:\_Repositories\_Diploma_Thesis_Repositories\dev_dito
   git init
   ```

2. **Struktur anlegen**
   - Verzeichnisse erstellen
   - Mature Scripts kopieren (siehe Mapping)
   - Neue Dateien erstellen (README, docker-compose, etc.)

3. **Pfade in Scripts anpassen**

   - `config.py` Dateien: Relative Pfade verwenden
   - `env.yaml` Dateien: Pfade auf neues Repo umstellen

4. **GitHub Repository erstellen**
   ```powershell
   gh repo create IxI-Enki/DA_2026_dev_dito --private --source=. --push
   ```

5. **legacy-wiki-repo bereinigen**
   - `02_dev_dito/` entfernen
   - `docker-compose.yml` anpassen
