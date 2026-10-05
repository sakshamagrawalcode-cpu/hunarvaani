# HunarVaani: install EVERYTHING for the real prototype on Windows with an NVIDIA GPU.
#
#   Double-click INSTALL.bat   (or in PowerShell:  powershell -ExecutionPolicy Bypass -File .\install.ps1)
#
# What it does (safe to run again; finished steps are quick the second time):
#   1. Python 3.11, Git and Ollama (installed with winget if missing)
#   2. The server's Python environment (.venv) with speech-to-text (IndicConformer, ONNX Runtime)
#   3. Settings (.env): real models, an LLM that fits your GPU, a random officer password
#   4. Hugging Face login, for the two AI4Bharat models (you click "Agree" once on each page)
#   5. Downloads: IndicConformer (~2.5 GB) and the LLM in Ollama (~6 GB)
#   6. The voice: Indic Parler-TTS in its own environment (.venv-tts, CUDA 12.8 for RTX 50 cards),
#      renders every spoken line in Hindi, Marathi and English once (~30-60 min)
#   7. Checks every model and runs the tests
#
# Options:  -SkipVoices      skip step 6 (run it later with: .\install.ps1 -OnlyVoices)
#           -OnlyVoices      only step 6
#           -Langs hi        render only Hindi (default: hi,mr,en)
#           -Model gemma4:e2b-it-qat   choose the LLM yourself
param([switch]$SkipVoices, [switch]$OnlyVoices, [string[]]$Langs = @("hi", "mr", "en"), [string]$Model = "")
$LangList = ($Langs -join ",")

# "Continue": every step checks its own exit code (Windows PowerShell 5.1 can stop on harmless warnings otherwise)
$ErrorActionPreference = "Continue"
$ProgressPreference = "SilentlyContinue"
Set-Location -LiteralPath $PSScriptRoot
$env:HF_HUB_DISABLE_SYMLINKS_WARNING = "1"
$env:PYTHONUTF8 = "1"

