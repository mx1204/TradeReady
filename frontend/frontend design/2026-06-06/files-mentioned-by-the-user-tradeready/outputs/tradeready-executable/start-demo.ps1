$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

$port = 4174

Write-Host "Starting TradeReady demo at http://127.0.0.1:$port"
python -m http.server $port --bind 127.0.0.1
