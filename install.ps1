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
    [switch]$SkipEnv,
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
    Write-Host "  -SkipEnv         Skip .env file setup"
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
    return $networks -contains "leonidas-network"
}

function New-HtlWikiNetwork {
    if (Test-NetworkExists) {
        Write-Host "[OK] Network 'leonidas-network' already exists" -ForegroundColor Green
        return $true
    }
    
    Write-Host "[INFO] Creating network 'leonidas-network'..." -ForegroundColor Cyan
    docker network create --driver bridge --attachable leonidas-network 2>&1 | Out-Null
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
    $containers = docker network inspect leonidas-network --format '{{range .Containers}}{{.Name}} {{end}}' 2>&1
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

function Step-Env {
    Write-Host ""
    Write-Host "=== Step 4: Environment Configuration ===" -ForegroundColor Cyan

    $envFile = Join-Path $script:PROJECT_ROOT "backend_services\.env"
    $envTemplate = Join-Path $script:PROJECT_ROOT "backend_services\.env.template"

    if (Test-Path $envFile) {
        Write-Host "[OK] .env file already exists" -ForegroundColor Green

        # Check if WIKI_ROOT is set
        $content = Get-Content $envFile -Raw
        if ($content -match 'WIKI_ROOT=(.+)' -and $Matches[1].Trim() -ne '') {
            $wikiRoot = $Matches[1].Trim()
            if (Test-Path $wikiRoot) {
                Write-Host "[OK] WIKI_ROOT=$wikiRoot (valid)" -ForegroundColor Green
            }
            else {
                Write-Host "[WARN] WIKI_ROOT=$wikiRoot (path not found)" -ForegroundColor Yellow
            }
        }
        else {
            Write-Host "[WARN] WIKI_ROOT not configured in .env" -ForegroundColor Yellow
            Write-Host "       DokuWiki will be started from leonidas stacks or manually." -ForegroundColor DarkGray
        }
        return $true
    }

    if (-not (Test-Path $envTemplate)) {
        Write-Host "[WARN] No .env.template found. Skipping .env setup." -ForegroundColor Yellow
        return $true
    }

    Write-Host "[INFO] Creating .env from template..." -ForegroundColor Cyan

    # Copy template
    Copy-Item $envTemplate $envFile

    # Try to detect DokuWiki installation automatically
    $leonidasWiki = Join-Path (Split-Path -Parent (Split-Path -Parent $script:PROJECT_ROOT)) `
        "year_2025_26\SYP_2025_26\leonie\internal_leonidas\development\first_own_dokuwiki"

    if (Test-Path $leonidasWiki) {
        Write-Host "[INFO] Detected DokuWiki at: $leonidasWiki" -ForegroundColor Cyan

        if (-not $Force) {
            $confirm = Read-Host "Use this path for WIKI_ROOT? (Y/n)"
            if ($confirm -eq 'n' -or $confirm -eq 'N') {
                $leonidasWiki = Read-Host "Enter WIKI_ROOT path"
            }
        }

        if ($leonidasWiki -and (Test-Path $leonidasWiki)) {
            # Update .env file
            $envContent = Get-Content $envFile -Raw
            $envContent = $envContent -replace 'WIKI_ROOT=', "WIKI_ROOT=$leonidasWiki"
            Set-Content -Path $envFile -Value $envContent -Encoding utf8NoBOM
            Write-Host "[OK] WIKI_ROOT set to: $leonidasWiki" -ForegroundColor Green
        }
    }
    else {
        Write-Host "[INFO] No DokuWiki auto-detected." -ForegroundColor Yellow
        Write-Host "       Edit backend_services/.env to set WIKI_ROOT manually." -ForegroundColor DarkGray
    }

    Write-Host "[OK] .env file created" -ForegroundColor Green
    return $true
}

function Step-Build {
    Write-Host ""
    Write-Host "=== Step 5: Build Docker Images ===" -ForegroundColor Cyan
    
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
    Write-Host "=== Step 6: Start Services ===" -ForegroundColor Cyan

    # Start core services (orchestrator + qdrant)
    Push-Location (Join-Path $script:PROJECT_ROOT "backend_services")
    try {
        Write-Host "[INFO] Starting stack-g-devdito core services..." -ForegroundColor Cyan

        docker compose -p stack-g-devdito up -d 2>&1 | ForEach-Object {
            Write-Host $_ -ForegroundColor DarkGray
        }

        if ($LASTEXITCODE -ne 0) {
            Write-Host "[ERROR] Failed to start core services" -ForegroundColor Red
            return $false
        }
        Write-Host "[OK] Core services started (orchestrator, qdrant)" -ForegroundColor Green
    }
    finally {
        Pop-Location
    }

    # Start DokuWiki (A+C hybrid logic)
    Write-Host ""
    $wikiRunning = docker ps --filter "name=dev-dito-wiki" --format "{{.Names}}" 2>$null
    if ($wikiRunning) {
        Write-Host "[OK] DokuWiki already running" -ForegroundColor Green
    }
    else {
        $wikiStarted = $false

        # Strategy C: leonidas stacks compose
        $leonidasCompose = Join-Path (Split-Path -Parent (Split-Path -Parent $script:PROJECT_ROOT)) `
            "year_2025_26\SYP_2025_26\leonie\internal_leonidas\stacks\stack-g-devdito\docker-compose.yml"
        if (Test-Path $leonidasCompose) {
            $leonidasDir = Split-Path -Parent $leonidasCompose
            Write-Host "[INFO] Starting DokuWiki from leonidas stacks..." -ForegroundColor Cyan
            Push-Location $leonidasDir
            try {
                docker compose -p stack-g-devdito up -d 2>$null
                $check = docker ps --filter "name=dev-dito-wiki" --format "{{.Names}}" 2>$null
                if ($check) {
                    $wikiStarted = $true
                    Write-Host "[OK] DokuWiki started (leonidas stacks)" -ForegroundColor Green
                }
            }
            finally {
                Pop-Location
            }
        }

        # Strategy A: .env + wiki profile
        if (-not $wikiStarted) {
            $envFile = Join-Path $script:PROJECT_ROOT "backend_services\.env"
            if (Test-Path $envFile) {
                $envContent = Get-Content $envFile -Raw
                if ($envContent -match 'WIKI_ROOT=(.+)' -and $Matches[1].Trim() -ne '') {
                    $wikiRoot = $Matches[1].Trim()
                    if (Test-Path $wikiRoot) {
                        Write-Host "[INFO] Starting DokuWiki via .env (WIKI_ROOT=$wikiRoot)..." -ForegroundColor Cyan
                        Push-Location (Join-Path $script:PROJECT_ROOT "backend_services")
                        try {
                            docker compose -p stack-g-devdito --profile wiki up -d 2>$null
                            $check = docker ps --filter "name=dev-dito-wiki" --format "{{.Names}}" 2>$null
                            if ($check) {
                                $wikiStarted = $true
                                Write-Host "[OK] DokuWiki started (.env profile)" -ForegroundColor Green
                            }
                        }
                        finally {
                            Pop-Location
                        }
                    }
                }
            }
        }

        # Fallback: start existing stopped container
        if (-not $wikiStarted) {
            $existing = docker ps -a --filter "name=dev-dito-wiki" --format "{{.Names}}" 2>$null
            if ($existing) {
                Write-Host "[INFO] Starting existing dev-dito-wiki container..." -ForegroundColor Cyan
                docker start dev-dito-wiki 2>$null | Out-Null
                $check = docker ps --filter "name=dev-dito-wiki" --format "{{.Names}}" 2>$null
                if ($check) {
                    $wikiStarted = $true
                    Write-Host "[OK] DokuWiki started (existing container)" -ForegroundColor Green
                }
            }
        }

        if (-not $wikiStarted) {
            Write-Host "[WARN] DokuWiki not started. Set WIKI_ROOT in backend_services/.env" -ForegroundColor Yellow
        }
    }

    Write-Host "[OK] Services started" -ForegroundColor Green
    return $true
}

