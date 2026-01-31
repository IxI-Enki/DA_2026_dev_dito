#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Deploy Dev Dito DokuWiki Plugin to local test wiki.

.DESCRIPTION
    Copies the plugin from dokuwiki_plugin/ to the target wiki's plugins_dev/devdito/ folder.
    Performs PHP syntax checks before deployment.

.PARAMETER TargetWiki
    Path to the target DokuWiki installation (default: standard dev wiki path).

.PARAMETER SkipSyntaxCheck
    Skip PHP syntax validation before deploy.

.PARAMETER Verbose
    Show detailed output.

.EXAMPLE
    .\deploy-plugin.ps1
    Deploy to default test wiki location.

.EXAMPLE
    .\deploy-plugin.ps1 -TargetWiki "C:\path\to\wiki"
    Deploy to custom wiki location.
#>

[CmdletBinding()]
param(
    [string]$TargetWiki = "D:\_Repositories\year_2025_26\SYP_2025_26\leonie\internal_leonidas\development\first_own_dokuwiki",
    [switch]$SkipSyntaxCheck,
    [switch]$Help
)

$ErrorActionPreference = 'Stop'

# Show help
if ($Help) {
    Get-Help $MyInvocation.MyCommand.Path -Detailed
    exit 0
}

# Configuration
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir
$SourceDir = Join-Path $RepoRoot "dokuwiki_plugin"
$TargetDir = Join-Path $TargetWiki "plugins_dev\devdito"

# Colors and formatting
function Write-Status {
    param([string]$Message, [string]$Type = "INFO")
    $prefix = switch ($Type) {
        "OK"    { "[OK]   " }
        "ERROR" { "[ERROR]" }
        "WARN"  { "[WARN] " }
        default { "[INFO] " }
    }
    Write-Host "$prefix $Message"
}

function Write-Header {
    param([string]$Title)
    Write-Host ""
    Write-Host ("=" * 60)
    Write-Host "  $Title"
    Write-Host ("=" * 60)
}

# Main deployment logic
Write-Header "Dev Dito Plugin Deployment"

# Validate source
if (-not (Test-Path $SourceDir)) {
    Write-Status "Source directory not found: $SourceDir" -Type "ERROR"
    exit 1
}

Write-Status "Source: $SourceDir"
Write-Status "Target: $TargetDir"

# Check required files
$requiredFiles = @(
    "plugin.info.txt",
    "action.php",
    "admin.php",
    "conf\default.php",
    "conf\metadata.php",
    "lib\ConfigLoader.php"
)

Write-Host ""
Write-Status "Checking required files..."

$missingFiles = @()
foreach ($file in $requiredFiles) {
    $filePath = Join-Path $SourceDir $file
    if (Test-Path $filePath) {
        Write-Status "  Found: $file" -Type "OK"
    } else {
        Write-Status "  Missing: $file" -Type "ERROR"
        $missingFiles += $file
    }
}

if ($missingFiles.Count -gt 0) {
    Write-Status "Missing required files. Aborting." -Type "ERROR"
    exit 1
}

# Generate settings.json from env.yaml (Constitution Article II-B)
Write-Host ""
Write-Status "Generating settings.json from central config..."

$configPy = Join-Path $RepoRoot "config.py"
$settingsJson = Join-Path $RepoRoot "config\settings.json"

if (Test-Path $configPy) {
    $result = python $configPy 2>&1
    if ($LASTEXITCODE -eq 0) {
        if (Test-Path $settingsJson) {
            Write-Status "  settings.json generated successfully" -Type "OK"
        } else {
            Write-Status "  settings.json not created (check env.yaml)" -Type "WARN"
        }
    } else {
        Write-Status "  Failed to generate settings.json: $result" -Type "WARN"
        Write-Status "  Plugin will use fallback config values" -Type "WARN"
    }
} else {
    Write-Status "  config.py not found at $configPy" -Type "WARN"
}

