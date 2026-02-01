# =============================================================================
# Dev Dito - Installation Script
# =============================================================================
# One-command installation for Dev Dito
# Usage: git clone https://github.com/IxI-Enki/DA_2026_dev_dito.git && .\install.ps1
# =============================================================================

#Requires -Version 7.0

param(
    [switch]$SkipDocker,
    [switch]$SkipNetwork,
    [switch]$SkipMigration,
    [switch]$SkipBuild,
    [switch]$Force,
    [switch]$Help
)

$ErrorActionPreference = "Stop"
$script:VERSION = "1.0.0"
$script:PROJECT_ROOT = $PSScriptRoot

# =============================================================================
# Helper Functions (inline to avoid module loading issues)
# =============================================================================

function Show-Banner {
    Write-Host ""
    Write-Host "  ____             ____  _ _        " -ForegroundColor Cyan
    Write-Host " |  _ \  _____   _|  _ \(_) |_ ___  " -ForegroundColor Cyan
    Write-Host " | | | |/ _ \ \ / / | | | | __/ _ \ " -ForegroundColor Cyan
    Write-Host " | |_| |  __/\ V /| |_| | | || (_) |" -ForegroundColor Cyan
    Write-Host " |____/ \___| \_/ |____/|_|\__\___/ " -ForegroundColor Cyan
    Write-Host ""
    Write-Host " Pipeline Manager for DokuWiki" -ForegroundColor White
    Write-Host " Version: $script:VERSION" -ForegroundColor DarkGray
    Write-Host ""
    Write-Host "========================================" -ForegroundColor DarkGray
}

function Show-Help {
    Show-Banner
    Write-Host "Usage: .\install.ps1 [options]" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Options:" -ForegroundColor Yellow
    Write-Host "  -SkipDocker      Skip Docker check and startup"
    Write-Host "  -SkipNetwork     Skip network creation"
    Write-Host "  -SkipMigration   Skip migration detection"
    Write-Host "  -SkipBuild       Skip Docker image building"
    Write-Host "  -Force           Skip all confirmations"
    Write-Host "  -Help            Show this help message"
    Write-Host ""
    Write-Host "Examples:" -ForegroundColor Yellow
    Write-Host "  .\install.ps1                    # Full installation"
    Write-Host "  .\install.ps1 -SkipDocker        # Skip Docker check"
    Write-Host "  .\install.ps1 -Force             # Non-interactive mode"
    Write-Host ""
}

function Test-DockerInstalled {
    try {
        $null = Get-Command docker -ErrorAction SilentlyContinue
        return $true
    }
    catch { return $false }
}

function Test-DockerRunning {
    try {
        docker info 2>&1 | Out-Null
        return $LASTEXITCODE -eq 0
    }
    catch { return $false }
}

function Start-DockerDesktop {
    $paths = @(
        "$env:ProgramFiles\Docker\Docker\Docker Desktop.exe",
        "$env:LOCALAPPDATA\Docker\Docker Desktop.exe"
    )
    
    foreach ($path in $paths) {
        if (Test-Path $path) {
            Write-Host "[INFO] Starting Docker Desktop..." -ForegroundColor Cyan
            Start-Process -FilePath $path -WindowStyle Minimized
            return $true
        }
    }
    return $false
}

function Wait-ForDockerReady {
    param([int]$TimeoutSeconds = 120)
    
    $endTime = (Get-Date).AddSeconds($TimeoutSeconds)
    
    while ((Get-Date) -lt $endTime) {
        if (Test-DockerRunning) {
            return $true
        }
        Start-Sleep -Seconds 3
        Write-Host "." -NoNewline
    }
    Write-Host ""
    return $false
}

function Test-NetworkExists {
    $networks = docker network ls --format "{{.Name}}" 2>&1
    return $networks -contains "htl-wiki-network"
}

function New-HtlWikiNetwork {
    if (Test-NetworkExists) {
        Write-Host "[OK] Network 'htl-wiki-network' already exists" -ForegroundColor Green
        return $true
    }
    
    Write-Host "[INFO] Creating network 'htl-wiki-network'..." -ForegroundColor Cyan
    docker network create --driver bridge --attachable htl-wiki-network 2>&1 | Out-Null
    return $LASTEXITCODE -eq 0
}

function Find-LegacySetup {
    $legacy = @()
    $containers = docker ps -a --format "{{.Names}}" 2>&1
    $legacy += $containers | Where-Object { $_ -like "devdito_*" }
    
    $networks = docker network ls --format "{{.Name}}" 2>&1
    if ($networks -contains "devdito_network") {
        $legacy += "devdito_network"
    }
    
    return $legacy
}

# =============================================================================
# Main Installation Steps
# =============================================================================