function Step-DeployPlugin {
    Write-Host ""
    Write-Host "=== Step 7: Deploy DokuWiki Plugin ===" -ForegroundColor Cyan
    
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
    Write-Host "=== Step 8: Health Check ===" -ForegroundColor Cyan

    # Wait for services to initialize
    Start-Sleep -Seconds 5

    $endpoints = @(
        @{ Name = 'Orchestrator';  Url = 'http://localhost:18089/health' },
        @{ Name = 'DokuWiki';      Url = 'http://localhost:18080' },
        @{ Name = 'Qdrant';        Url = 'http://localhost:18334/healthz' }
    )

    foreach ($ep in $endpoints) {
        try {
            $null = Invoke-WebRequest -Uri $ep.Url -TimeoutSec 5 -ErrorAction Stop
            Write-Host ("[OK] {0,-16} {1}" -f $ep.Name, $ep.Url) -ForegroundColor Green
        }
        catch {
            Write-Host ("[--] {0,-16} {1}" -f $ep.Name, $ep.Url) -ForegroundColor Yellow
        }
    }

    # List running containers
    Write-Host ""
    Write-Host "[INFO] Running Dev Dito containers:" -ForegroundColor Cyan
    $containers = docker ps --filter "name=dev-dito" --format "  {{.Names}}`t{{.Status}}" 2>&1
    if ($containers -is [array]) {
        foreach ($line in $containers) { Write-Host $line -ForegroundColor White }
    }
    elseif ($containers) {
        Write-Host $containers -ForegroundColor White
    }

    return $true
}

