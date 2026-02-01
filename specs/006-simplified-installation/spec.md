# Spec 006: Simplified Dev Dito Installation

## Problem Statement

Dev Dito currently requires manual setup of Docker containers and complex configuration. The existing ecosystem has multiple Docker stacks (Stack-A through Stack-I) running from adjacent projects, and Dev Dito's `backend_services` stack runs separately instead of integrating with the established `stack-g-devdito` naming convention.

### Current Pain Points

1. **Fragmented Docker Setup**: `backend_services` runs as a loose stack instead of integrating with `stack-g-devdito`
2. **Manual Installation**: No automated setup script for new users
3. **No Docker Detection**: Users must manually ensure Docker is running
4. **No Migration Path**: No way to upgrade from old Dev Dito setups
5. **Network Isolation**: Dev Dito doesn't integrate with the shared Docker network (`htl-wiki-network`)

### Existing Docker Ecosystem (from Screenshot)

```
stack-d-ai-core
├── qdrant-main-vector-db (qdrant/qdrant:v1.13.2) - Port 6333
└── qdrant-init

stack-g-devdito
└── dev-dito-wiki (linuxserver/dokuwiki:latest) - Port 8080

stack-b-wiki-core
└── keycloak-server (keycloak/keycloak:25.0) - Port 8081

stack-a-wiki-sandbox
└── wiki-sandbox (linuxserver/dokuwiki:latest) - Port 8090

stack-h-mcp
└── semantic-search-wiki-core - Port 3000
```

## Solution

Create a unified installation system that:
1. Integrates Dev Dito into the existing multi-stack ecosystem
2. Provides a simple `git clone` + `install.ps1` workflow
3. Auto-detects and manages Docker Desktop
4. Migrates existing setups to the new structure

## Requirements

### R1: Installation Script (`install.ps1`)

The script MUST:
1. Check for Docker Desktop installation
   - If installed: Start Docker Desktop if not running
   - If not installed: Provide download link and instructions
2. Detect existing Dev Dito setups
   - If found: Offer migration to current structure
   - If outdated: Offer upgrade path
   - If none: Offer fresh installation
3. Configure the shared Docker network (`htl-wiki-network`)
4. Start `stack-g-devdito` services with correct naming conventions

### R2: Stack-G Integration

The `backend_services/docker-compose.yml` MUST:
1. Use project name `stack-g-devdito` (not `backend_services`)
2. Join the external network `htl-wiki-network`
3. Follow naming convention: `dev-dito-{service-name}`
4. Integrate with existing stacks (Stack-D for Qdrant, Stack-H for MCP)

### R3: DokuWiki Plugin Integration

The Dev Dito extension MUST:
1. Use only official DokuWiki APIs (NO core hacks)
2. Provide admin pages for:
   - Service status monitoring
   - Pipeline management
   - Docker stack control (via API, not Docker socket)
3. Communicate with backend services via HTTP APIs

### R4: Configuration Management

1. Single configuration source (`config/env.yaml`)
2. Auto-discovery of connected services
3. Health checks for all dependent services

## Architecture

```
User Machine
├── Git Clone: dev_dito/
│   ├── install.ps1          # Entry point
│   ├── scripts/
│   │   ├── docker_manager.ps1
│   │   ├── network_setup.ps1
│   │   └── migration.ps1
│   └── backend_services/
│       └── docker-compose.yml  # stack-g-devdito
│
└── Docker Desktop
    └── htl-wiki-network (external)
        ├── stack-g-devdito (THIS PROJECT)
        │   ├── dev-dito-wiki
        │   ├── dev-dito-orchestrator
        │   └── dev-dito-module-*
        ├── stack-d-ai-core (EXTERNAL)
        │   └── qdrant-main-vector-db
        └── stack-h-mcp (EXTERNAL)
            └── semantic-search-wiki-core
```

## Out of Scope

- Linux/macOS installation (Windows-first, others later)
- Docker-in-Docker (forbidden by architecture)
- Core DokuWiki modifications

## Success Criteria

1. New user can install with: `git clone ... && .\install.ps1`
2. Existing users can upgrade without data loss
3. All services visible in Docker Desktop under `stack-g-devdito`
4. Dev Dito dashboard shows all connected services
