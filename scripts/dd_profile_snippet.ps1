# =============================================================================
# DEV DITO ALIASES - DokuWiki RAG Pipeline Manager
# =============================================================================
# Author: IxI-Enki (https://github.com/IxI-Enki)
# Date: 2026-02-05
# Description: Aliases for Dev Dito pipeline management, Docker stack control,
#              installation, and development workflows.
#
# Installation:
#   Add this line to your $PROFILE:
#     . "$env:USERPROFILE\path\to\dev_dito\scripts\dd_profile_snippet.ps1"
#
# Alias Naming Convention:
#   dd-*     = Dev Dito commands (short prefix)
#   devdito* = Dev Dito commands (explicit prefix)
#
# Quick Reference:
#   dd              Interactive wizard / help
#   dd-install      Install/update Dev Dito
#   dd-up           Start all services
#   dd-down         Stop all services
#   dd-status       Show stack and pipeline status
#   dd-fetch        Run wiki fetcher pipeline
#   dd-logs         View container logs
#   dd-sandbox      Open wiki-sandbox (stack-a)
#   dd-sandbox-up   Start wiki-sandbox
# =============================================================================

# =============================================================================
# CONFIGURATION
# =============================================================================

$script:DD_REPO_ROOT = 'D:\_Repositories\_Diploma_Thesis_Repositories\dev_dito'
$script:DD_COMPOSE_FILE = "$script:DD_REPO_ROOT\backend_services\docker-compose.yml"
$script:DD_STACK_NAME = 'stack-g-devdito'
$script:DD_GITHUB_REPO = 'https://github.com/IxI-Enki/DA_2026_dev_dito.git'

# External stack paths (leonidas ecosystem)
$script:DD_LEONIDAS_STACKS = 'D:\_Repositories\year_2025_26\SYP_2025_26\leonie\internal_leonidas\stacks'
$script:DD_SANDBOX_COMPOSE = "$script:DD_LEONIDAS_STACKS\stack-a-wiki-sandbox"
$script:DD_WIKI_COMPOSE = "$script:DD_LEONIDAS_STACKS\stack-g-devdito"

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

function Show-DevDitoBanner {
    Write-Host ""
    Write-Host "  ____             ____  _ _        " -ForegroundColor Cyan
    Write-Host " |  _ \  _____   _|  _ \(_) |_ ___  " -ForegroundColor Cyan
    Write-Host " | | | |/ _ \ \ / / | | | | __/ _ \ " -ForegroundColor Cyan
    Write-Host " | |_| |  __/\ V /| |_| | | || (_) |" -ForegroundColor Cyan
    Write-Host " |____/ \___| \_/ |____/|_|\__\___/ " -ForegroundColor Cyan
    Write-Host ""
    Write-Host " DokuWiki RAG Pipeline Manager" -ForegroundColor White
    Write-Host ""
}

function Test-DevDitoInstalled {
    return (Test-Path $script:DD_REPO_ROOT) -and (Test-Path $script:DD_COMPOSE_FILE)
}

function Test-DevDitoRunning {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { return $false }
    $containers = docker ps --filter "name=dev-dito" --format "{{.Names}}" 2>$null
    return ($containers -and $containers.Count -gt 0)
}

function Test-ContainerRunning {
    param([string]$Name)
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { return $false }
    $status = docker ps --filter "name=$Name" --format "{{.Status}}" 2>$null
    return ($null -ne $status -and $status -ne '')
}

function Test-DockerDaemonRunning {
    try {
        docker info 2>&1 | Out-Null
        return $LASTEXITCODE -eq 0
    }
    catch { return $false }
}

function Start-DockerDesktopIfNeeded {
    <#
    .SYNOPSIS
    Ensures Docker Desktop is running. Starts it if needed, waits up to 120s.
    Returns $true when Docker daemon is ready, $false on failure.
    #>
    if (Test-DockerDaemonRunning) { return $true }

    # Docker CLI installed?
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        Write-Host "[ERROR] Docker is not installed." -ForegroundColor Red
        Write-Host "        Install via: winget install Docker.DockerDesktop" -ForegroundColor Yellow
        return $false
    }

    # Locate and launch Docker Desktop
    $paths = @(
        "$env:ProgramFiles\Docker\Docker\Docker Desktop.exe",
        "$env:LOCALAPPDATA\Docker\Docker Desktop.exe"
    )
    $launched = $false
    foreach ($p in $paths) {
        if (Test-Path $p) {
            Write-Host "[INFO] Starting Docker Desktop..." -ForegroundColor Cyan
            Start-Process -FilePath $p -WindowStyle Minimized
            $launched = $true
            break
        }
    }
    if (-not $launched) {
        Write-Host "[ERROR] Could not find Docker Desktop executable." -ForegroundColor Red
        Write-Host "        Searched: $($paths -join ', ')" -ForegroundColor Yellow
        return $false
    }

    # Wait for the daemon to become ready (up to 120 s)
    Write-Host "[INFO] Waiting for Docker daemon (up to 120s)..." -ForegroundColor Cyan
    $deadline = (Get-Date).AddSeconds(120)
    while ((Get-Date) -lt $deadline) {
        if (Test-DockerDaemonRunning) {
            Write-Host "[OK] Docker is ready." -ForegroundColor Green
            return $true
        }
        Write-Host "." -NoNewline
        Start-Sleep -Seconds 3
    }
    Write-Host ""
    Write-Host "[ERROR] Docker did not become ready within 120 seconds." -ForegroundColor Red
    return $false
}

