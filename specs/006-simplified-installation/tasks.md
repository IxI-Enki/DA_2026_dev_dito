# Tasks 006: Simplified Dev Dito Installation

## Phase 1: Docker Integration Refactoring

- [x] **T1.1** Update `backend_services/docker-compose.yml`
  - [x] Add explicit `name: stack-g-devdito` at top level
  - [x] Add `htl-wiki-network` as external network
  - [x] Update all service names to `dev-dito-{service}` format
  - [x] Update container_name for each service
  - [x] Add network configuration to each service

- [x] **T1.2** Update orchestrator configuration
  - [x] Update service discovery to use new container names
  - [x] Update docker-compose commands to use `-p stack-g-devdito`

- [ ] **T1.3** Update DokuWiki plugin configuration
  - [ ] Update `PipelineOrchestrator.php` with new service URLs
  - [ ] Update `settings.json` template

## Phase 2: Installation Scripts

- [x] **T2.1** Create `scripts/docker_manager.ps1`
  - [x] `Test-DockerInstalled` function
  - [x] `Test-DockerRunning` function
  - [x] `Start-DockerDesktop` function
  - [x] `Wait-ForDockerReady` function (with timeout)
  - [x] `Get-DockerDownloadUrl` function

- [x] **T2.2** Create `scripts/network_setup.ps1`
  - [x] `Test-NetworkExists` function
  - [x] `New-HtlWikiNetwork` function
  - [x] `Get-ConnectedStacks` function
  - [x] `Show-NetworkStatus` function

- [x] **T2.3** Create `scripts/migration.ps1`
  - [x] `Find-ExistingDevDitoSetup` function
  - [x] `Get-SetupVersion` function
  - [x] `Backup-ExistingData` function
  - [x] `Migrate-ToCurrentStructure` function
  - [x] `Remove-LegacyContainers` function

- [x] **T2.4** Create `install.ps1` main script
  - [x] Welcome banner with version info
  - [x] Docker check workflow
  - [x] Network setup workflow
  - [x] Migration detection workflow
  - [x] Image build/pull workflow
  - [x] Stack startup workflow
  - [x] Plugin deployment workflow
  - [x] Health check workflow
  - [x] Success message with next steps

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
