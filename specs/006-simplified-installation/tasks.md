# Tasks 006: Simplified Dev Dito Installation

## Phase 1: Docker Integration Refactoring

- [ ] **T1.1** Update `backend_services/docker-compose.yml`
  - [ ] Add explicit `name: stack-g-devdito` at top level
  - [ ] Add `htl-wiki-network` as external network
  - [ ] Update all service names to `dev-dito-{service}` format
  - [ ] Update container_name for each service
  - [ ] Add network configuration to each service

- [ ] **T1.2** Update orchestrator configuration
  - [ ] Update service discovery to use new container names
  - [ ] Update docker-compose commands to use `-p stack-g-devdito`

- [ ] **T1.3** Update DokuWiki plugin configuration
  - [ ] Update `PipelineOrchestrator.php` with new service URLs
  - [ ] Update `settings.json` template

## Phase 2: Installation Scripts

- [ ] **T2.1** Create `scripts/docker_manager.ps1`
  - [ ] `Test-DockerInstalled` function
  - [ ] `Test-DockerRunning` function
  - [ ] `Start-DockerDesktop` function
  - [ ] `Wait-ForDockerReady` function (with timeout)
  - [ ] `Get-DockerDownloadUrl` function

- [ ] **T2.2** Create `scripts/network_setup.ps1`
  - [ ] `Test-NetworkExists` function
  - [ ] `New-HtlWikiNetwork` function
  - [ ] `Get-ConnectedStacks` function
  - [ ] `Show-NetworkStatus` function

- [ ] **T2.3** Create `scripts/migration.ps1`
  - [ ] `Find-ExistingDevDitoSetup` function
  - [ ] `Get-SetupVersion` function
  - [ ] `Backup-ExistingData` function
  - [ ] `Migrate-ToCurrentStructure` function
  - [ ] `Remove-LegacyContainers` function

- [ ] **T2.4** Create `install.ps1` main script
  - [ ] Welcome banner with version info
  - [ ] Docker check workflow
  - [ ] Network setup workflow
  - [ ] Migration detection workflow
  - [ ] Image build/pull workflow
  - [ ] Stack startup workflow
  - [ ] Plugin deployment workflow
  - [ ] Health check workflow
  - [ ] Success message with next steps

## Phase 3: Plugin Integration

- [ ] **T3.1** Update `deploy-plugin.ps1`
  - [ ] Auto-detect `dev-dito-wiki` container
  - [ ] Support both local and container deployment
  - [ ] Generate `settings.json` dynamically

- [ ] **T3.2** Add service discovery to plugin
  - [ ] Ping orchestrator on plugin load
  - [ ] Show connection status in admin panel
  - [ ] Auto-retry on connection failure

## Phase 4: Documentation

- [ ] **T4.1** Update `README.md`
  - [ ] Quick start section
  - [ ] Prerequisites section
  - [ ] Installation steps
  - [ ] Troubleshooting section

- [ ] **T4.2** Create architecture diagram
  - [ ] Stack relationships
  - [ ] Network topology
  - [ ] Service dependencies

## Verification Checklist

- [ ] Fresh install works with `git clone && .\install.ps1`
- [ ] Docker Desktop starts automatically if installed
- [ ] Network `htl-wiki-network` created if missing
- [ ] All containers named `dev-dito-*` under `stack-g-devdito`
- [ ] Plugin auto-deployed to wiki container
- [ ] Dashboard shows all services as connected
- [ ] Existing data preserved during migration