function Get-DevDitoOrchestratorUrl {
    return "http://localhost:8089"
}

# =============================================================================
# MAIN WIZARD FUNCTION
# =============================================================================

function Invoke-DevDito {
    <#
    .SYNOPSIS
        Dev Dito - DokuWiki RAG Pipeline Manager

    .DESCRIPTION
        Central command for Dev Dito management. Provides installation,
        Docker stack control, pipeline execution, and status monitoring.

        Part of the HTL Leonding multi-stack ecosystem:
          Stack-A  wiki-sandbox       (port 8090)
          Stack-B  wiki-core          (Keycloak, port 8081)
          Stack-D  ai-core            (Qdrant, port 6333)
          Stack-G  devdito            (Orchestrator 8089, Wiki 8080, Qdrant 6334)
          Stack-H  mcp                (Semantic Search, port 3000)

    .PARAMETER Action
        Action to perform. Run 'dd -Help' for full list.

    .PARAMETER Force
        Skip confirmations for destructive operations.

    .PARAMETER Follow
        Follow log output (for logs action).

    .PARAMETER Target
        Specify target service (logs: orchestrator/qdrant, open: wiki/admin/api/sandbox).

    .PARAMETER Help
        Show detailed help with examples.

    .EXAMPLE
        dd
        # Interactive mode - shows status and available commands

    .EXAMPLE
        dd -Action up
        # Start all Dev Dito Docker services

    .EXAMPLE
        dd -Action sandbox-up
        # Start wiki-sandbox (stack-a) for extension testing

    .EXAMPLE
        dd -Action logs -Follow -Target qdrant
        # Follow Qdrant container logs in real-time

    .LINK
        https://github.com/IxI-Enki/DA_2026_dev_dito
    #>
    [CmdletBinding(DefaultParameterSetName = 'Interactive')]
    param(
        [Parameter(Position = 0, ParameterSetName = 'Action')]
        [ValidateSet(
            'install', 'up', 'down', 'restart', 'status', 'logs',
            'fetch', 'evaluate', 'preprocess', 'embed', 'deploy',
            'health', 'open', 'plugin', 'pull', 'build', 'help',
            'sandbox-up', 'sandbox-down', 'sandbox-status', 'sandbox-open'
        )]
        [string]$Action,

        [Parameter(ParameterSetName = 'Action')]
        [switch]$Force,

        [Parameter(ParameterSetName = 'Action')]
        [switch]$Follow,

        [Parameter(ParameterSetName = 'Action')]
        [string]$Target,

        [Parameter(ParameterSetName = 'Help')]
        [switch]$Help
    )

    # Show help
    if ($Help -or $Action -eq 'help') {
        Show-DevDitoHelp
        return
    }

    # Interactive mode (no action specified)
    if (-not $Action) {
        Show-DevDitoBanner

        if (-not (Test-DevDitoInstalled)) {
            Write-Host "[WARN] Dev Dito not installed at: $script:DD_REPO_ROOT" -ForegroundColor Yellow
            Write-Host ""
            Write-Host "Run 'dd -Action install' or 'dd-install' to install." -ForegroundColor Cyan
            return
        }

        # Show quick status
        Write-Host "Status:" -ForegroundColor Cyan
        if (Test-DevDitoRunning) {
            Write-Host "  [OK] Services running" -ForegroundColor Green
            $containers = docker ps --filter "name=dev-dito" --format "{{.Names}}: {{.Status}}" 2>$null
            foreach ($c in $containers) {
                Write-Host "       $c" -ForegroundColor DarkGray
            }
        }
        else {
            Write-Host "  [--] Services not running" -ForegroundColor Yellow
        }

        # Check sandbox
        if (Test-ContainerRunning 'wiki-sandbox') {
            Write-Host "  [OK] Sandbox running (port 8090)" -ForegroundColor Green
        }

        Write-Host ""
        Write-Host "Quick Commands:" -ForegroundColor Cyan
        Write-Host "  dd-up        Start services"
        Write-Host "  dd-down      Stop services"
        Write-Host "  dd-status    Full status"
        Write-Host "  dd-fetch     Run wiki fetch"
        Write-Host "  dd-logs      View logs"
        Write-Host "  dd -Help     Show full help"
        Write-Host ""
        return
    }

    # Execute action
    switch ($Action) {
        'install'        { Invoke-DevDitoInstall -Force:$Force }
        'pull'           { Invoke-DevDitoPull }
        'build'          { Invoke-DevDitoBuild }
        'up'             { Invoke-DevDitoUp }
        'down'           { Invoke-DevDitoDown -Force:$Force }
        'restart'        { Invoke-DevDitoRestart -Force:$Force }
        'status'         { Get-DevDitoStatus }
        'logs'           { Get-DevDitoLogs -Follow:$Follow -Target:$Target }
        'health'         { Test-DevDitoHealth }
        'open'           { Open-DevDitoWeb -Target:$Target }
        'plugin'         { Invoke-DevDitoDeployPlugin }
        'fetch'          { Invoke-DevDitoPipeline -Stage 'fetch' }
        'evaluate'       { Invoke-DevDitoPipeline -Stage 'evaluate' }
        'preprocess'     { Invoke-DevDitoPipeline -Stage 'preprocess' }
        'embed'          { Invoke-DevDitoPipeline -Stage 'embed' }
        'deploy'         { Invoke-DevDitoPipeline -Stage 'deploy' }
        'sandbox-up'     { Invoke-SandboxUp }
        'sandbox-down'   { Invoke-SandboxDown }
        'sandbox-status' { Get-SandboxStatus }
        'sandbox-open'   { Open-DevDitoWeb -Target 'sandbox' }
    }
}

