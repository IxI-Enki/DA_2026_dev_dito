# =============================================================================
# Migration - Dev Dito Installation Helper
# =============================================================================
# Functions for detecting and migrating existing Dev Dito setups
# =============================================================================

$ErrorActionPreference = "Stop"

function Find-ExistingDevDitoSetup {
    <#
    .SYNOPSIS
        Search for existing Dev Dito installations
    .OUTPUTS
        Hashtable with setup info or $null
    #>
    $setups = @()
    
    # Check for running containers with Dev Dito naming patterns
    $patterns = @(
        "devdito_*",
        "dev-dito-*",
        "dev_dito_*",
        "*devdito*"
    )
    
    try {
        $allContainers = docker ps -a --format "{{.Names}}" 2>&1
        
        foreach ($pattern in $patterns) {
            $foundContainers = $allContainers | Where-Object { $_ -like $pattern }
            foreach ($match in $foundContainers) {
                $setups += @{
                    Container = $match
                    Pattern = $pattern
                }
            }
        }
    }
    catch {
        Write-Host "[WARN] Could not check for existing containers: $_" -ForegroundColor Yellow
    }
    
    # Check for existing volumes
    try {
        $volumes = docker volume ls --format "{{.Name}}" 2>&1
        $devditoVolumes = $volumes | Where-Object { $_ -match "devdito|dev.dito" }
        
        foreach ($vol in $devditoVolumes) {
            $setups += @{
                Volume = $vol
                Type = "volume"
            }
        }
    }
    catch {
        Write-Host "[WARN] Could not check for existing volumes: $_" -ForegroundColor Yellow
    }
    
    # Check for legacy network
    try {
        $networks = docker network ls --format "{{.Name}}" 2>&1
        $legacyNetworks = $networks | Where-Object { 
            $_ -match "devdito" -and $_ -ne "htl-wiki-network" 
        }
        
        foreach ($net in $legacyNetworks) {
            $setups += @{
                Network = $net
                Type = "network"
            }
        }
    }
    catch {
        Write-Host "[WARN] Could not check for existing networks: $_" -ForegroundColor Yellow
    }
    
    if ($setups.Count -eq 0) {
        return $null
    }
    
    return $setups
}

function Get-SetupVersion {
    <#
    .SYNOPSIS
        Determine the version/type of an existing setup
    .PARAMETER SetupInfo
        Setup info from Find-ExistingDevDitoSetup
    .OUTPUTS
        String - Version identifier
    #>
    param(
        [Parameter(Mandatory)]
        [array]$SetupInfo
    )
    
    # Check naming patterns to determine version
    $hasNewNaming = $SetupInfo | Where-Object { $_.Container -like "dev-dito-*" }
    $hasOldNaming = $SetupInfo | Where-Object { $_.Container -like "devdito_*" }
    $hasLegacyNetwork = $SetupInfo | Where-Object { $_.Network -eq "devdito_network" }
    
    if ($hasNewNaming -and -not $hasOldNaming -and -not $hasLegacyNetwork) {
        return "current"
    }
    elseif ($hasOldNaming -or $hasLegacyNetwork) {
        return "legacy"
    }
    else {
        return "unknown"
    }
}

function Backup-ExistingData {
    <#
    .SYNOPSIS
        Backup data from existing Dev Dito setup
    .PARAMETER BackupPath
        Path to store backup
    .OUTPUTS
        Boolean - True if backup successful
    #>
    param(
        [string]$BackupPath = ".\backup"
    )
    
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $backupDir = Join-Path $BackupPath "devdito_backup_$timestamp"
    
    Write-Host "[INFO] Creating backup at: $backupDir" -ForegroundColor Cyan
    
    try {
        New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
        
        # Backup data directory if exists
        $dataDir = ".\data"
        if (Test-Path $dataDir) {
            Write-Host "[INFO] Backing up data directory..." -ForegroundColor Cyan
            Copy-Item -Path $dataDir -Destination "$backupDir\data" -Recurse -Force
        }
        
        # Backup config directory if exists
        $configDir = ".\config"
        if (Test-Path $configDir) {
            Write-Host "[INFO] Backing up config directory..." -ForegroundColor Cyan
            Copy-Item -Path $configDir -Destination "$backupDir\config" -Recurse -Force
        }
        
        Write-Host "[OK] Backup created successfully" -ForegroundColor Green
        return $true
    }
    catch {
        Write-Host "[ERROR] Backup failed: $_" -ForegroundColor Red
        return $false
    }
}

