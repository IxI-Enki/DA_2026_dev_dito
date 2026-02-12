# =============================================================================
# Network Setup - Dev Dito Installation Helper
# =============================================================================
# Functions for Docker network management
# =============================================================================

$ErrorActionPreference = "Stop"

$script:NETWORK_NAME = "leonidas-network"

function Test-NetworkExists {
    <#
    .SYNOPSIS
        Check if the HTL Wiki network exists
    .OUTPUTS
        Boolean - True if network exists
    #>
    try {
        $networks = docker network ls --format "{{.Name}}" 2>&1
        return $networks -contains $script:NETWORK_NAME
    }
    catch {
        return $false
    }
}

function New-HtlWikiNetwork {
    <#
    .SYNOPSIS
        Create the HTL Wiki shared network
    .OUTPUTS
        Boolean - True if created successfully
    #>
    if (Test-NetworkExists) {
        Write-Host "[OK] Network '$script:NETWORK_NAME' already exists" -ForegroundColor Green
        return $true
    }
    
    Write-Host "[INFO] Creating network '$script:NETWORK_NAME'..." -ForegroundColor Cyan
    
    try {
        docker network create `
            --driver bridge `
            --attachable `
            $script:NETWORK_NAME 2>&1 | Out-Null
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "[OK] Network created successfully" -ForegroundColor Green
            return $true
        }
    }
    catch {
        Write-Host "[ERROR] Failed to create network: $_" -ForegroundColor Red
    }
    
    return $false
}

function Get-ConnectedStacks {
    <#
    .SYNOPSIS
        Get list of stacks/containers connected to the HTL Wiki network
    .OUTPUTS
        Array of container names
    #>
    if (-not (Test-NetworkExists)) {
        return @()
    }
    
    try {
        $containers = docker network inspect $script:NETWORK_NAME `
            --format '{{range .Containers}}{{.Name}} {{end}}' 2>&1
        
        if ($LASTEXITCODE -eq 0 -and $containers) {
            return ($containers -split '\s+' | Where-Object { $_ })
        }
    }
    catch {
        Write-Host "[WARN] Could not inspect network: $_" -ForegroundColor Yellow
    }
    
    return @()
}

function Show-NetworkStatus {
    <#
    .SYNOPSIS
        Display the current network status and connected containers
    #>
    Write-Host ""
    Write-Host "=== Network Status ===" -ForegroundColor Cyan
    
    if (-not (Test-NetworkExists)) {
        Write-Host "[INFO] Network '$script:NETWORK_NAME' does not exist" -ForegroundColor Yellow
        return
    }
    
    Write-Host "[OK] Network '$script:NETWORK_NAME' exists" -ForegroundColor Green
    
    $containers = Get-ConnectedStacks
    if ($containers.Count -eq 0) {
        Write-Host "[INFO] No containers connected" -ForegroundColor Yellow
    }
    else {
        Write-Host "[INFO] Connected containers:" -ForegroundColor Cyan
        foreach ($container in $containers) {
            # Determine stack based on naming convention
            $stack = switch -Regex ($container) {
                "^wiki-sandbox"          { "stack-a-wiki-sandbox" }
                "^keycloak"              { "stack-b-wiki-core" }
                "^qdrant"                { "stack-d-ai-core" }
                "^dev-dito"              { "stack-g-devdito" }
                "^semantic-search"       { "stack-h-mcp" }
                default                  { "unknown" }
            }
            Write-Host "  - $container ($stack)" -ForegroundColor White
        }
    }
    Write-Host ""
}

function Get-ExpectedStacks {
    <#
    .SYNOPSIS
        Get list of expected stacks in the HTL Wiki ecosystem
    .OUTPUTS
        Hashtable of stack info
    #>
    return @{
# >>> Expected Stacks >>>

        'stack-a-wiki-sandbox' = @{
            Description = 'Plain DokuWiki sandbox instance'
            Required = $false
            Containers = @('wiki-sandbox')
        }

        'stack-b-wiki-core' = @{
            Description = 'Core wiki services (Keycloak)'
            Required = $false
            Containers = @('keycloak-server')
        }

        'stack-d-ai-core' = @{
            Description = 'AI infrastructure (Qdrant)'
            Required = $true
            Containers = @('qdrant-main-vector-db')
        }

        'stack-g-devdito' = @{
            Description = 'Dev Dito services'
            Required = $true
            Containers = @('dev-dito-wiki', 'dev-dito-orchestrator')
        }

        'stack-h-mcp' = @{
            Description = 'MCP servers (Semantic Search)'
            Required = $false
            Containers = @('semantic-search-wiki-core')
        }
# <<< Expected Stacks <<<
    }
}

function Invoke-NetworkSetup {
    <#
    .SYNOPSIS
        Full network setup workflow
    .OUTPUTS
        Boolean - True if network is ready
    #>
    Write-Host ""
    Write-Host "=== Network Setup ===" -ForegroundColor Cyan
    
    if (-not (New-HtlWikiNetwork)) {
        return $false
    }
    
    Show-NetworkStatus
    return $true
}

# Export functions
Export-ModuleMember -Function @(
    'Test-NetworkExists',
    'New-HtlWikiNetwork',
    'Get-ConnectedStacks',
    'Show-NetworkStatus',
    'Get-ExpectedStacks',
    'Invoke-NetworkSetup'
)