# =============================================================================
# ACTION FUNCTIONS
# =============================================================================

function Invoke-DevDitoInstall {
    param([switch]$Force)

    Show-DevDitoBanner
    Write-Host "=== Installing Dev Dito ===" -ForegroundColor Cyan

    if (Test-DevDitoInstalled) {
        Write-Host "[INFO] Dev Dito already installed at: $script:DD_REPO_ROOT" -ForegroundColor Yellow

        if (-not $Force) {
            $confirm = Read-Host "Update existing installation? (y/N)"
            if ($confirm -ne 'y' -and $confirm -ne 'Y') {
                Write-Host "[INFO] Installation cancelled" -ForegroundColor Yellow
                return
            }
        }

        # Run install.ps1 for update
        Push-Location $script:DD_REPO_ROOT
        try {
            & "$script:DD_REPO_ROOT\install.ps1" -Force:$Force
        }
        finally {
            Pop-Location
        }
    }
    else {
        Write-Host "[INFO] Cloning Dev Dito repository..." -ForegroundColor Cyan

        $parentDir = Split-Path -Parent $script:DD_REPO_ROOT
        if (-not (Test-Path $parentDir)) {
            New-Item -ItemType Directory -Path $parentDir -Force | Out-Null
        }

        Push-Location $parentDir
        try {
            git clone $script:DD_GITHUB_REPO (Split-Path -Leaf $script:DD_REPO_ROOT)

            if ($LASTEXITCODE -eq 0) {
                Write-Host "[OK] Repository cloned" -ForegroundColor Green

                # Run install script
                Push-Location $script:DD_REPO_ROOT
                try {
                    & "$script:DD_REPO_ROOT\install.ps1" -Force:$Force
                }
                finally {
                    Pop-Location
                }
            }
            else {
                Write-Host "[ERROR] Failed to clone repository" -ForegroundColor Red
            }
        }
        finally {
            Pop-Location
        }
    }
}

function Invoke-DevDitoPull {
    Write-Host "=== Pulling Latest Changes ===" -ForegroundColor Cyan

    if (-not (Test-DevDitoInstalled)) {
        Write-Host "[ERROR] Dev Dito not installed. Run 'dd-install' first." -ForegroundColor Red
        return
    }

    Push-Location $script:DD_REPO_ROOT
    try {
        git fetch --all
        git pull --rebase

        if ($LASTEXITCODE -eq 0) {
            Write-Host "[OK] Repository updated" -ForegroundColor Green
        }
        else {
            Write-Host "[WARN] Pull may have conflicts - check git status" -ForegroundColor Yellow
        }
    }
    finally {
        Pop-Location
    }
}

function Invoke-DevDitoBuild {
    Write-Host "=== Building Docker Images ===" -ForegroundColor Cyan

    if (-not (Test-DevDitoInstalled)) {
        Write-Host "[ERROR] Dev Dito not installed. Run 'dd-install' first." -ForegroundColor Red
        return
    }

    Push-Location "$script:DD_REPO_ROOT\backend_services"
    try {
        docker compose -p $script:DD_STACK_NAME build

        if ($LASTEXITCODE -eq 0) {
            Write-Host "[OK] Images built successfully" -ForegroundColor Green
        }
        else {
            Write-Host "[ERROR] Build failed" -ForegroundColor Red
        }
    }
    finally {
        Pop-Location
    }
}

