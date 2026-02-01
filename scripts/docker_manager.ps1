# =============================================================================
# Docker Manager - Dev Dito Installation Helper
# =============================================================================
# Functions for Docker Desktop detection, startup, and management
# =============================================================================

$ErrorActionPreference = "Stop"

function Test-DockerInstalled {
    <#
    .SYNOPSIS
        Check if Docker is installed on the system
    .OUTPUTS
        Boolean - True if Docker is installed
    #>
    try {
        $dockerPath = Get-Command docker -ErrorAction SilentlyContinue
        return $null -ne $dockerPath
    }
    catch {
        return $false
    }
}

function Test-DockerRunning {
    <#
    .SYNOPSIS
        Check if Docker daemon is running
    .OUTPUTS
        Boolean - True if Docker is running
    #>
    try {
        $result = docker info 2>&1
        return $LASTEXITCODE -eq 0
    }
    catch {
        return $false
    }
}

function Get-DockerDesktopPath {
    <#
    .SYNOPSIS
        Get the path to Docker Desktop executable
    .OUTPUTS
        String - Path to Docker Desktop or $null
    #>
    $paths = @(
        "$env:ProgramFiles\Docker\Docker\Docker Desktop.exe",
        "$env:LOCALAPPDATA\Docker\Docker Desktop.exe",
        "${env:ProgramFiles(x86)}\Docker\Docker\Docker Desktop.exe"
    )
    
    foreach ($path in $paths) {
        if (Test-Path $path) {
            return $path
        }
    }
    return $null
}

function Start-DockerDesktop {
    <#
    .SYNOPSIS
        Start Docker Desktop application
    .OUTPUTS
        Boolean - True if started successfully
    #>
    $dockerDesktopPath = Get-DockerDesktopPath
    
    if (-not $dockerDesktopPath) {
        Write-Host "[ERROR] Docker Desktop not found" -ForegroundColor Red
        return $false
    }
    
    Write-Host "[INFO] Starting Docker Desktop..." -ForegroundColor Cyan
    Start-Process -FilePath $dockerDesktopPath -WindowStyle Minimized
    return $true
}

function Wait-ForDockerReady {
    <#
    .SYNOPSIS
        Wait for Docker daemon to be ready
    .PARAMETER TimeoutSeconds
        Maximum time to wait in seconds (default: 120)
    .OUTPUTS
        Boolean - True if Docker is ready
    #>
    param(
        [int]$TimeoutSeconds = 120
    )
    
    $startTime = Get-Date
    $endTime = $startTime.AddSeconds($TimeoutSeconds)
    
    Write-Host "[INFO] Waiting for Docker to be ready..." -ForegroundColor Cyan
    
    while ((Get-Date) -lt $endTime) {
        if (Test-DockerRunning) {
            Write-Host "[OK] Docker is ready" -ForegroundColor Green
            return $true
        }
        
        $elapsed = [int]((Get-Date) - $startTime).TotalSeconds
        Write-Host "`r[INFO] Waiting... ($elapsed/$TimeoutSeconds seconds)" -NoNewline
        Start-Sleep -Seconds 2
    }
    
    Write-Host ""
    Write-Host "[ERROR] Docker did not start within $TimeoutSeconds seconds" -ForegroundColor Red
    return $false
}

function Get-DockerDownloadUrl {
    <#
    .SYNOPSIS
        Get the Docker Desktop download URL for Windows
    .OUTPUTS
        String - Download URL
    #>
    return "https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe"
}

function Show-DockerInstallInstructions {
    <#
    .SYNOPSIS
        Display Docker installation instructions
    #>
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Yellow
    Write-Host " Docker Desktop Installation Required" -ForegroundColor Yellow
    Write-Host "========================================" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Docker Desktop is required to run Dev Dito." -ForegroundColor White
    Write-Host ""
    Write-Host "Download from:" -ForegroundColor Cyan
    Write-Host "  $(Get-DockerDownloadUrl)" -ForegroundColor Green
    Write-Host ""
    Write-Host "Or install via winget:" -ForegroundColor Cyan
    Write-Host "  winget install Docker.DockerDesktop" -ForegroundColor Green
    Write-Host ""
    Write-Host "After installation:" -ForegroundColor Cyan
    Write-Host "  1. Start Docker Desktop" -ForegroundColor White
    Write-Host "  2. Wait for it to fully start (whale icon stable)" -ForegroundColor White
    Write-Host "  3. Run this installer again" -ForegroundColor White
    Write-Host ""
}

function Invoke-DockerCheck {
    <#
    .SYNOPSIS
        Full Docker check workflow - install, start, or verify
    .OUTPUTS
        Boolean - True if Docker is ready to use
    #>
    
    # Check if Docker is installed
    if (-not (Test-DockerInstalled)) {
        Show-DockerInstallInstructions
        return $false
    }
    
    Write-Host "[OK] Docker is installed" -ForegroundColor Green
    
    # Check if Docker is running
    if (Test-DockerRunning) {
        Write-Host "[OK] Docker is running" -ForegroundColor Green
        return $true
    }
    
    # Try to start Docker Desktop
    Write-Host "[INFO] Docker is not running" -ForegroundColor Yellow
    
    if (-not (Start-DockerDesktop)) {
        return $false
    }
    
    # Wait for Docker to be ready
    return Wait-ForDockerReady -TimeoutSeconds 120
}

# Export functions
Export-ModuleMember -Function @(
    'Test-DockerInstalled',
    'Test-DockerRunning',
    'Start-DockerDesktop',
    'Wait-ForDockerReady',
    'Get-DockerDownloadUrl',
    'Show-DockerInstallInstructions',
    'Invoke-DockerCheck'
)
