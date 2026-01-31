# Embeddings Directory

Place your embedding files here for Qdrant initialization.

## Required Format

File: `embedded_chunks.jsonl` (JSON Lines format)

Each line must contain:
```json
{"id": "unique_id", "text": "content text", "embedding": [0.1, 0.2, ...], "metadata": {"title": "...", "namespace": "...", "page_id": "...", "source": "...", "content_type": "..."}}
```

## Generation

Use OpenAI `text-embedding-3-large` (dim=3072) for embeddings.
