# Dev Dito - Wiki Embedding Pipeline & Service Gateway

> **Diplomarbeit 2026** - HTL Leonding  
> **Autor:** Jan Ritt (IxI-Enki)  
> **Repository:** Private

---

## Uebersicht

Dev Dito ist ein **Service Gateway** (HTTP-Client) fuer DokuWiki zur Verwaltung der kompletten Wiki-Embedding-Pipeline. Es ermoeglicht die Erstellung von semantischen Embeddings aus Wiki-Inhalten fuer die Verwendung in RAG-basierten KI-Systemen.

**Wichtig:** Dev Dito *verbindet sich mit* externen Services (MCP Server, Qdrant, LLMs), *enthaelt diese aber nicht*. Die Services laufen in separaten Docker-Stacks.

### Features

- **Wiki Content Fetching** - Kompletter Wiki-Export via JSON-RPC API
- **Deep Content Evaluation** - Qualitaetsanalyse und Content-Klassifizierung
- **OpenAI Embeddings** - text-embedding-3-large (3072 Dimensionen)
- **Qdrant Integration** - Vector Database fuer semantische Suche
- **SSH Deploy** - Automatischer Transfer zum Raspberry Pi
- **DokuWiki Plugin** - Admin-Interface fuer Pipeline-Steuerung

---

## Repository Struktur

```
dev_dito/
├── config/                  # ZENTRALE Konfiguration (env.yaml)
│   ├── PLACEHOLDER_env.yaml # Template mit Dokumentation
│   ├── env.yaml             # Aktive Config (gitignored)
│   ├── settings.json        # Auto-generiert fuer PHP
│   └── secrets/             # Token & Zertifikate (gitignored)
├── config.py                # Config-Loader (Python)
├── pipeline/                # Embedding Pipeline Scripts
│   ├── 01_wiki_fetcher/     # Wiki Content Fetcher
│   ├── 02_deep_evaluation/  # Content Evaluation
│   ├── 03_embeddings_creator/ # Embedding Generation
│   └── 04_deploy/           # SSH Transfer Scripts
├── dokuwiki_plugin/         # DokuWiki Plugin "devdito"
│   ├── lib/ConfigLoader.php # Config-Loader (PHP)
│   └── ...
├── backend_services/        # Docker Backend Services (Referenz)
│   ├── qdrant_db/           # Qdrant Vector Database
│   └── wiki_dev_mcp_server/ # MCP Server
├── docs/                    # Dokumentation
├── specs/                   # Feature Specifications
├── data/                    # Output Verzeichnisse
└── scripts/                 # Deployment Scripts
```

---

## Quick Start

### 1. Voraussetzungen

- Python 3.11+
- PHP 8.0+ (fuer Syntax-Checks)
- Docker & Docker Compose (fuer Backend-Services)
- OpenAI API Key
- SSH Zugang zum Raspberry Pi (optional)

### 2. Konfiguration einrichten

```powershell
# Repository klonen
git clone https://github.com/IxI-Enki/DA_2026_dev_dito.git
cd DA_2026_dev_dito

# 1. env.yaml erstellen
Copy-Item config/PLACEHOLDER_env.yaml config/env.yaml

# 2. env.yaml bearbeiten - setze:
#    - PATHS.root_dir (dein lokaler Pfad)
#    - SOURCE_WIKI.api.url (Wiki JSON-RPC URL)
#    - SERVICES.* (MCP, Qdrant URLs)

# 3. Secrets hinzufuegen
# Token-Dateien in config/secrets/ ablegen:
#   - json_rpc_api.token (Wiki API Token)
#   - ssl.cert (SSL Zertifikat fuer Wiki)
#   - openai.token (OpenAI API Key)

# 4. Config testen und settings.json generieren
python config.py
```

### 3. Python Dependencies installieren

```powershell
pip install -r pipeline/01_wiki_fetcher/requirements.txt
pip install -r pipeline/02_deep_evaluation/requirements.txt
pip install -r pipeline/03_embeddings_creator/requirements.txt
```

