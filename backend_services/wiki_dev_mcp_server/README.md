# Wiki Semantic Search MCP Server

MCP (Model Context Protocol) server providing semantic search over HTL Leonding Wiki content.

## Overview

This server exposes a `semantic_wiki_search` tool that queries the Qdrant vector database
to find wiki pages semantically related to the search query.

## Requirements

- Running Qdrant instance with populated `wiki_embeddings` collection
- OpenAI API key (for query embedding generation)

## Configuration

| Variable          | Default           | Description                   |
| ----------------- | ----------------- | ----------------------------- |
| `QDRANT_HOST`     | `qdrant_db`       | Qdrant server hostname        |
| `QDRANT_PORT`     | `6333`            | Qdrant REST API port          |
| `COLLECTION_NAME` | `wiki_embeddings` | Name of the vector collection |
| `OPENAI_API_KEY`  | -                 | **Required** OpenAI API key   |

## Tool: `semantic_wiki_search`

### Description

Semantic search in the HTL Leonding Wiki (LeoWiki).
Searches wiki content based on semantic similarity.
Finds relevant pages even if exact search terms don't appear.

### Parameters

| Parameter          | Type    | Required | Default | Description                      |
| ------------------ | ------- | -------- | ------- | -------------------------------- |
| `query`            | string  | yes      | -       | Search query in natural language |
| `top_k`            | integer | no       | 5       | Number of results (1-20)         |
| `namespace_filter` | string  | no       | -       | Filter by wiki namespace         |

### Example Usage

```json
{
  "name": "semantic_wiki_search",
  "arguments": {
    "query": "Wie funktioniert die Matura Anmeldung?",
    "top_k": 5
  }
}
```

### Response Format

Returns formatted markdown with:

- Score (cosine similarity)
- Title
- Namespace
- Page ID
- Content Type
- Source URL
- Content excerpt

## Docker Usage

The MCP server runs as a Docker container and communicates via stdio.
To test manually:

```bash
docker compose exec -it wiki_dev_mcp_server python server.py
```

## MCP Client Configuration

Add to your MCP client config (e.g., Claude Desktop):

```json
{
  "mcpServers": {
    "wiki-search": {
      "command": "docker",
      "args": ["compose", "exec", "-T", "wiki_dev_mcp_server", "python", "server.py"],
      "cwd": "/path/to/first_own_dokuwiki"
    }
  }
}
```