function Invoke-DevDitoUp {
    Write-Host "=== Starting Dev Dito Services ===" -ForegroundColor Cyan

    if (-not (Test-DevDitoInstalled)) {
        Write-Host "[ERROR] Dev Dito not installed. Run 'dd-install' first." -ForegroundColor Red
        return
    }

    # --- Ensure Docker Desktop is running ---
    if (-not (Start-DockerDesktopIfNeeded)) {
        Write-Host "[ERROR] Cannot proceed without Docker. Aborting." -ForegroundColor Red
        return
    }

    # Ensure network exists
    $networks = docker network ls --format "{{.Name}}" 2>$null
    if ($networks -notcontains 'leonidas-network') {
        Write-Host "[INFO] Creating leonidas-network..." -ForegroundColor Cyan
        docker network create --driver bridge --attachable leonidas-network 2>$null
    }

    # --- Start core services (orchestrator + qdrant) ---
    Push-Location "$script:DD_REPO_ROOT\backend_services"
    try {
        # Capture output; filter known orphan warning (wiki container may belong
        # to a different compose origin while sharing the project name).
        $composeOut = docker compose -p $script:DD_STACK_NAME up -d 2>&1
        $exitCode = $LASTEXITCODE
        $composeOut | ForEach-Object {
            $line = $_.ToString()
            if ($line -notmatch 'Found orphan containers') { Write-Host $line }
        }
        if ($exitCode -ne 0) {
            Write-Host "[ERROR] Failed to start core services" -ForegroundColor Red
            return
        }
        Write-Host "[OK] Core services started (orchestrator, qdrant)" -ForegroundColor Green
    }
    finally {
        Pop-Location
    }

    # --- Start DokuWiki ---
    # Strategy priority (avoids orphan / project-identity conflicts):
    #   1. Already running          -> skip
    #   2. docker start (existing)  -> fastest, no compose file collision
    #   3. Profile wiki (same file) -> cleanest first-time path
    #   4. Leonidas stacks compose  -> external fallback (own project name)
    Write-Host ""
    if (Test-ContainerRunning 'dev-dito-wiki') {
        Write-Host "[OK] DokuWiki already running" -ForegroundColor Green
    }
    else {
        $wikiStarted = $false

        # (2) Try starting an existing stopped container first (most common case)
        $existing = docker ps -a --filter "name=^dev-dito-wiki$" --format "{{.Names}}" 2>$null
        if ($existing -eq 'dev-dito-wiki') {
            Write-Host "[INFO] Starting existing dev-dito-wiki container..." -ForegroundColor Cyan
            docker start dev-dito-wiki 2>$null | Out-Null
            Start-Sleep -Milliseconds 500
            if (Test-ContainerRunning 'dev-dito-wiki') {
                $wikiStarted = $true
                Write-Host "[OK] DokuWiki started (existing container)" -ForegroundColor Green
            }
        }

        # (3) Profile wiki from the same compose file (.env required)
        if (-not $wikiStarted) {
            $envFile = "$script:DD_REPO_ROOT\backend_services\.env"
            if (Test-Path $envFile) {
                $envContent = Get-Content $envFile -Raw
                if ($envContent -match 'WIKI_ROOT=(.+)' -and $Matches[1].Trim() -ne '') {
                    $wikiRoot = $Matches[1].Trim()
                    if (Test-Path $wikiRoot) {
                        Write-Host "[INFO] Starting DokuWiki via profile wiki (WIKI_ROOT=$wikiRoot)..." -ForegroundColor Cyan
                        Push-Location "$script:DD_REPO_ROOT\backend_services"
                        try {
                            docker compose -p $script:DD_STACK_NAME --profile wiki up -d 2>$null
                            if ($LASTEXITCODE -eq 0 -and (Test-ContainerRunning 'dev-dito-wiki')) {
                                $wikiStarted = $true
                                Write-Host "[OK] DokuWiki started (profile wiki)" -ForegroundColor Green
                            }
                        }
                        finally {
                            Pop-Location
                        }
                    }
                }
            }
        }

        # (4) Leonidas stacks compose (external fallback, own project name)
        if (-not $wikiStarted -and (Test-Path "$script:DD_WIKI_COMPOSE\docker-compose.yml")) {
            Write-Host "[INFO] Starting DokuWiki from leonidas stacks..." -ForegroundColor Cyan
            Push-Location $script:DD_WIKI_COMPOSE
            try {
                # NOTE: No -p override — uses directory-based project name to
                # avoid mixing with stack-g-devdito from backend_services/.
                docker compose up -d 2>$null
                if ($LASTEXITCODE -eq 0 -and (Test-ContainerRunning 'dev-dito-wiki')) {
                    $wikiStarted = $true
                    Write-Host "[OK] DokuWiki started (leonidas stacks)" -ForegroundColor Green
                }
            }
            finally {
                Pop-Location
            }
        }

        if (-not $wikiStarted) {
            Write-Host "[WARN] DokuWiki could not be started." -ForegroundColor Yellow
            Write-Host "       Options:" -ForegroundColor Yellow
            Write-Host "       1. Set WIKI_ROOT in backend_services/.env (see .env.template)" -ForegroundColor DarkGray
            Write-Host "       2. Start wiki manually from leonidas stacks" -ForegroundColor DarkGray
        }
    }

    Write-Host ""
    Write-Host "Access points:" -ForegroundColor Cyan
    Write-Host "  DokuWiki:     http://localhost:8080" -ForegroundColor White
    Write-Host "  Admin Panel:  http://localhost:8080/?do=admin&page=devdito" -ForegroundColor White
    Write-Host "  Orchestrator: http://localhost:8089" -ForegroundColor White
    Write-Host "  Qdrant:       http://localhost:6334" -ForegroundColor White
}

function Invoke-DevDitoDown {
    param([switch]$Force)

    Write-Host "=== Stopping Dev Dito Services ===" -ForegroundColor Cyan

    if (-not $Force) {
        $confirm = Read-Host "Stop all Dev Dito services? (y/N)"
        if ($confirm -ne 'y' -and $confirm -ne 'Y') {
            Write-Host "[INFO] Cancelled" -ForegroundColor Yellow
            return
        }
    }

    Push-Location "$script:DD_REPO_ROOT\backend_services"
    try {
        docker compose -p $script:DD_STACK_NAME down

        if ($LASTEXITCODE -eq 0) {
            Write-Host "[OK] Services stopped" -ForegroundColor Green
        }
    }
    finally {
        Pop-Location
    }

    # Also stop wiki if it was started externally
    if (Test-ContainerRunning 'dev-dito-wiki') {
        Write-Host "[INFO] Stopping DokuWiki container..." -ForegroundColor Cyan
        docker stop dev-dito-wiki 2>$null | Out-Null
        Write-Host "[OK] DokuWiki stopped" -ForegroundColor Green
    }
}

function Invoke-DevDitoRestart {
    param([switch]$Force)

    Invoke-DevDitoDown -Force:$Force
    Start-Sleep -Seconds 2
    Invoke-DevDitoUp
}

# =============================================================================
# STATUS & MONITORING
# =============================================================================

