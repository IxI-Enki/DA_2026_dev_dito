# Dev Dito - Backend Services

Backend-Infrastruktur fuer die Dev Dito Extension.

## Komponenten

### Qdrant Vector Database

Verzeichnis: `qdrant_db/`

Semantische Suche mit Vektor-Embeddings.

```bash
# Docker starten
docker build -t devdito-qdrant ./qdrant_db
docker run -p 6333:6333 devdito-qdrant
```

### MCP Server

Verzeichnis: `wiki_dev_mcp_server/`

Model Context Protocol Server fuer AI-Integration.

```bash
# Docker starten
docker build -t devdito-mcp ./wiki_dev_mcp_server
docker run -p 3000:3000 devdito-mcp
```

## Architektur

```
DokuWiki + Dev Dito Plugin
         |
         v
    MCP Server (Port 3000)
         |
         v
    Qdrant DB (Port 6333)
```

## Hinweis

Diese Backend-Services sind optional. Das Dev Dito Plugin funktioniert
auch ohne sie (mit eingeschraenkter Funktionalitaet).