function Say([string]$t) { Write-Host ""; Write-Host "==> $t" -ForegroundColor Cyan }
function Note([string]$t) { Write-Host "    $t" }
function Warn([string]$t) { Write-Host "    WARNING: $t" -ForegroundColor Yellow }
function Fail([string]$t) {
    Write-Host ""; Write-Host "STOPPED: $t" -ForegroundColor Red
    Write-Host "Fix this, then run the installer again (finished steps are skipped quickly)." -ForegroundColor Red
    exit 1
}
function Have([string]$cmd) { [bool](Get-Command $cmd -ErrorAction SilentlyContinue) }
function Refresh-Path {
    $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [Environment]::GetEnvironmentVariable("Path", "User")
}
function Run([string]$exe, [string[]]$arguments, [string]$what) {
    & $exe @arguments | Out-Host
    if ($LASTEXITCODE -ne 0) { Fail "$what failed (exit code $LASTEXITCODE). Scroll up for the reason." }
}
function Winget-Install([string]$id, [string]$name) {
    if (-not (Have "winget")) {
        Fail "winget is missing, so $name cannot be installed automatically. Install 'App Installer' from the Microsoft Store, or install $name yourself, then run again."
    }
    Note "installing $name with winget ..."
    & winget install -e --id $id --accept-package-agreements --accept-source-agreements --silent
    Refresh-Path
}
function Find-Python {
    if (Have "py") {
        try {
            $p = & py -3.11 -c "import sys; print(sys.executable)" 2>$null
            if ($LASTEXITCODE -eq 0 -and $p) { return $p.Trim() }
        } catch { }
    }
    foreach ($x in @("$env:LOCALAPPDATA\Programs\Python\Python311\python.exe", "C:\Program Files\Python311\python.exe")) {
        if (Test-Path $x) { return $x }
    }
    return $null
}
function Venv-Python([string]$dir) { return (Join-Path $PSScriptRoot "$dir\Scripts\python.exe") }
function Make-Venv([string]$dir, [string]$py) {
    $vp = Venv-Python $dir
    if (Test-Path $vp) {
        $v = (& $vp -c "import sys; print('%d.%d' % sys.version_info[:2])" | Select-Object -Last 1)
        if ($v -eq "3.11") { return $vp }
        Note "$dir uses Python $v; rebuilding it with Python 3.11 ..."
        Remove-Item -Recurse -Force $dir
    }
    Run $py @("-m", "venv", $dir) "Creating $dir" | Out-Null
    Run $vp @("-m", "pip", "install", "--upgrade", "pip", "--quiet") "Updating pip" | Out-Null
    return $vp
}
function Set-EnvValue([string]$key, [string]$value) {
    $path = Join-Path $PSScriptRoot ".env"
    $lines = @()
    if (Test-Path $path) { $lines = @(Get-Content -LiteralPath $path -Encoding UTF8) }
    $found = $false
    for ($i = 0; $i -lt $lines.Count; $i++) {
        if ($lines[$i] -match "^\s*$key\s*=") { $lines[$i] = "$key=$value"; $found = $true }
    }
    if (-not $found) { $lines += "$key=$value" }
    [IO.File]::WriteAllLines($path, [string[]]$lines, (New-Object Text.UTF8Encoding $false))
}
function Get-EnvValue([string]$key) {
    $path = Join-Path $PSScriptRoot ".env"
    if (-not (Test-Path $path)) { return "" }
    foreach ($l in Get-Content -LiteralPath $path -Encoding UTF8) {
        if ($l -match "^\s*$key\s*=\s*(.*)$") { return $Matches[1].Trim() }
    }
    return ""
}
function Random-Secret([int]$n) {
    $chars = "abcdefghijkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789".ToCharArray()
    $bytes = New-Object byte[] $n
    [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    return -join ($bytes | ForEach-Object { $chars[$_ % $chars.Length] })
}
function Ollama-Exe {
    if (Have "ollama") { return (Get-Command ollama).Source }
    $x = "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe"
    if (Test-Path $x) { return $x }
    return $null
}
function Ollama-Up {
    try { Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 3 | Out-Null; return $true } catch { return $false }
}
function Start-Ollama([string]$exe) {
    if (Ollama-Up) { return }
    Note "starting Ollama ..."
    try { Start-Process -FilePath $exe -ArgumentList "serve" -WindowStyle Hidden } catch { }
    for ($i = 0; $i -lt 30; $i++) { Start-Sleep -Seconds 1; if (Ollama-Up) { return } }
    Fail "Ollama did not start. Open the Ollama app from the Start menu, then run again."
}

Write-Host "HunarVaani installer" -ForegroundColor Green
Write-Host "Folder: $PSScriptRoot"
if ($PSScriptRoot -match "OneDrive") {
    Warn "This folder is inside OneDrive. OneDrive syncing can lock files and slow the install."
    Warn "Better: move the folder to C:\HunarVaani and run INSTALL.bat from there."
    Read-Host "    Press Enter to continue here anyway, or close this window to move it first" | Out-Null
}
try { $longPaths = (Get-ItemProperty "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" -ErrorAction Stop).LongPathsEnabled } catch { $longPaths = 0 }
if ($longPaths -ne 1 -and $PSScriptRoot.Length -gt 40) {
    Warn "This folder path is long ($($PSScriptRoot.Length) characters) and Windows long paths are off."
    Warn "Some packages have very long file names and may fail to install. Move the folder to C:\HunarVaani if that happens."
}

# 1. tools --------------------------------------------------------------------------------------
Say "1/7 Checking Python 3.11, Git, Ollama and the GPU"
$py = Find-Python
if (-not $py) { Winget-Install "Python.Python.3.11" "Python 3.11"; $py = Find-Python }
if (-not $py) { Fail "Python 3.11 is not installed. Get it from python.org (3.11.x, tick 'Add python.exe to PATH')." }
Note "Python: $py"
if (-not (Have "git")) {
    Winget-Install "Git.Git" "Git"
    if (Test-Path "C:\Program Files\Git\cmd") { $env:Path += ";C:\Program Files\Git\cmd" }
}
if (-not (Have "git")) { Fail "Git is not installed (the voice model needs it). Get it from git-scm.com." }
Note "Git: OK"
$ollama = Ollama-Exe
if (-not $ollama) { Winget-Install "Ollama.Ollama" "Ollama"; $ollama = Ollama-Exe }
if (-not $ollama) { Fail "Ollama is not installed. Get it from ollama.com/download." }
Note "Ollama: $ollama"
$vram = 0
try {
    $vram = [int]((& nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits) | Select-Object -First 1).Trim()
    $gpuName = ((& nvidia-smi --query-gpu=name --format=csv,noheader) | Select-Object -First 1).Trim()
    Note "GPU: $gpuName, $vram MiB"
} catch { Warn "nvidia-smi did not answer: no NVIDIA GPU or an old driver. Update the driver from nvidia.com." }
if (-not $Model) {
    $Model = Get-EnvValue "LLM_MODEL"
    if (-not $Model -or $Model -eq "gemma4:e4b") {
        if ($vram -ge 11000) { $Model = "gemma4:e4b" }
        elseif ($vram -ge 7500) { $Model = "gemma4:e4b-it-qat" }
        else { $Model = "gemma4:e2b-it-qat" }
    }
}
Note "LLM for this GPU: $Model"

if (-not $OnlyVoices) {
    # 2. server environment ---------------------------------------------------------------------
    Say "2/7 Server environment (.venv): packages and speech-to-text (a few minutes)"
    $vp = Make-Venv ".venv" $py
    Run $vp @("-m", "pip", "install", "-r", "requirements.txt") "Installing server packages"
    Run $vp @("-m", "pip", "install", "torch==2.7.1", "torchaudio==2.7.1", "--index-url", "https://download.pytorch.org/whl/cpu") "Installing PyTorch (CPU, for speech-to-text)"
    Run $vp @("-m", "pip", "install", "-r", "requirements-models.txt") "Installing speech-to-text packages"

    # 3. settings ------------------------------------------------------------------------------
    Say "3/7 Settings (.env)"
    if (-not (Test-Path ".env")) { Copy-Item ".env.example" ".env" }
    Set-EnvValue "HV_MODELS" "real"
    Set-EnvValue "LLM_MODEL" $Model
    Set-EnvValue "STT_DEVICE" "cpu"
    if ((Get-EnvValue "OFFICER_PASSWORD") -in @("", "change-me")) { Set-EnvValue "OFFICER_PASSWORD" (Random-Secret 12) }
    if ((Get-EnvValue "EXOTEL_WS_TOKEN") -match "^(|change-me.*)$") { Set-EnvValue "EXOTEL_WS_TOKEN" (Random-Secret 32) }
    Note "real models on, LLM $Model, speech-to-text on the CPU (keeps the GPU for the LLM)"
}

# 4. Hugging Face ------------------------------------------------------------------------------
Say "4/7 Hugging Face access for the AI4Bharat models"
$vp = Venv-Python ".venv"
if (-not (Test-Path $vp)) { Fail "Run the installer once without -OnlyVoices first." }
$repos = @("ai4bharat/indic-conformer-600m-multilingual")
if (-not $SkipVoices) { $repos += "ai4bharat/indic-parler-tts" }
$checkAccess = @"
import sys
from huggingface_hub import hf_hub_download
bad = []
for repo in sys.argv[1:]:
    try:
        hf_hub_download(repo, 'config.json')
    except Exception as exc:
        bad.append(repo + ': ' + type(exc).__name__)
print('\n'.join(bad))
sys.exit(1 if bad else 0)
"@
$checkFile = Join-Path $env:TEMP "hv_check_access.py"
[IO.File]::WriteAllText($checkFile, $checkAccess)
for ($try = 1; $try -le 3; $try++) {
    & $vp $checkFile @repos
    if ($LASTEXITCODE -eq 0) { Note "access to both models: OK"; break }
    if ($try -eq 3) { Fail "Still no access to the models above. Check that you clicked 'Agree' on both pages while logged in." }
    Write-Host ""
    Write-Host "    You need a free Hugging Face account and to accept each model's terms once:" -ForegroundColor Yellow
    Write-Host "      1. Log in (or sign up) at huggingface.co in the browser windows that open now"
    Write-Host "      2. On each model page that opens, click 'Agree and access repository'"
    Write-Host "      3. On the tokens page, create a token of type 'Read' and copy it"
    foreach ($r in $repos) { Start-Process "https://huggingface.co/$r" }
    Start-Process "https://huggingface.co/settings/tokens"
    $secure = Read-Host "    Paste the token here (it stays hidden) and press Enter" -AsSecureString
    $env:HV_HF_TOKEN = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure))
    & $vp -c "import os; from huggingface_hub import login; login(token=os.environ['HV_HF_TOKEN'], add_to_git_credential=False)"
    Remove-Item Env:\HV_HF_TOKEN -ErrorAction SilentlyContinue
}