function Get-DevDitoStatus {
    Show-DevDitoBanner

    Write-Host "=== Docker Stack Status ===" -ForegroundColor Cyan

    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        Write-Host "[ERROR] Docker not found" -ForegroundColor Red
        return
    }

    # --- Stack-G containers ---
    Write-Host ""
    Write-Host "  Stack-G (devdito):" -ForegroundColor Yellow
    $containers = docker ps -a --filter "name=dev-dito" --format "    {{.Names}}`t{{.Status}}" 2>$null
    if ($containers) {
        # Output each line separately to avoid array flattening
        if ($containers -is [array]) {
            foreach ($line in $containers) {
                $color = if ($line -match 'Up ') { 'Green' }
                         elseif ($line -match 'Exited') { 'Red' }
                         else { 'DarkGray' }
                Write-Host $line -ForegroundColor $color
            }
        }
        else {
            $color = if ($containers -match 'Up ') { 'Green' }
                     elseif ($containers -match 'Exited') { 'Red' }
                     else { 'DarkGray' }
            Write-Host $containers -ForegroundColor $color
        }
    }
    else {
        Write-Host "    [--] No dev-dito containers found" -ForegroundColor DarkGray
    }

    # --- Stack-A containers ---
    Write-Host ""
    Write-Host "  Stack-A (wiki-sandbox):" -ForegroundColor Yellow
    $sandbox = docker ps -a --filter "name=wiki-sandbox" --format "    {{.Names}}`t{{.Status}}" 2>$null
    if ($sandbox) {
        $color = if ($sandbox -match 'Up ') { 'Green' }
                 elseif ($sandbox -match 'Exited') { 'Red' }
                 else { 'DarkGray' }
        Write-Host $sandbox -ForegroundColor $color
    }
    else {
        Write-Host "    [--] No sandbox containers found" -ForegroundColor DarkGray
    }

    Write-Host ""
    Write-Host "=== Pipeline Status ===" -ForegroundColor Cyan

    # Try to get pipeline status from orchestrator
    try {
        $response = Invoke-RestMethod -Uri "$(Get-DevDitoOrchestratorUrl)/status" -TimeoutSec 5 -ErrorAction Stop

        foreach ($stage in $response.stages) {
            $statusColor = switch ($stage.status) {
                'success'   { 'Green' }
                'completed' { 'Green' }
                'running'   { 'Cyan' }
                'error'     { 'Red' }
                'cancelled' { 'Yellow' }
                'never_run' { 'DarkGray' }
                default     { 'DarkGray' }
            }

            $lastRun = if ($stage.last_run) {
                try {
                    $dt = [DateTime]::Parse($stage.last_run)
                    $dt.ToString('yyyy-MM-dd HH:mm')
                }
                catch { $stage.last_run }
            }
            else { 'never' }

            Write-Host ("  {0,-20} [{1,-10}]  Last: {2}" -f $stage.name, $stage.status, $lastRun) -ForegroundColor $statusColor
        }

        if ($response.active_job) {
            Write-Host ""
            Write-Host "  Active Job: $($response.active_job.job_id)" -ForegroundColor Yellow
        }
    }
    catch {
        Write-Host "  [INFO] Orchestrator not responding (services may be stopped)" -ForegroundColor Yellow
    }

    Write-Host ""
}

function Get-DevDitoLogs {
    param(
        [switch]$Follow,
        [string]$Target = 'orchestrator'
    )

    Push-Location "$script:DD_REPO_ROOT\backend_services"
    try {
        $followFlag = if ($Follow) { '-f' } else { '--tail=100' }
        docker compose -p $script:DD_STACK_NAME logs $followFlag $Target
    }
    finally {
        Pop-Location
    }
}

function Test-DevDitoHealth {
    Write-Host "=== Health Check ===" -ForegroundColor Cyan
    Write-Host ""

    $endpoints = @(
        @{ Name = 'Orchestrator';  Url = 'http://localhost:8089/health';  Stack = 'Stack-G' },
        @{ Name = 'DokuWiki';      Url = 'http://localhost:8080';         Stack = 'Stack-G' },
        @{ Name = 'Qdrant';        Url = 'http://localhost:6334/healthz'; Stack = 'Stack-G' },
        @{ Name = 'Wiki Sandbox';  Url = 'http://localhost:8090';         Stack = 'Stack-A' }
    )

    foreach ($ep in $endpoints) {
        try {
            $null = Invoke-WebRequest -Uri $ep.Url -TimeoutSec 5 -ErrorAction Stop
            Write-Host ("[OK] {0,-16} {1,-10} {2}" -f $ep.Name, $ep.Stack, $ep.Url) -ForegroundColor Green
        }
        catch {
            Write-Host ("[--] {0,-16} {1,-10} {2}" -f $ep.Name, $ep.Stack, $ep.Url) -ForegroundColor Red
        }
    }

    Write-Host ""
}

function Open-DevDitoWeb {
    param([string]$Target = 'wiki')

    $url = switch ($Target) {
        'wiki'    { 'http://localhost:8080' }
        'admin'   { 'http://localhost:8080/?do=admin&page=devdito' }
        'api'     { 'http://localhost:8089' }
        'qdrant'  { 'http://localhost:6334/dashboard' }
        'sandbox' { 'http://localhost:8090' }
        default   { 'http://localhost:8080' }
    }

    Write-Host "[INFO] Opening $url" -ForegroundColor Cyan
    Start-Process $url
}

function Invoke-DevDitoDeployPlugin {
    Write-Host "=== Deploying DokuWiki Plugin ===" -ForegroundColor Cyan

    $deployScript = "$script:DD_REPO_ROOT\scripts\deploy-plugin.ps1"

    if (Test-Path $deployScript) {
        & $deployScript
    }
    else {
        Write-Host "[ERROR] Deploy script not found: $deployScript" -ForegroundColor Red
    }
}

