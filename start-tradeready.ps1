$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$frontend = Join-Path $root "frontend\frontend design\2026-06-06\files-mentioned-by-the-user-tradeready\outputs\tradeready-executable"

$backendPort = 8000
$frontendPort = 4174
$envFile = Join-Path $root ".env"

$backendArgs = @(
  "-m", "uvicorn",
  "backend.tradeready.main:app",
  "--host", "127.0.0.1",
  "--port", "$backendPort",
  "--reload"
)

if (Test-Path $envFile) {
  $backendArgs += @("--env-file", $envFile)
  Write-Host "Loading backend environment from .env"
}

Write-Host "Starting TradeReady backend at http://127.0.0.1:$backendPort"
$backend = Start-Process -WindowStyle Hidden -FilePath python -ArgumentList $backendArgs -WorkingDirectory $root -PassThru

try {
  Start-Sleep -Seconds 3
  $health = Invoke-RestMethod -Uri "http://127.0.0.1:$backendPort/health" -TimeoutSec 5
  if ($health.status -ne "ok") {
    throw "Backend health check failed."
  }

  Write-Host "Backend ready."
  Write-Host "Starting TradeReady frontend at http://127.0.0.1:$frontendPort"
  Write-Host "Open http://127.0.0.1:$frontendPort in your browser."
  Write-Host "Press Ctrl+C to stop the frontend; the script will stop the backend."

  Set-Location $frontend
  python -m http.server $frontendPort --bind 127.0.0.1
}
finally {
  if ($backend -and -not $backend.HasExited) {
    Stop-Process -Id $backend.Id -Force -ErrorAction SilentlyContinue
  }
}