### 4. DokuWiki Plugin deployen

```powershell
# Plugin zum Test-Wiki kopieren
.\scripts\deploy-plugin.ps1

# Oder mit benutzerdefiniertem Pfad:
.\scripts\deploy-plugin.ps1 -TargetWiki "C:\path\to\wiki"
```

---

## Konfiguration

### Zentrale Config (Constitution Article II-B)

**Alle** Konfigurationswerte sind zentral in `config/env.yaml` definiert.

```yaml
# config/env.yaml (Auszug)

PATHS:
  root_dir: D:/_Repositories/_Diploma_Thesis_Repositories/dev_dito
  secrets_dir: ${root_dir}/config/secrets

SOURCE_WIKI:
  api:
    url: https://leowiki.htl-leonding.ac.at/lib/exe/jsonrpc.php
  authentication:
    token_file: ${secrets_dir}/json_rpc_api.token
  certificate: ${secrets_dir}/ssl.cert

SERVICES:
  mcp_server:
    url: http://wiki_dev_mcp_server:3000
  qdrant:
    host: qdrant_db
    port: 6333

PLUGIN:
  enabled: true
  panel_position: right
```

### Config-Workflow

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ config/env.yaml │────▶│ python config.py│────▶│ settings.json   │
│ (Quelle)        │     │ (Generator)     │     │ (fuer PHP)      │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               │
                               ▼
                        ┌─────────────────┐
                        │ Python Pipeline │
                        │ (import config) │
                        └─────────────────┘
```

### Config in Python nutzen

```python
# Einfach:
from config import SOURCE_WIKI_URL, MCP_SERVER_URL, settings

# Oder mit Pfad-Syntax:
from config import get_setting
url = get_setting("SERVICES.mcp_server.url")
```

### Config in PHP nutzen

```php
use dokuwiki\plugin\devdito\lib\ConfigLoader;

$mcpUrl = ConfigLoader::get('SERVICES.mcp_server.url');
$timeout = ConfigLoader::get('SERVICES.mcp_server.timeout', 30);
```

---

## Pipeline Workflow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ Wiki Fetch  │────▶│ Evaluation  │────▶│ Embeddings  │────▶│ SSH Deploy  │────▶│ Qdrant Init │
│ JSON-RPC API│     │ Content QA  │     │ OpenAI API  │     │ Raspberry Pi│     │ Collection  │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
```

### Pipeline ausfuehren

```powershell
# 1. Wiki Fetch
python pipeline/01_wiki_fetcher/fetch_full_wiki_extended.py

# 2. Deep Evaluation
python pipeline/02_deep_evaluation/run_deep_evaluation.py

# 3. Embeddings erstellen
python pipeline/03_embeddings_creator/main.py

# 4. Deploy to Raspberry Pi
python pipeline/04_deploy/transfer_to_pi.py
```

---

## Dokumentation

- [Architektur](docs/architecture.md) - Technische Architektur
- [Spec Kit](specs/) - Feature Specifications
- [Pipeline Manager](planning/dev_dito_pipeline_manager.md) - Pipeline Details
- [Repository Setup](planning/dev_dito_repository_setup.md) - Setup Dokumentation

---

## Development

### Spec Kit Workflow

```powershell
# Feature spezifizieren
# /specify [feature-name]

# Technischen Plan erstellen
# /plan [feature-name]

# Tasks generieren
# /tasks [feature-name]

# Implementieren
# /implement [feature-name]
```

### Deployment testen

```powershell
# PHP Syntax Check
php -l dokuwiki_plugin/action.php

# Config generieren
python config.py

# Plugin deployen
.\scripts\deploy-plugin.ps1
```

---

## Lizenz

Private - HTL Leonding Diplomarbeit 2026

---

*Erstellt: 2026-01-24 | Aktualisiert: 2026-01-31*