function Remove-LegacyContainers {
    <#
    .SYNOPSIS
        Remove legacy Dev Dito containers
    .PARAMETER Force
        Skip confirmation prompt
    .OUTPUTS
        Boolean - True if removal successful
    #>
    param(
        [switch]$Force
    )
    
    $legacyPatterns = @("devdito_*", "dev_dito_*")
    $containersToRemove = @()
    
    try {
        $allContainers = docker ps -a --format "{{.Names}}" 2>&1
        
        foreach ($pattern in $legacyPatterns) {
            $foundContainers = $allContainers | Where-Object { $_ -like $pattern }
            $containersToRemove += $foundContainers
        }
    }
    catch {
        Write-Host "[ERROR] Could not list containers: $_" -ForegroundColor Red
        return $false
    }
    
    if ($containersToRemove.Count -eq 0) {
        Write-Host "[INFO] No legacy containers to remove" -ForegroundColor Cyan
        return $true
    }
    
    Write-Host "[INFO] Legacy containers found:" -ForegroundColor Yellow
    foreach ($c in $containersToRemove) {
        Write-Host "  - $c" -ForegroundColor White
    }
    
    if (-not $Force) {
        $confirm = Read-Host "Remove these containers? (y/N)"
        if ($confirm -ne "y" -and $confirm -ne "Y") {
            Write-Host "[INFO] Skipping container removal" -ForegroundColor Yellow
            return $true
        }
    }
    
    foreach ($container in $containersToRemove) {
        Write-Host "[INFO] Removing $container..." -ForegroundColor Cyan
        docker rm -f $container 2>&1 | Out-Null
    }
    
    Write-Host "[OK] Legacy containers removed" -ForegroundColor Green
    return $true
}

function Update-ToCurrentStructure {
    <#
    .SYNOPSIS
        Full migration workflow from legacy to current structure
    .OUTPUTS
        Boolean - True if migration successful
    #>
    
    Write-Host ""
    Write-Host "=== Migration to Current Structure ===" -ForegroundColor Cyan
    
    # Step 1: Backup
    Write-Host ""
    Write-Host "[Step 1/4] Creating backup..." -ForegroundColor Cyan
    if (-not (Backup-ExistingData)) {
        Write-Host "[ERROR] Backup failed, aborting migration" -ForegroundColor Red
        return $false
    }
    
    # Step 2: Stop legacy containers
    Write-Host ""
    Write-Host "[Step 2/4] Stopping legacy containers..." -ForegroundColor Cyan
    docker stop $(docker ps -q --filter "name=devdito_") 2>&1 | Out-Null
    docker stop $(docker ps -q --filter "name=dev_dito_") 2>&1 | Out-Null
    
    # Step 3: Remove legacy containers
    Write-Host ""
    Write-Host "[Step 3/4] Removing legacy containers..." -ForegroundColor Cyan
    if (-not (Remove-LegacyContainers -Force)) {
        Write-Host "[WARN] Some containers could not be removed" -ForegroundColor Yellow
    }
    
    # Step 4: Remove legacy network
    Write-Host ""
    Write-Host "[Step 4/4] Removing legacy network..." -ForegroundColor Cyan
    docker network rm devdito_network 2>&1 | Out-Null
    
    Write-Host ""
    Write-Host "[OK] Migration complete" -ForegroundColor Green
    return $true
}

function Show-MigrationStatus {
    <#
    .SYNOPSIS
        Display migration status and recommendations
    #>
    $existingSetup = Find-ExistingDevDitoSetup
    
    Write-Host ""
    Write-Host "=== Existing Setup Detection ===" -ForegroundColor Cyan
    
    if (-not $existingSetup) {
        Write-Host "[INFO] No existing Dev Dito setup found" -ForegroundColor Green
        Write-Host "[INFO] Fresh installation will be performed" -ForegroundColor Cyan
        return "fresh"
    }
    
    $version = Get-SetupVersion -SetupInfo $existingSetup
    
    Write-Host "[INFO] Existing setup detected (version: $version)" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Found components:" -ForegroundColor Cyan
    
    foreach ($item in $existingSetup) {
        if ($item.Container) {
            Write-Host "  [Container] $($item.Container)" -ForegroundColor White
        }
        if ($item.Volume) {
            Write-Host "  [Volume] $($item.Volume)" -ForegroundColor White
        }
        if ($item.Network) {
            Write-Host "  [Network] $($item.Network)" -ForegroundColor White
        }
    }
    
    Write-Host ""
    
    switch ($version) {
        "current" {
            Write-Host "[OK] Setup is already current" -ForegroundColor Green
            return "current"
        }
        "legacy" {
            Write-Host "[WARN] Legacy setup needs migration" -ForegroundColor Yellow
            return "migrate"
        }
        default {
            Write-Host "[WARN] Unknown setup version, manual review recommended" -ForegroundColor Yellow
            return "unknown"
        }
    }
}

# Export functions
Export-ModuleMember -Function @(
    'Find-ExistingDevDitoSetup',
    'Get-SetupVersion',
    'Backup-ExistingData',
    'Remove-LegacyContainers',
    'Update-ToCurrentStructure',
    'Show-MigrationStatus'
)
