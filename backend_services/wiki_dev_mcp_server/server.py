#!/usr/bin/env python3
"""
Wiki Semantic Search MCP Server (HTTP/JSON-RPC)

Provides semantic search capabilities over DokuWiki content
stored in Qdrant vector database via JSON-RPC over HTTP.

Compatible with Leonidas Plugin's MCPToolProxy.
"""
import json
import os
import sys
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from openai import OpenAI
from pydantic import BaseModel
from qdrant_client import QdrantClient
import uvicorn

# Configuration
QDRANT_HOST = os.getenv("QDRANT_HOST", "qdrant_db")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "wiki_embeddings")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
EMBEDDING_MODEL = "text-embedding-3-large"
VECTOR_DIM = 3072
DEFAULT_TOP_K = 5
SERVER_PORT = int(os.getenv("MCP_SERVER_PORT", "3000"))


class SearchResult(BaseModel):
    """A single search result."""
    score: float
    text: str
    title: str
    namespace: str
    page_id: str
    source_url: str
    content_type: str


def create_embedding(text: str, openai_client: OpenAI) -> list[float]:
    """Create embedding for search query."""
    response = openai_client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text,
        dimensions=VECTOR_DIM,
    )
    return response.data[0].embedding


def format_results_for_llm(results: list[SearchResult]) -> str:
    """Format search results for LLM consumption."""
    if not results:
        return "Keine Ergebnisse gefunden."
    
    output_parts = []
    for i, result in enumerate(results, 1):
        output_parts.append(f"""
## Ergebnis {i} (Score: {result.score:.3f})

**Titel:** {result.title}
**Namespace:** {result.namespace}
**Seiten-ID:** {result.page_id}
**Content-Type:** {result.content_type}
**URL:** {result.source_url}

### Inhalt:
{result.text}

---""")
    
    return "\n".join(output_parts)


# Tool definitions for tools/list
TOOLS = [
    {
        "name": "semantic_wiki_search",
        "description": "Semantische Suche im HTL Leonding Wiki (LeoWiki). Durchsucht Wiki-Inhalte basierend auf semantischer Aehnlichkeit. Findet relevante Seiten auch wenn exakte Suchbegriffe nicht vorkommen.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Die Suchanfrage in natuerlicher Sprache"
                },
                "top_k": {
                    "type": "integer",
                    "description": "Anzahl der zurueckzugebenden Ergebnisse (1-20)",
                    "default": 5,
                    "minimum": 1,
                    "maximum": 20
                },
                "namespace_filter": {
                    "type": "string",
                    "description": "Optional: Filter nach Wiki-Namespace"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "faceted_search",
        "description": "Facettensuche im HTL Wiki. Verwendet semantische Suche um relevante Dokumente zu finden. Verwende dieses Tool ZUERST bei JEDER Frage ueber HTL Lehrer, Kurse, Raeume, Stundenplaene oder Events.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Die Suchanfrage (Frage des Benutzers als String)"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximale Anzahl der Ergebnisse",
                    "default": 5
                }
            },
            "required": ["query"]
        }
    }
]


def execute_search(query: str, top_k: int = 5, namespace_filter: str | None = None) -> dict:
    """Execute semantic search against Qdrant."""
    if not query.strip():
        return {"error": "Suchanfrage darf nicht leer sein.", "results": []}
    
    if not OPENAI_API_KEY:
        return {"error": "OPENAI_API_KEY nicht konfiguriert.", "results": []}
    
    try:
        # Create embedding for query
        openai_client = OpenAI(api_key=OPENAI_API_KEY)
        query_embedding = create_embedding(query, openai_client)
        
        # Connect to Qdrant (suppress version warning)
        qdrant_client = QdrantClient(
            host=QDRANT_HOST, 
            port=QDRANT_PORT,
            check_compatibility=False  # Suppress version mismatch warning
        )
        
        # Build filter if namespace specified
        search_filter = None
        if namespace_filter:
            search_filter = {
                "must": [
                    {
                        "key": "metadata.namespace",
                        "match": {"value": namespace_filter}
                    }
                ]
            }
        
        # Search
        search_results = qdrant_client.search(
            collection_name=COLLECTION_NAME,
            query_vector=query_embedding,
            limit=min(max(top_k, 1), 20),
            query_filter=search_filter,
            with_payload=True,
        )
        
        # Process results
        results = []
        for hit in search_results:
            payload = hit.payload or {}
            metadata = payload.get("metadata", {})
            
            results.append({
                "score": hit.score,
                "text": payload.get("text", ""),
                "title": metadata.get("title", "Unbekannt"),
                "namespace": metadata.get("namespace", ""),
                "page_id": metadata.get("page_id", ""),
                "source_url": metadata.get("source", ""),
                "content_type": metadata.get("content_type", ""),
            })
        
        return {
            "query": query,
            "total": len(results),
            "results": results
        }
        
    except Exception as e:
        return {"error": f"Suche fehlgeschlagen: {str(e)}", "results": []}