function Show-Success {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host " Installation Complete!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Access Points:" -ForegroundColor Cyan
    Write-Host "  DokuWiki:     http://localhost:18080" -ForegroundColor White
    Write-Host "  Admin Panel:  http://localhost:18080/?do=admin&page=devdito" -ForegroundColor White
    Write-Host "  Orchestrator: http://localhost:18089" -ForegroundColor White
    Write-Host "  Qdrant:       http://localhost:18334" -ForegroundColor White
    Write-Host ""
    Write-Host "Quick Commands (dd alias):" -ForegroundColor Cyan
    Write-Host "  dd-status     Show comprehensive status" -ForegroundColor DarkGray
    Write-Host "  dd-logs       View orchestrator logs" -ForegroundColor DarkGray
    Write-Host "  dd-health     Check all service endpoints" -ForegroundColor DarkGray
    Write-Host "  dd-open       Open DokuWiki in browser" -ForegroundColor DarkGray
    Write-Host "  dd -Help      Full command reference" -ForegroundColor DarkGray
    Write-Host ""
    Write-Host "Profile Setup:" -ForegroundColor Cyan
    Write-Host "  Add this to your `$PROFILE to enable the 'dd' alias:" -ForegroundColor DarkGray
    Write-Host "  . `"$script:PROJECT_ROOT\scripts\dd_profile_snippet.ps1`"" -ForegroundColor White
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

    # Step 4: Environment (.env)
    if (-not $SkipEnv) {
        if (-not (Step-Env)) {
            Write-Host ""
            Write-Host "[WARN] Environment setup had issues - continuing" -ForegroundColor Yellow
        }
    }

    # Step 5: Build
    if (-not $SkipBuild) {
        if (-not (Step-Build)) {
            Write-Host ""
            Write-Host "[ERROR] Installation aborted: Build failed" -ForegroundColor Red
            exit 1
        }
    }

    # Step 6: Start
    if (-not (Step-Start)) {
        Write-Host ""
        Write-Host "[ERROR] Installation aborted: Failed to start services" -ForegroundColor Red
        exit 1
    }
    
    # Step 7: Deploy Plugin
    Step-DeployPlugin | Out-Null

    # Step 8: Health Check
    Step-HealthCheck | Out-Null
    
    # Done!
    Show-Success
}

# Run main
Main