function Step-Docker {
    Write-Host ""
    Write-Host "=== Step 1: Docker Check ===" -ForegroundColor Cyan
    
    if (-not (Test-DockerInstalled)) {
        Write-Host "[ERROR] Docker is not installed" -ForegroundColor Red
        Write-Host ""
        Write-Host "Please install Docker Desktop from:" -ForegroundColor Yellow
        Write-Host "  https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe" -ForegroundColor Green
        Write-Host ""
        Write-Host "Or via winget:" -ForegroundColor Yellow
        Write-Host "  winget install Docker.DockerDesktop" -ForegroundColor Green
        Write-Host ""
        return $false
    }
    
    Write-Host "[OK] Docker is installed" -ForegroundColor Green
    
    if (Test-DockerRunning) {
        Write-Host "[OK] Docker is running" -ForegroundColor Green
        return $true
    }
    
    Write-Host "[INFO] Docker is not running, attempting to start..." -ForegroundColor Yellow
    
    if (-not (Start-DockerDesktop)) {
        Write-Host "[ERROR] Could not find Docker Desktop executable" -ForegroundColor Red
        return $false
    }
    
    Write-Host "[INFO] Waiting for Docker to be ready (up to 2 minutes)..." -ForegroundColor Cyan
    
    if (-not (Wait-ForDockerReady -TimeoutSeconds 120)) {
        Write-Host "[ERROR] Docker did not start in time" -ForegroundColor Red
        return $false
    }
    
    Write-Host "[OK] Docker is ready" -ForegroundColor Green
    return $true
}

function Step-Network {
    Write-Host ""
    Write-Host "=== Step 2: Network Setup ===" -ForegroundColor Cyan
    
    if (-not (New-HtlWikiNetwork)) {
        Write-Host "[ERROR] Failed to create network" -ForegroundColor Red
        return $false
    }
    
    # Show connected containers
    $containers = docker network inspect htl-wiki-network --format '{{range .Containers}}{{.Name}} {{end}}' 2>&1
    if ($containers -and $LASTEXITCODE -eq 0) {
        $containerList = ($containers -split '\s+' | Where-Object { $_ })
        if ($containerList.Count -gt 0) {
            Write-Host "[INFO] Connected containers:" -ForegroundColor Cyan
            foreach ($c in $containerList) {
                Write-Host "  - $c" -ForegroundColor White
            }
        }
    }
    
    return $true
}

function Step-Migration {
    Write-Host ""
    Write-Host "=== Step 3: Migration Check ===" -ForegroundColor Cyan
    
    $legacy = Find-LegacySetup
    
    if ($legacy.Count -eq 0) {
        Write-Host "[OK] No legacy setup found" -ForegroundColor Green
        return $true
    }
    
    Write-Host "[WARN] Legacy Dev Dito components found:" -ForegroundColor Yellow
    foreach ($item in $legacy) {
        Write-Host "  - $item" -ForegroundColor White
    }
    
    if (-not $Force) {
        Write-Host ""
        $confirm = Read-Host "Migrate to new structure? This will stop and remove legacy containers. (y/N)"
        if ($confirm -ne "y" -and $confirm -ne "Y") {
            Write-Host "[INFO] Skipping migration" -ForegroundColor Yellow
            return $true
        }
    }
    
    # Stop and remove legacy containers
    Write-Host "[INFO] Removing legacy components..." -ForegroundColor Cyan
    foreach ($item in $legacy) {
        if ($item -eq "devdito_network") {
            docker network rm devdito_network 2>&1 | Out-Null
        }
        else {
            docker rm -f $item 2>&1 | Out-Null
        }
    }
    
    Write-Host "[OK] Migration complete" -ForegroundColor Green
    return $true
}

function Step-Build {
    Write-Host ""
    Write-Host "=== Step 4: Build Docker Images ===" -ForegroundColor Cyan
    
    $composeFile = Join-Path $script:PROJECT_ROOT "backend_services\docker-compose.yml"
    
    if (-not (Test-Path $composeFile)) {
        Write-Host "[ERROR] docker-compose.yml not found at: $composeFile" -ForegroundColor Red
        return $false
    }
    
    Write-Host "[INFO] Building Dev Dito images..." -ForegroundColor Cyan
    
    Push-Location (Join-Path $script:PROJECT_ROOT "backend_services")
    try {
        docker compose -p stack-g-devdito build 2>&1 | ForEach-Object {
            if ($_ -match "error|Error|ERROR") {
                Write-Host $_ -ForegroundColor Red
            }
            elseif ($_ -match "Successfully|CACHED") {
                Write-Host $_ -ForegroundColor Green
            }
            else {
                Write-Host $_ -ForegroundColor DarkGray
            }
        }
        
        if ($LASTEXITCODE -ne 0) {
            Write-Host "[ERROR] Build failed" -ForegroundColor Red
            return $false
        }
    }
    finally {
        Pop-Location
    }
    
    Write-Host "[OK] Images built successfully" -ForegroundColor Green
    return $true
}

