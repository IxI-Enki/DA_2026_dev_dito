# Dev Dito - One Shot
# Dot-source profile snippet so dd-* aliases and DD_REPO_ROOT work when run standalone (e.g. from IDE)
if ($PSScriptRoot) {
    $snippet = Join-Path $PSScriptRoot 'dd_profile_snippet.ps1'
    if (Test-Path $snippet) { . $snippet }
}

Clear-Host

# Check:
#   - Health
      dd-health
#   - Status
      dd-status
      dd-sandbox-status

Write-Host "[OK] " -NoNewline -ForegroundColor Green
Write-Host "Checking in finished`n" -ForegroundColor DarkGreen

# Clean Restart:
#   - Shutdown
Write-Host "[INFO] " -NoNewline -ForegroundColor Cyan
Write-Host "...shutting down docker service-stacks [A-G]" -ForegroundColor DarkGray
      dd-down
      dd-sandbox-down
Write-Host "[OK] " -NoNewline -ForegroundColor Green
Write-Host "Docker service-stacks [A-G] shut down`n" -ForegroundColor DarkGreen

#   - Startup
Write-Host "[INFO] " -NoNewline -ForegroundColor Cyan
Write-Host "...starting docker service stacks [A-G]" -ForegroundColor DarkGray
      dd-up
      dd-sandbox-up
Write-Host "[OK] " -NoNewline -ForegroundColor Green
Write-Host "Docker service-stacks [A-G] started`n" -ForegroundColor DarkGreen

#-------------------------------------------------------------------------------------------------
# Wait until all four HTTP endpoints respond (or 90-second timeout).
# DokuWiki and Wiki Sandbox need ~15-25 s after container start before serving.
#-------------------------------------------------------------------------------------------------
$waitEndpoints = @(
    'http://localhost:18089/health',   # Orchestrator  (fast)
    'http://localhost:18334/healthz',  # Qdrant        (fast)
    'http://localhost:18080',          # DokuWiki      (slow)
    'http://localhost:8090'            # Wiki Sandbox  (slow)
)
$maxWaitSec   = 90
$pollInterval = 3
$deadline     = (Get-Date).AddSeconds($maxWaitSec)
$remaining    = [System.Collections.Generic.List[string]]$waitEndpoints

Write-Host "[INFO] Waiting for all services to become ready (timeout ${maxWaitSec}s)..." -ForegroundColor Cyan

while ($remaining.Count -gt 0 -and (Get-Date) -lt $deadline) {
    Start-Sleep -Seconds $pollInterval
    $stillWaiting = [System.Collections.Generic.List[string]]::new()
    foreach ($url in $remaining) {
        try {
            $null = Invoke-WebRequest -Uri $url -TimeoutSec 2 -ErrorAction Stop
            Write-Host "  [OK] $url" -ForegroundColor Green
        } catch {
            $stillWaiting.Add($url)
        }
    }
    $remaining = $stillWaiting
}

if ($remaining.Count -gt 0) {
    Write-Host "[WARN] The following endpoints did not respond within ${maxWaitSec}s:" -ForegroundColor Yellow
    $remaining | ForEach-Object { Write-Host "  [--] $_" -ForegroundColor Red }
} else {
    Write-Host "[OK] All services ready." -ForegroundColor Green
}
Write-Host ""
#-------------------------------------------------------------------------------------------------

# Re-Check:
#   - Health
      dd-health
#   - Status
      dd-status
      dd-sandbox-status

Write-Host "[OK] " -NoNewline -ForegroundColor Green
Write-Host "Checking in finished`n" -ForegroundColor DarkGreen

Write-Host "[INFO] " -NoNewline -ForegroundColor Cyan
Write-Host "...opening local wiki instance by alias: " -NoNewline -ForegroundColor DarkGray
Write-Host "'dd-sandbox-open'" -ForegroundColor DarkCyan
dd-sandbox-open
Write-Host "[OK] " -NoNewline -ForegroundColor Green
Write-Host "local wiki instance opened`n" -ForegroundColor DarkGreen

# Write-Host "[INFO] Sandboox wiki instance at: " -NoNewline -ForegroundColor Cyan
# Write-Host "http://localhost:18090" -ForegroundColor Blue

Write-Host "[INFO] " -NoNewline -ForegroundColor Cyan
Write-Host "...opening dev dito by alias:  " -NoNewline -ForegroundColor DarkGray
Write-Host  "'dd-admin'" -ForegroundColor DarkCyan
dd-admin
Write-Host "[OK] " -NoNewline -ForegroundColor Green
Write-Host "dev dito opened`n" -ForegroundColor DarkGreen

# Write-Host "[INFO] Dev dito admin panel at: " -NoNewline -ForegroundColor Cyan
# Write-Host "http://localhost:18080/?do=admin&page=devdito" -ForegroundColor Blue