# FastAPI Application
app = FastAPI(title="Wiki Semantic Search MCP Server")

# CORS for browser access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "service": "wiki-semantic-search-mcp"}


@app.get("/")
async def root():
    """Root endpoint with server info."""
    return {
        "name": "wiki-semantic-search-mcp",
        "version": "1.0.0",
        "description": "Semantic search MCP server for HTL Wiki",
        "transport": "jsonrpc"
    }


@app.post("/")
@app.post("/mcp")
async def jsonrpc_endpoint(request: Request):
    """
    JSON-RPC 2.0 endpoint for MCP protocol.
    
    Supports:
    - tools/list: List available tools
    - tools/call: Execute a tool
    """
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            content={
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": "Parse error"}
            },
            status_code=400
        )
    
    request_id = body.get("id", None)
    method = body.get("method", "")
    params = body.get("params", {})
    
    print(f"[INFO] JSON-RPC request: method={method}", file=sys.stderr)
    
    # Handle methods
    if method == "tools/list":
        return JSONResponse(content={
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {"tools": TOOLS}
        })
    
    elif method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})
        
        print(f"[INFO] Calling tool: {tool_name} with args: {arguments}", file=sys.stderr)
        
        if tool_name in ("semantic_wiki_search", "faceted_search"):
            query = arguments.get("query", "")
            top_k = arguments.get("top_k", arguments.get("limit", DEFAULT_TOP_K))
            namespace_filter = arguments.get("namespace_filter")
            
            result = execute_search(query, top_k, namespace_filter)
            
            # Format for MCP content response
            if "error" in result and result["error"]:
                content = [{"type": "text", "text": f"[ERROR] {result['error']}"}]
            else:
                # Format results as markdown text
                formatted = f"## Semantische Suche: '{query}'\n\nGefunden: {result['total']} Ergebnisse\n\n"
                for i, r in enumerate(result["results"], 1):
                    formatted += f"### {i}. {r['title']} (Score: {r['score']:.3f})\n"
                    formatted += f"- **Namespace:** {r['namespace']}\n"
                    formatted += f"- **Seiten-ID:** {r['page_id']}\n"
                    formatted += f"- **URL:** {r['source_url']}\n"
                    formatted += f"- **Content-Type:** {r['content_type']}\n\n"
                    formatted += f"{r['text'][:1000]}{'...' if len(r['text']) > 1000 else ''}\n\n---\n\n"
                
                content = [{"type": "text", "text": formatted}]
            
            return JSONResponse(content={
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {"content": content}
            })
        
        else:
            return JSONResponse(content={
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"}
            })
    
    elif method == "ping":
        # Leonidas expects {"result": {"ok": true}} for ping
        return JSONResponse(content={
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {"ok": True}
        })
    
    else:
        return JSONResponse(content={
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": -32601, "message": f"Method not found: {method}"}
        })


if __name__ == "__main__":
    print(f"[INFO] Starting Wiki Semantic Search MCP Server on port {SERVER_PORT}...", file=sys.stderr)
    print(f"[INFO] Qdrant: {QDRANT_HOST}:{QDRANT_PORT}", file=sys.stderr)
    print(f"[INFO] Collection: {COLLECTION_NAME}", file=sys.stderr)
    
    uvicorn.run(app, host="0.0.0.0", port=SERVER_PORT, log_level="info")