function Invoke-DevDitoPipeline {
    param(
        [Parameter(Mandatory)]
        [ValidateSet('fetch', 'evaluate', 'preprocess', 'embed', 'deploy')]
        [string]$Stage
    )

    Write-Host "=== Running Pipeline: $Stage ===" -ForegroundColor Cyan

    if (-not (Test-DevDitoRunning)) {
        Write-Host "[ERROR] Dev Dito services not running. Run 'dd-up' first." -ForegroundColor Red
        return
    }

    try {
        $response = Invoke-RestMethod -Uri "$(Get-DevDitoOrchestratorUrl)/run/$Stage" -Method Post -TimeoutSec 10 -ErrorAction Stop

        if ($response.success) {
            Write-Host "[OK] $($response.message)" -ForegroundColor Green
            Write-Host "Job ID: $($response.job_id)" -ForegroundColor Cyan
            Write-Host ""
            Write-Host "Monitor progress:" -ForegroundColor DarkGray
            Write-Host "  dd-status                  # Quick overview" -ForegroundColor DarkGray
            Write-Host "  dd-logs -Follow             # Live logs" -ForegroundColor DarkGray
        }
        else {
            Write-Host "[ERROR] $($response.message)" -ForegroundColor Red
        }
    }
    catch {
        Write-Host "[ERROR] Failed to start pipeline: $_" -ForegroundColor Red
    }
}

# =============================================================================
# SANDBOX (Stack-A) MANAGEMENT
# =============================================================================

function Invoke-SandboxUp {
    Write-Host "=== Starting Wiki Sandbox (Stack-A) ===" -ForegroundColor Cyan

    if (Test-ContainerRunning 'wiki-sandbox') {
        Write-Host "[OK] Wiki sandbox already running" -ForegroundColor Green
        Write-Host "     http://localhost:8090" -ForegroundColor DarkGray
        return
    }

    # Ensure network exists
    $networks = docker network ls --format "{{.Name}}" 2>$null
    if ($networks -notcontains 'leonidas-network') {
        Write-Host "[INFO] Creating leonidas-network..." -ForegroundColor Cyan
        docker network create --driver bridge --attachable leonidas-network 2>$null
    }

    # Try compose file first
    if (Test-Path "$script:DD_SANDBOX_COMPOSE\docker-compose.yml") {
        Push-Location $script:DD_SANDBOX_COMPOSE
        try {
            docker compose up -d
            if ($LASTEXITCODE -eq 0) {
                Write-Host "[OK] Wiki sandbox started" -ForegroundColor Green
                Write-Host "     http://localhost:8090" -ForegroundColor DarkGray
            }
            else {
                Write-Host "[ERROR] Failed to start sandbox" -ForegroundColor Red
            }
        }
        finally {
            Pop-Location
        }
    }
    else {
        # Fallback: try to start existing stopped container
        $existing = docker ps -a --filter "name=wiki-sandbox" --format "{{.Names}}" 2>$null
        if ($existing) {
            docker start wiki-sandbox 2>$null | Out-Null
            if (Test-ContainerRunning 'wiki-sandbox') {
                Write-Host "[OK] Wiki sandbox started (existing container)" -ForegroundColor Green
                Write-Host "     http://localhost:8090" -ForegroundColor DarkGray
            }
            else {
                Write-Host "[ERROR] Failed to start sandbox container" -ForegroundColor Red
            }
        }
        else {
            Write-Host "[WARN] No sandbox compose file found at:" -ForegroundColor Yellow
            Write-Host "       $script:DD_SANDBOX_COMPOSE" -ForegroundColor DarkGray
            Write-Host "       And no existing container found." -ForegroundColor DarkGray
        }
    }
}

function Invoke-SandboxDown {
    Write-Host "=== Stopping Wiki Sandbox (Stack-A) ===" -ForegroundColor Cyan

    if (-not (Test-ContainerRunning 'wiki-sandbox')) {
        Write-Host "[INFO] Wiki sandbox is not running" -ForegroundColor Yellow
        return
    }

    if (Test-Path "$script:DD_SANDBOX_COMPOSE\docker-compose.yml") {
        Push-Location $script:DD_SANDBOX_COMPOSE
        try {
            docker compose down
            Write-Host "[OK] Wiki sandbox stopped" -ForegroundColor Green
        }
        finally {
            Pop-Location
        }
    }
    else {
        docker stop wiki-sandbox 2>$null | Out-Null
        Write-Host "[OK] Wiki sandbox stopped" -ForegroundColor Green
    }
}

function Get-SandboxStatus {
    Write-Host "=== Wiki Sandbox (Stack-A) Status ===" -ForegroundColor Cyan
    Write-Host ""

    $container = docker ps -a --filter "name=wiki-sandbox" --format "{{.Names}}\t{{.Status}}\t{{.Ports}}" 2>$null
    if ($container) {
        $color = if ($container -match 'Up ') { 'Green' } else { 'Red' }
        Write-Host "  $container" -ForegroundColor $color
    }
    else {
        Write-Host "  [--] No wiki-sandbox container found" -ForegroundColor DarkGray
    }

    Write-Host ""
    Write-Host "  URL: http://localhost:8090" -ForegroundColor DarkGray
    Write-Host ""
}

# =============================================================================
# ENHANCED HELP
# =============================================================================

