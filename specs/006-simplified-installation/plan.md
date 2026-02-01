# Plan 006: Simplified Dev Dito Installation

## Phase 1: Docker Integration Refactoring

### 1.1 Rename and Restructure docker-compose.yml
- Change project name from implicit to explicit `stack-g-devdito`
- Add external network configuration for `htl-wiki-network`
- Update all container names to follow `dev-dito-{service}` convention
- Remove duplicate services that exist in other stacks

### 1.2 Service Naming Convention Update
Current → Target:
- `module_preprocessor` → `dev-dito-module-preprocessor`
- `module_evaluator` → `dev-dito-module-evaluator`
- `module_embedder` → `dev-dito-module-embedder`
- `module_deployer` → `dev-dito-module-deployer`
- `module_fetcher` → `dev-dito-module-fetcher`
- `orchestrator` → `dev-dito-orchestrator`

### 1.3 Network Configuration
```yaml
networks:
  htl-wiki-network:
    external: true
    name: htl-wiki-network
```

## Phase 2: Installation Script Development

### 2.1 Docker Detection (`scripts/docker_manager.ps1`)
```powershell
# Functions:
- Test-DockerInstalled
- Test-DockerRunning
- Start-DockerDesktop
- Wait-ForDockerReady
- Get-DockerDownloadUrl
```

### 2.2 Network Setup (`scripts/network_setup.ps1`)
```powershell
# Functions:
- Test-NetworkExists
- New-HtlWikiNetwork
- Get-ConnectedStacks
```

### 2.3 Migration Logic (`scripts/migration.ps1`)
```powershell
# Functions:
- Find-ExistingDevDitoSetup
- Get-SetupVersion
- Backup-ExistingData
- Migrate-ToCurrentStructure
- Remove-LegacyContainers
```

### 2.4 Main Installer (`install.ps1`)
```powershell
# Flow:
1. Show welcome banner
2. Check Docker → Install/Start if needed
3. Check network → Create if needed
4. Check existing setup → Migrate if needed
5. Pull/Build images
6. Start stack-g-devdito
7. Deploy DokuWiki plugin
8. Run health checks
9. Show success + next steps
```

## Phase 3: Plugin Deployment Integration

### 3.1 Auto-Deploy Plugin
- Detect `dev-dito-wiki` container
- Copy plugin files to mounted volume
- Verify plugin activation

### 3.2 Configuration Injection
- Generate `settings.json` with correct service URLs
- Configure orchestrator endpoint based on network

## Phase 4: Documentation

### 4.1 README Update
- Quick start guide
- Prerequisites
- Troubleshooting

### 4.2 Architecture Diagram
- Visual representation of stack relationships

## Dependencies

| Dependency | Stack | Required For |
|------------|-------|--------------|
| Qdrant | stack-d-ai-core | Embeddings storage |
| Keycloak | stack-b-wiki-core | Authentication (optional) |
| MCP Server | stack-h-mcp | Semantic search |

## Risk Mitigation

1. **Docker not installed**: Provide clear instructions + download link
2. **Network conflicts**: Check for existing networks before creation
3. **Data loss during migration**: Mandatory backup before migration
4. **Service discovery fails**: Fallback to manual configuration

## Timeline Estimate

| Phase | Effort | Priority |
|-------|--------|----------|
| Phase 1 | 2h | High |
| Phase 2 | 4h | High |
| Phase 3 | 1h | Medium |
| Phase 4 | 1h | Medium |
