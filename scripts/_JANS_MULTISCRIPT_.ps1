# Dev Dito - One Shot

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
Start-Sleep -Seconds 2
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
Write-Host "[INFO] " -NoNewline -ForegroundColor Cyan
Write-Host "...might take a few seconds to open..." -ForegroundColor DarkGray
Start-Sleep -Seconds 5
dd-sandbox-open
Write-Host "[OK] " -NoNewline -ForegroundColor Green
Write-Host "local wiki instance opened`n" -ForegroundColor DarkGreen

# Write-Host "[INFO] Sandboox wiki instance at: " -NoNewline -ForegroundColor Cyan
# Write-Host "http://localhost:8090" -ForegroundColor Blue

Write-Host "[INFO] " -NoNewline -ForegroundColor Cyan
Write-Host "...opening dev dito by alias:  " -NoNewline -ForegroundColor DarkGray
Write-Host  "'dd-admin'" -ForegroundColor DarkCyan
Write-Host "[INFO] " -NoNewline -ForegroundColor Cyan
Write-Host "...might take a few seconds to open..." -ForegroundColor DarkGray
Start-Sleep -Seconds 5
dd-admin
Write-Host "[OK] " -NoNewline -ForegroundColor Green
Write-Host "dev dito opened`n" -ForegroundColor DarkGreen

# Write-Host "[INFO] Dev dito admin panel at: " -NoNewline -ForegroundColor Cyan
# Write-Host "http://localhost:8080/?do=admin&page=devdito" -ForegroundColor Blue