function Show-DevDitoHelp {
    Show-DevDitoBanner

    Write-Host "USAGE:" -ForegroundColor Yellow
    Write-Host "  dd [Action] [Options]"
    Write-Host ""

    # --- Service Management ---
    Write-Host "SERVICE MANAGEMENT:" -ForegroundColor Yellow
    Write-Host "  install     Clone repo (if needed) and run installation"
    Write-Host "  pull        Pull latest changes from GitHub"
    Write-Host "  build       Build Docker images"
    Write-Host "  up          Start all Dev Dito services (orchestrator + qdrant + wiki)"
    Write-Host "  down        Stop all Dev Dito services"
    Write-Host "  restart     Restart all services"
    Write-Host "  status      Show comprehensive status of all stacks and pipeline"
    Write-Host "  logs        View container logs"
    Write-Host "  health      Check all service endpoints (all stacks)"
    Write-Host "  open        Open web interfaces in browser"
    Write-Host "  plugin      Deploy DokuWiki plugin to running instance"
    Write-Host ""

    # --- Pipeline ---
    Write-Host "PIPELINE STAGES:" -ForegroundColor Yellow
    Write-Host "  fetch       [1/5]  Fetch wiki content via JSON-RPC API"
    Write-Host "  evaluate    [2/5]  Evaluate fetched content quality (LLM-based)"
    Write-Host "  preprocess  [3/5]  Convert to RAG-optimized Markdown with frontmatter"
    Write-Host "  embed       [4/5]  Generate vector embeddings (OpenAI API)"
    Write-Host "  deploy      [5/5]  Upload embeddings to Qdrant vector database"
    Write-Host ""

    # --- Sandbox ---
    Write-Host "SANDBOX (Stack-A):" -ForegroundColor Yellow
    Write-Host "  sandbox-up      Start wiki-sandbox DokuWiki instance (port 8090)"
    Write-Host "  sandbox-down    Stop wiki-sandbox"
    Write-Host "  sandbox-status  Show sandbox container status"
    Write-Host "  sandbox-open    Open sandbox in browser"
    Write-Host ""

    # --- Options ---
    Write-Host "OPTIONS:" -ForegroundColor Yellow
    Write-Host "  -Force      Skip confirmations (for down, restart, install)"
    Write-Host "  -Follow     Follow log output in real-time (for logs)"
    Write-Host "  -Target     Specify target service or URL:"
    Write-Host "              logs:  orchestrator | qdrant"
    Write-Host "              open:  wiki | admin | api | qdrant | sandbox"
    Write-Host ""

    # --- Shortcuts ---
    Write-Host "SHORTCUTS:" -ForegroundColor Yellow
    Write-Host "  dd-install     = dd -Action install"
    Write-Host "  dd-up          = dd -Action up"
    Write-Host "  dd-down        = dd -Action down"
    Write-Host "  dd-restart     = dd -Action restart"
    Write-Host "  dd-status      = dd -Action status"
    Write-Host "  dd-logs        = dd -Action logs -Follow"
    Write-Host "  dd-health      = dd -Action health"
    Write-Host "  dd-open        = dd -Action open -Target wiki"
    Write-Host "  dd-admin       = dd -Action open -Target admin"
    Write-Host "  dd-fetch       = dd -Action fetch"
    Write-Host "  dd-embed       = dd -Action embed"
    Write-Host "  dd-sandbox     = dd -Action sandbox-open"
    Write-Host "  dd-sandbox-open= dd -Action sandbox-open"
    Write-Host "  dd-sandbox-up  = dd -Action sandbox-up"
    Write-Host "  dd-sandbox-down= dd -Action sandbox-down"
    Write-Host "  cd-dd          = Set-Location to dev_dito repo root"
    Write-Host ""

    # --- Examples ---
    Write-Host "EXAMPLES:" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  # ---- Getting Started ----" -ForegroundColor DarkCyan
    Write-Host "  dd-install                             # First-time setup"
    Write-Host "  dd-up                                  # Start all services"
    Write-Host "  dd-health                              # Verify everything works"
    Write-Host ""
    Write-Host "  # ---- Daily Development ----" -ForegroundColor DarkCyan
    Write-Host "  dd-up                                  # Start services"
    Write-Host "  dd-status                              # Check current state"
    Write-Host "  dd-open                                # Open DokuWiki in browser"
    Write-Host "  dd-admin                               # Open Admin panel"
    Write-Host "  dd-down                                # Stop when done"
    Write-Host ""
    Write-Host "  # ---- Full Pipeline Run ----" -ForegroundColor DarkCyan
    Write-Host "  dd-fetch                               # 1. Fetch wiki content"
    Write-Host "  dd -Action evaluate                    # 2. Evaluate quality"
    Write-Host "  dd -Action preprocess                  # 3. RAG preprocessing"
    Write-Host "  dd -Action embed                       # 4. Generate embeddings"
    Write-Host "  dd -Action deploy                      # 5. Upload to Qdrant"
    Write-Host ""
    Write-Host "  # ---- Logs & Debugging ----" -ForegroundColor DarkCyan
    Write-Host "  dd -Action logs -Follow                # Follow orchestrator logs"
    Write-Host "  dd -Action logs -Follow -Target qdrant # Follow Qdrant logs"
    Write-Host "  dd -Action logs -Target qdrant         # Last 100 Qdrant log lines"
    Write-Host ""
    Write-Host "  # ---- Sandbox / Testing ----" -ForegroundColor DarkCyan
    Write-Host "  dd sandbox-up                          # Start sandbox wiki"
    Write-Host "  dd sandbox-open                        # Open sandbox in browser"
    Write-Host "  dd sandbox-status                      # Check sandbox state"
    Write-Host "  dd sandbox-down                        # Stop sandbox"
    Write-Host ""
    Write-Host "  # ---- Update & Rebuild ----" -ForegroundColor DarkCyan
    Write-Host "  dd -Action pull                        # Pull latest code"
    Write-Host "  dd -Action build                       # Rebuild Docker images"
    Write-Host "  dd -Action restart -Force              # Restart without confirmation"
    Write-Host "  dd -Action plugin                      # Re-deploy DokuWiki plugin"
    Write-Host ""
    Write-Host "  # ---- Flag Combinations ----" -ForegroundColor DarkCyan
    Write-Host "  dd -Action install -Force              # Non-interactive install"
    Write-Host "  dd -Action down -Force                 # Stop without confirmation"
    Write-Host "  dd -Action open -Target qdrant         # Open Qdrant dashboard"
    Write-Host "  dd -Action open -Target api            # Open Orchestrator API"
    Write-Host ""

    # --- Stack Overview ---
    Write-Host "STACK OVERVIEW:" -ForegroundColor Yellow
    Write-Host "  Stack-A  wiki-sandbox       http://localhost:8090     DokuWiki test instance"
    Write-Host "  Stack-B  wiki-core          http://localhost:8081     Keycloak SSO"
    Write-Host "  Stack-D  ai-core            http://localhost:6333     Qdrant (main)"
    Write-Host "  Stack-G  devdito            http://localhost:8080     DokuWiki + Pipeline"
    Write-Host "  Stack-G  devdito-api        http://localhost:8089     Orchestrator API"
    Write-Host "  Stack-G  devdito-qdrant     http://localhost:6334     Qdrant (dev dito)"
    Write-Host "  Stack-H  mcp               http://localhost:3000     Semantic Search"
    Write-Host ""
}