# PHP Syntax Check
if (-not $SkipSyntaxCheck) {
    Write-Host ""
    Write-Status "Running PHP syntax checks..."
    
    $phpFiles = Get-ChildItem -Path $SourceDir -Filter "*.php" -Recurse
    $syntaxErrors = @()
    
    foreach ($phpFile in $phpFiles) {
        $result = php -l $phpFile.FullName 2>&1
        if ($LASTEXITCODE -ne 0) {
            $syntaxErrors += $phpFile.Name
            Write-Status "  Syntax error: $($phpFile.Name)" -Type "ERROR"
        } else {
            Write-Status "  Valid: $($phpFile.Name)" -Type "OK"
        }
    }
    
    if ($syntaxErrors.Count -gt 0) {
        Write-Status "PHP syntax errors found. Fix before deploying." -Type "ERROR"
        exit 1
    }
}

# Check target wiki exists
if (-not (Test-Path $TargetWiki)) {
    Write-Status "Target wiki not found: $TargetWiki" -Type "WARN"
    Write-Status "Creating target directory anyway..."
}

# Create target directory
Write-Host ""
Write-Status "Deploying plugin..."

if (Test-Path $TargetDir) {
    Write-Status "  Removing old deployment..."
    Remove-Item -Path $TargetDir -Recurse -Force
}

# Create target directory
New-Item -ItemType Directory -Path $TargetDir -Force | Out-Null

# Copy files
$itemsToCopy = @(
    "plugin.info.txt",
    "action.php",
    "admin.php",
    "logo.png",
    "conf",
    "lang",
    "lib",
    "dist"
)

foreach ($item in $itemsToCopy) {
    $sourcePath = Join-Path $SourceDir $item
    $targetPath = Join-Path $TargetDir $item
    
    if (Test-Path $sourcePath) {
        if ((Get-Item $sourcePath).PSIsContainer) {
            Copy-Item -Path $sourcePath -Destination $targetPath -Recurse -Force
            $fileCount = (Get-ChildItem -Path $sourcePath -Recurse -File).Count
            Write-Status "  Copied: $item/ ($fileCount files)" -Type "OK"
        } else {
            Copy-Item -Path $sourcePath -Destination $targetPath -Force
            Write-Status "  Copied: $item" -Type "OK"
        }
    } else {
        Write-Status "  Skipped: $item (not found)" -Type "WARN"
    }
}

# Verify deployment
Write-Host ""
Write-Status "Verifying deployment..."

$deployedFiles = Get-ChildItem -Path $TargetDir -Recurse -File
$totalSize = ($deployedFiles | Measure-Object -Property Length -Sum).Sum

Write-Status "  Total files: $($deployedFiles.Count)" -Type "OK"
Write-Status "  Total size: $([math]::Round($totalSize / 1KB, 2)) KB" -Type "OK"

# Read version from plugin.info.txt
$pluginInfo = Get-Content (Join-Path $TargetDir "plugin.info.txt") -Raw
if ($pluginInfo -match "version\s+(.+)") {
    $version = $matches[1].Trim()
    Write-Status "  Version: $version" -Type "OK"
}

# Copy settings.json to plugin's config directory
if (Test-Path $settingsJson) {
    # Create config/ directory inside the plugin
    $pluginConfigDir = Join-Path $TargetDir "config"
    if (-not (Test-Path $pluginConfigDir)) {
        New-Item -ItemType Directory -Path $pluginConfigDir -Force | Out-Null
    }
    Copy-Item -Path $settingsJson -Destination $pluginConfigDir -Force
    Write-Status "  Copied: settings.json to plugin/config/" -Type "OK"
}

# Summary
Write-Header "Deployment Complete"

Write-Host ""
Write-Host "  Plugin deployed to:"
Write-Host "  $TargetDir"
Write-Host ""
Write-Host "  Configuration:"
Write-Host "  - Central config: config/env.yaml (source)"
Write-Host "  - Generated:      config/settings.json (for PHP)"
Write-Host ""
Write-Host "  Next steps:"
Write-Host "  1. Start the wiki if not running:"
Write-Host "     cd `"$TargetWiki`""
Write-Host "     .\scripts\start.ps1"
Write-Host ""
Write-Host "  2. Open wiki in browser and log in as admin"
Write-Host ""
Write-Host "  3. Check Admin -> Dev Dito Core Setup"
Write-Host ""
Write-Host "  To change settings:"
Write-Host "  - Edit config/env.yaml, then run: python config.py"
Write-Host "  - Re-deploy: .\scripts\deploy-plugin.ps1"
Write-Host ""

exit 0
