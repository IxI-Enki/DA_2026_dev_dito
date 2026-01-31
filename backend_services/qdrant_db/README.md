# Qdrant DB - Wiki Embeddings

Vector database service for storing and querying wiki embeddings.

## Overview

This service provides:

- Qdrant vector database container
- Init container to populate the database with pre-computed embeddings

## Configuration

| Variable          | Default                                  | Description                           |
| ----------------- | ---------------------------------------- | ------------------------------------- |
| `QDRANT_HOST`     | `localhost`                              | Qdrant server hostname                |
| `QDRANT_PORT`     | `6333`                                   | Qdrant REST API port                  |
| `COLLECTION_NAME` | `wiki_embeddings`                        | Name of the vector collection         |
| `EMBEDDINGS_FILE` | `/data/embeddings/embedded_chunks.jsonl` | Path to embeddings file               |
| `FORCE_REINIT`    | -                                        | Set to `1` to force re-initialization |

## Embedding Format

The embeddings JSONL file contains entries with:

```json
{
  "id": "unique-id",
  "text": "The text content...",
  "embedding": [0.1, 0.2, ...],  // 3072 dimensions (text-embedding-3-large)
  "metadata": {
    "source": "https://...",
    "title": "Page Title",
    "namespace": "archive:exams",
    "page_id": "archive:exams:page-name",
    "content_type": "KNOWLEDGE"
  }
}
```

## Endpoints

- REST API: `http://localhost:6333`
- gRPC: `localhost:6334`
- Dashboard: `http://localhost:6333/dashboard`

## Manual Initialization

If needed, run the init script manually:

```bash
docker compose run --rm qdrant_init
```

Force re-initialization:

```bash
docker compose run --rm -e FORCE_REINIT=1 qdrant_init
```