if (-not $OnlyVoices) {
    # 5. downloads -----------------------------------------------------------------------------
    Say "5/7 Downloading speech-to-text (IndicConformer, ~2.5 GB) and the LLM ($Model, ~4-7 GB)"
    Run $vp @("-c", "from huggingface_hub import snapshot_download; print(snapshot_download('ai4bharat/indic-conformer-600m-multilingual'))") "Downloading IndicConformer"
    Run $vp @("scripts\load_stt.py") "Loading IndicConformer"
    Start-Ollama $ollama
    & $ollama pull $Model
    if ($LASTEXITCODE -ne 0) {
        Warn "pull failed; updating Ollama (Gemma 4 needs a recent version) and trying again ..."
        Get-Process -Name "ollama*" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2
        & winget upgrade -e --id Ollama.Ollama --accept-package-agreements --accept-source-agreements --silent
        Start-Sleep -Seconds 5; Start-Ollama $ollama
        Run $ollama @("pull", $Model) "Downloading the LLM"
    }
}

# 6. voices ------------------------------------------------------------------------------------
if (-not $SkipVoices) {
    Say "6/7 Voice: Indic Parler-TTS on the GPU, rendering every spoken line ($LangList)"
    $tp = Make-Venv ".venv-tts" $py
    Run $tp @("-m", "pip", "install", "torch==2.7.1", "torchaudio==2.7.1", "--index-url", "https://download.pytorch.org/whl/cu128") "Installing PyTorch with CUDA 12.8"
    Run $tp @("-m", "pip", "install", "-r", "requirements-tts.txt") "Installing Parler-TTS"
    & $tp -c "import torch, sys; ok = torch.cuda.is_available(); print('    PyTorch sees the GPU:', torch.cuda.get_device_name(0) if ok else 'NO'); sys.exit(0 if ok else 1)"
    if ($LASTEXITCODE -ne 0) {
        Warn "PyTorch cannot use the GPU, so rendering would take hours. Update the NVIDIA driver (nvidia.com/drivers) and run again."
        Read-Host "    Press Enter to render on the CPU anyway, or close this window" | Out-Null
    }
    if (Ollama-Up) { try { & $ollama stop $Model | Out-Null } catch { } }  # free the GPU memory for the voice model
    Note "Each line takes a few seconds; progress and time left are shown. You can stop with Ctrl+C and run"
    Note "'.\install.ps1 -OnlyVoices' later: finished lines are kept."
    Run $tp @("scripts\render_audio.py", "--langs", $LangList) "Rendering the voice"
} else {
    Note "skipped the voice (the kiosk uses the browser voice until you run: .\install.ps1 -OnlyVoices)"
}

# 7. checks ------------------------------------------------------------------------------------
Say "7/7 Checking every model and running the tests"
Start-Ollama $ollama
& $vp "scripts\check_models.py"
$modelsOk = $LASTEXITCODE -eq 0
& $vp -c "import sys, unittest; r = unittest.TextTestRunner(stream=sys.stdout, verbosity=0).run(unittest.defaultTestLoader.discover('tests')); print('    tests:', r.testsRun, 'run,', len(r.failures) + len(r.errors), 'failed')" 2>$null

Write-Host ""
if ($modelsOk) { Write-Host "Installed. Everything runs on this laptop." -ForegroundColor Green }
else { Write-Host "Installed, but a model check failed (see the FAIL line above, and README section 7)." -ForegroundColor Yellow }
Write-Host ""
Write-Host "Start:    double-click RUN.bat   (or .\run.ps1)"
Write-Host "Kiosk:    http://localhost:8000/kiosk    (the port is printed when it starts)"
Write-Host "Officer:  http://localhost:8000/officer  user: $(Get-EnvValue 'OFFICER_USER')  password: in the .env file (OFFICER_PASSWORD)"
