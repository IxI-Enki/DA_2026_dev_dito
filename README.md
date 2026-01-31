# Dev Dito - Wiki Embedding Pipeline & Service Addon

> **Diplomarbeit 2026** - HTL Leonding  
> **Autor:** Jan Ritt (IxI-Enki)  
> **Repository:** Private

---

## Uebersicht

Dev Dito ist ein **Service Addon** fuer DokuWiki zur Verwaltung der kompletten Wiki-Embedding-Pipeline. Es ermoeglicht die Erstellung von semantischen Embeddings aus Wiki-Inhalten fuer die Verwendung in RAG-basierten KI-Systemen.

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
├── docs/                    # Dokumentation
├── config/                  # Zentrale Konfiguration
├── pipeline/                # Embedding Pipeline Scripts
│   ├── 01_wiki_fetcher/     # Wiki Content Fetcher
│   ├── 02_deep_evaluation/  # Content Evaluation
│   ├── 03_embeddings_creator/ # Embedding Generation
│   └── 04_deploy/           # SSH Transfer Scripts
├── backend_services/        # Docker Backend Services
│   ├── qdrant_db/           # Qdrant Vector Database
│   ├── wiki_dev_mcp_server/ # MCP Server
│   └── embeddings/          # Embedding Output
├── dokuwiki_plugin/         # DokuWiki Plugin "devdito"
├── data/                    # Output Verzeichnisse
└── planning/                # Planung & Archiv
```

---

## Quick Start

### 1. Voraussetzungen

- Python 3.11+
- Docker & Docker Compose
- OpenAI API Key
- SSH Zugang zum Raspberry Pi (optional)

### 2. Environment Setup

```powershell
# Repository klonen
git clone https://github.com/IxI-Enki/DA_2026_dev_dito.git
cd DA_2026_dev_dito

# Python Dependencies installieren
pip install -r pipeline/01_wiki_fetcher/requirements.txt
pip install -r pipeline/02_deep_evaluation/requirements.txt
pip install -r pipeline/03_embeddings_creator/requirements.txt

# Environment Variable setzen
$env:OPENAI_API_KEY = "your-api-key"
```

### 3. Backend Services starten

```powershell
cd backend_services
docker-compose up -d
```

### 4. Pipeline ausfuehren

```powershell
# 1. Wiki Fetch
cd pipeline/01_wiki_fetcher
python fetch_full_wiki_extended.py

# 2. Deep Evaluation
cd ../02_deep_evaluation
python run_deep_evaluation.py

# 3. Embeddings erstellen
cd ../03_embeddings_creator
python main.py

# 4. Deploy to Raspberry Pi
cd ../04_deploy
python transfer_to_pi.py
```

---

## Pipeline Workflow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ Wiki Fetch  │────▶│ Evaluation  │────▶│ Embeddings  │────▶│ SSH Deploy  │────▶│ Qdrant Init │
│ JSON-RPC API│     │ Content QA  │     │ OpenAI API  │     │ Raspberry Pi│     │ Collection  │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
```

---

## Konfiguration

### config/env.example.yaml

Kopiere `env.example.yaml` nach `env.yaml` und passe die Werte an:

- `OPENAI_API_KEY`: OpenAI API Schluessel
- `WIKI_URL`: DokuWiki JSON-RPC Endpoint
- `SSH_HOST`: Raspberry Pi Hostname
- `SSH_USER`: SSH Benutzername

---

## Dokumentation

- [Architektur](docs/architecture.md) - Technische Architektur
- [Pipeline Manager](planning/dev_dito_pipeline_manager.md) - Pipeline Details
- [Repository Setup](planning/dev_dito_repository_setup.md) - Setup Dokumentation

---

## Lizenz

Private - HTL Leonding Diplomarbeit 2026

---

*Erstellt: 2026-01-24*