function Step-Start {
    Write-Host ""
    Write-Host "=== Step 5: Start Services ===" -ForegroundColor Cyan
    
    Push-Location (Join-Path $script:PROJECT_ROOT "backend_services")
    try {
        Write-Host "[INFO] Starting stack-g-devdito services..." -ForegroundColor Cyan
        
        docker compose -p stack-g-devdito up -d 2>&1 | ForEach-Object {
            Write-Host $_ -ForegroundColor DarkGray
        }
        
        if ($LASTEXITCODE -ne 0) {
            Write-Host "[ERROR] Failed to start services" -ForegroundColor Red
            return $false
        }
    }
    finally {
        Pop-Location
    }
    
    Write-Host "[OK] Services started" -ForegroundColor Green
    return $true
}

function Step-DeployPlugin {
    Write-Host ""
    Write-Host "=== Step 6: Deploy DokuWiki Plugin ===" -ForegroundColor Cyan
    
    # Check if dev-dito-wiki container exists
    $wikiContainer = docker ps --format "{{.Names}}" | Where-Object { $_ -eq "dev-dito-wiki" }
    
    if (-not $wikiContainer) {
        Write-Host "[INFO] dev-dito-wiki container not found" -ForegroundColor Yellow
        Write-Host "[INFO] Plugin deployment will be available when wiki container is running" -ForegroundColor Yellow
        return $true
    }
    
    # Run deploy script
    $deployScript = Join-Path $script:PROJECT_ROOT "scripts\deploy-plugin.ps1"
    if (Test-Path $deployScript) {
        Write-Host "[INFO] Deploying plugin to DokuWiki..." -ForegroundColor Cyan
        & $deployScript
    }
    else {
        Write-Host "[WARN] Deploy script not found: $deployScript" -ForegroundColor Yellow
    }
    
    return $true
}

function Step-HealthCheck {
    Write-Host ""
    Write-Host "=== Step 7: Health Check ===" -ForegroundColor Cyan
    
    # Wait a moment for services to start
    Start-Sleep -Seconds 3
    
    # Check orchestrator
    Write-Host "[INFO] Checking orchestrator..." -ForegroundColor Cyan
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:8089/health" -TimeoutSec 5 -ErrorAction SilentlyContinue
        Write-Host "[OK] Orchestrator is healthy" -ForegroundColor Green
    }
    catch {
        Write-Host "[WARN] Orchestrator not responding (may still be starting)" -ForegroundColor Yellow
    }
    
    # List running containers
    Write-Host ""
    Write-Host "[INFO] Running Dev Dito containers:" -ForegroundColor Cyan
    $containers = docker ps --filter "name=dev-dito" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>&1
    Write-Host $containers -ForegroundColor White
    
    return $true
}

function Show-Success {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host " Installation Complete!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next Steps:" -ForegroundColor Cyan
    Write-Host "  1. Access DokuWiki: http://localhost:8080" -ForegroundColor White
    Write-Host "  2. Admin Panel: http://localhost:8080/?do=admin&page=devdito" -ForegroundColor White
    Write-Host "  3. Orchestrator API: http://localhost:8089" -ForegroundColor White
    Write-Host ""
    Write-Host "Useful Commands:" -ForegroundColor Cyan
    Write-Host "  docker compose -p stack-g-devdito ps       # Show status" -ForegroundColor DarkGray
    Write-Host "  docker compose -p stack-g-devdito logs -f  # View logs" -ForegroundColor DarkGray
    Write-Host "  docker compose -p stack-g-devdito down     # Stop services" -ForegroundColor DarkGray
    Write-Host ""
}

# =============================================================================
# Main Entry Point
# =============================================================================

function Main {
    if ($Help) {
        Show-Help
        return
    }
    
    Show-Banner
    
    # Step 1: Docker
    if (-not $SkipDocker) {
        if (-not (Step-Docker)) {
            Write-Host ""
            Write-Host "[ERROR] Installation aborted: Docker not available" -ForegroundColor Red
            exit 1
        }
    }
    
    # Step 2: Network
    if (-not $SkipNetwork) {
        if (-not (Step-Network)) {
            Write-Host ""
            Write-Host "[ERROR] Installation aborted: Network setup failed" -ForegroundColor Red
            exit 1
        }
    }
    
    # Step 3: Migration
    if (-not $SkipMigration) {
        if (-not (Step-Migration)) {
            Write-Host ""
            Write-Host "[ERROR] Installation aborted: Migration failed" -ForegroundColor Red
            exit 1
        }
    }
    
    # Step 4: Build
    if (-not $SkipBuild) {
        if (-not (Step-Build)) {
            Write-Host ""
            Write-Host "[ERROR] Installation aborted: Build failed" -ForegroundColor Red
            exit 1
        }
    }
    
    # Step 5: Start
    if (-not (Step-Start)) {
        Write-Host ""
        Write-Host "[ERROR] Installation aborted: Failed to start services" -ForegroundColor Red
        exit 1
    }
    
    # Step 6: Deploy Plugin
    Step-DeployPlugin | Out-Null
    
    # Step 7: Health Check
    Step-HealthCheck | Out-Null
    
    # Done!
    Show-Success
}

# Run main
Main
