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

$pythonExe = if (Test-Path (Join-Path $root "venv\Scripts\python.exe")) {
  Join-Path $root "venv\Scripts\python.exe"
} elseif (Test-Path (Join-Path $root ".venv\Scripts\python.exe")) {
  Join-Path $root ".venv\Scripts\python.exe"
} else {
  "python"
}

$logOut = Join-Path $root "backend.out.log"
$logErr = Join-Path $root "backend.err.log"

function Join-ProcessArguments {
  param([string[]]$Arguments)

  return ($Arguments | ForEach-Object {
    if ($_ -match '[\s"]') {
      '"' + ($_ -replace '"', '\"') + '"'
    } else {
      $_
    }
  }) -join " "
}

$backendArgumentList = Join-ProcessArguments $backendArgs

Write-Host "Starting TradeReady backend at http://127.0.0.1:$backendPort"
$backend = Start-Process -FilePath $pythonExe -ArgumentList $backendArgumentList -WorkingDirectory $root -PassThru `
  -RedirectStandardOutput $logOut -RedirectStandardError $logErr -WindowStyle Hidden

try {
  $waited = 0
  Write-Host "Waiting for backend..." -NoNewline
  while ($waited -lt 15) {
    Start-Sleep -Seconds 1
    $waited++
    Write-Host "." -NoNewline
    try {
      $health = Invoke-RestMethod -Uri "http://127.0.0.1:$backendPort/health" -TimeoutSec 2 -ErrorAction Stop
      if ($health.status -eq "ok") { break }
    } catch { }
  }
  Write-Host ""
  if ($waited -ge 15) {
    Write-Host "Backend log:" -ForegroundColor Red
    Get-Content $logOut -ErrorAction SilentlyContinue
    Get-Content $logErr -ErrorAction SilentlyContinue
    throw "Backend did not start within 15 seconds."
  }

  Write-Host "Backend ready."
  Write-Host "Starting TradeReady frontend at http://127.0.0.1:$frontendPort"
  Write-Host "Open http://127.0.0.1:$frontendPort in your browser."
  Write-Host "Press Ctrl+C to stop the frontend; the script will stop the backend."

  Set-Location $frontend
  & $pythonExe -m http.server $frontendPort --bind 127.0.0.1
}
finally {
  if ($backend -and -not $backend.HasExited) {
    Stop-Process -Id $backend.Id -Force -ErrorAction SilentlyContinue
  }
}
