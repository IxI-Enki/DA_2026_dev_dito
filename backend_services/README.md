---
title: Dev Dito Backend Services
description: Docker-based backend infrastructure for the Dev Dito pipeline (Stack-G), including Qdrant vector database, pipeline orchestrator, and five pipeline modules.
author:
  name: Jan Ritt
  github: 'https://github.com/IxI-Enki'
version: 2.0.0
created: 2025-11-01
updated: 2026-02-13
tags: [docker, backend-services, qdrant, orchestrator, pipeline, stack-g]
---

# Dev Dito - Backend Services

Docker-based backend infrastructure for the Dev Dito pipeline (Stack-G in the HTL Wiki multi-stack ecosystem).

## Architecture

```
DokuWiki + Dev Dito Plugin
         |
         v
   Orchestrator API (Port 18089)
         |
         v
   Pipeline Modules (fetcher, evaluator, preprocessor, embedder, deployer)
         |
         v
   Qdrant Vector DB (Port 18334)
```

## Services

### Always-on Services

| Service        | Image                       | Port  | Description                          |
| -------------- | --------------------------- | ----- | ------------------------------------ |
| `qdrant`       | `qdrant/qdrant:v1.13.2`     | 18334 | Vector database for wiki embeddings  |
| `orchestrator` | Custom (FastAPI)             | 18089 | Pipeline execution API               |

### Profile: `wiki`

| Service     | Image                                                  | Port  | Description              |
| ----------- | ------------------------------------------------------ | ----- | ------------------------ |
| `dokuwiki`  | `lscr.io/linuxserver/dokuwiki:version-2024-02-06a`     | 18080 | Development DokuWiki     |

### Profile: `pipeline` (run-to-completion modules)

| Service              | Description                                |
| -------------------- | ------------------------------------------ |
| `module_fetcher`     | Fetches wiki content via JSON-RPC API      |
| `module_evaluator`   | Evaluates fetched content quality          |
| `module_preprocessor`| Converts wiki syntax to RAG-ready Markdown |
| `module_embedder`    | Creates vector embeddings (OpenAI/Ollama)  |
| `module_deployer`    | Uploads embeddings to Qdrant               |

### Profile: `test`

| Service        | Port  | Description                     |
| -------------- | ----- | ------------------------------- |
| `qdrant-test`  | 18336 | Isolated Qdrant for testing     |

## Usage

```powershell
# Start core services (Qdrant + Orchestrator)
docker compose -p stack-g-devdito up -d

# Start with DokuWiki
docker compose -p stack-g-devdito --profile wiki up -d

# Run pipeline modules
docker compose -p stack-g-devdito --profile pipeline run module_fetcher

# Start test instance
docker compose -p stack-g-devdito --profile test up qdrant-test -d

# Stop all
docker compose -p stack-g-devdito down
```

## Configuration

- `.env` / `.env.template` -- Docker-specific environment variables
- `../config/env.yaml` -- Central pipeline configuration (mounted read-only)
- `../config/secrets/` -- Token and certificate files (mounted read-only)

## Network

All services connect to `leonidas-network` (external), shared with other HTL Wiki stacks (Stack-A, B, D, H).
