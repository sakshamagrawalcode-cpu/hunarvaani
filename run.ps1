# Start HunarVaani:  .\run.ps1            (uses .env: real models after install.ps1)
#                    .\run.ps1 -Fake      (no models: test the screens only)
#                    .\run.ps1 -Port 8010 (pick a port yourself)
param([switch]$Real, [switch]$Fake, [int]$Port = 8000)
Set-Location -LiteralPath $PSScriptRoot
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "Not installed yet: double-click INSTALL.bat first." -ForegroundColor Red; exit 1
}
if ($Real) { $env:HV_MODELS = "real" }
if ($Fake) { $env:HV_MODELS = "fake" }
$mode = $env:HV_MODELS
if (-not $mode -and (Test-Path ".env")) {
    $line = Select-String -Path ".env" -Pattern "^\s*HV_MODELS\s*=\s*(\w+)" | Select-Object -First 1
    if ($line) { $mode = $line.Matches[0].Groups[1].Value }
}
if ($mode -eq "real") {
    $up = $false
    try { Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 3 | Out-Null; $up = $true } catch { }
    if (-not $up) {
        $exe = "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe"
        if (Get-Command ollama -ErrorAction SilentlyContinue) { $exe = (Get-Command ollama).Source }
        if (Test-Path $exe) {
            Write-Host "Starting Ollama (the LLM) ..."
            Start-Process -FilePath $exe -ArgumentList "serve" -WindowStyle Hidden
            Start-Sleep -Seconds 4
        } else { Write-Host "Ollama not found: run INSTALL.bat" -ForegroundColor Yellow }
    }
}
# If the port is taken (another server, Docker), use the next free one.
while (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) {
    Write-Host "Port $Port is busy, trying $($Port + 1)"
    $Port++
}
Write-Host ""
Write-Host "HunarVaani ($mode models)" -ForegroundColor Green
Write-Host "Kiosk:   http://localhost:$Port/kiosk"
Write-Host "Officer: http://localhost:$Port/officer   (user and password in .env)"
Write-Host "Wait for 'models warmed up' below before the first test (about a minute). Stop with Ctrl+C."
Write-Host ""
.\.venv\Scripts\python.exe -m uvicorn hv.server:app --host 0.0.0.0 --port $Port