# =============================================================================
# SET LOCATION ALIAS
# =============================================================================

function Set-LocationDevDito {
    if (Test-Path $script:DD_REPO_ROOT) {
        Set-Location $script:DD_REPO_ROOT
    }
    else {
        Write-Host "[WARN] Dev Dito not installed at: $script:DD_REPO_ROOT" -ForegroundColor Yellow
    }
}

# =============================================================================
# ALIAS REGISTRATION
# =============================================================================

# Main command
Set-Alias -Name dd -Value Invoke-DevDito
Set-Alias -Name devdito -Value Invoke-DevDito
Set-Alias -Name dev-dito -Value Invoke-DevDito

# Shortcut functions for common actions
function dd-install { Invoke-DevDito -Action install @args }
function dd-pull { Invoke-DevDito -Action pull }
function dd-build { Invoke-DevDito -Action build }
function dd-up { Invoke-DevDito -Action up }
function dd-down { Invoke-DevDito -Action down -Force }
function dd-restart { Invoke-DevDito -Action restart -Force }
function dd-status { Invoke-DevDito -Action status }
function dd-logs { Invoke-DevDito -Action logs -Follow @args }
function dd-health { Invoke-DevDito -Action health }
function dd-open { Invoke-DevDito -Action open -Target wiki }
function dd-admin { Invoke-DevDito -Action open -Target admin }
function dd-plugin { Invoke-DevDito -Action plugin }

# Pipeline shortcuts
function dd-fetch { Invoke-DevDito -Action fetch }
function dd-evaluate { Invoke-DevDito -Action evaluate }
function dd-preprocess { Invoke-DevDito -Action preprocess }
function dd-embed { Invoke-DevDito -Action embed }
function dd-deploy { Invoke-DevDito -Action deploy }

# Sandbox shortcuts (Stack-A)
function dd-sandbox { Invoke-DevDito -Action sandbox-open }
function dd-sandbox-open { Invoke-DevDito -Action sandbox-open }  # Alias for consistency
function dd-sandbox-up { Invoke-DevDito -Action sandbox-up }
function dd-sandbox-down { Invoke-DevDito -Action sandbox-down }
function dd-sandbox-status { Invoke-DevDito -Action sandbox-status }

# Location alias
Set-Alias -Name cd-dd -Value Set-LocationDevDito
Set-Alias -Name sl-dd -Value Set-LocationDevDito
Set-Alias -Name CD-DD -Value Set-LocationDevDito
Set-Alias -Name SL-DD -Value Set-LocationDevDito

# =============================================================================
# TAB COMPLETION
# =============================================================================

Register-ArgumentCompleter -CommandName 'Invoke-DevDito' -ParameterName 'Action' -ScriptBlock {
    param($commandName, $parameterName, $wordToComplete)
    @(
        'install', 'up', 'down', 'restart', 'status', 'logs',
        'fetch', 'evaluate', 'preprocess', 'embed', 'deploy',
        'health', 'open', 'plugin', 'pull', 'build', 'help',
        'sandbox-up', 'sandbox-down', 'sandbox-status', 'sandbox-open'
    ) |
    Where-Object { $_ -like "$wordToComplete*" } |
    ForEach-Object { [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterValue', $_) }
}

Register-ArgumentCompleter -CommandName 'Invoke-DevDito' -ParameterName 'Target' -ScriptBlock {
    param($commandName, $parameterName, $wordToComplete)
    @('wiki', 'admin', 'api', 'qdrant', 'orchestrator', 'sandbox') |
    Where-Object { $_ -like "$wordToComplete*" } |
    ForEach-Object { [System.Management.Automation.CompletionResult]::new($_, $_, 'ParameterValue', $_) }
}
