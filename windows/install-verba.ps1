# Verba – Installation für Windows 10/11
# Installiert (nur falls fehlend, alles kostenlos über winget): Git, Node.js LTS, Python 3.12, FFmpeg.
# Danach: Verba nach %USERPROFILE%\Verba, Python- und Web-Pakete, faster-whisper + Modell "small" (~465 MB),
# und eine Verknüpfung "Verba" auf dem Desktop. Dauer: je nach Internet 10–20 Minuten.

$ErrorActionPreference = "Stop"
$Repo   = "https://github.com/staninjok/verba.git"
$Branch = "claude/great-ritchie-s7bqiu"
$Dir    = Join-Path $env:USERPROFILE "Verba"
$Model  = "small"   # gut für Spanisch auf normalen Laptops; "base" ist schneller, "medium" genauer

function Step($text) { Write-Host "`n==> $text" -ForegroundColor Cyan }
function Refresh-Path {
  $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [Environment]::GetEnvironmentVariable("Path", "User")
}
function Ensure($wingetId, $command) {
  if (Get-Command $command -ErrorAction SilentlyContinue) { Write-Host "   $command vorhanden"; return }
  Write-Host "   installiere $wingetId …"
  winget install --id $wingetId -e --silent --accept-source-agreements --accept-package-agreements
  Refresh-Path
}

if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
  throw "winget fehlt. Bitte 'App Installer' aus dem Microsoft Store installieren und dieses Skript erneut starten."
}

Step "Grundprogramme prüfen"
Ensure "Git.Git" "git"
Ensure "OpenJS.NodeJS.LTS" "node"
Ensure "Gyan.FFmpeg" "ffmpeg"
$pyOk = $false
try { & py -3 --version *> $null; $pyOk = ($LASTEXITCODE -eq 0) } catch {}
if (-not $pyOk) {
  winget install --id Python.Python.3.12 -e --silent --accept-source-agreements --accept-package-agreements
  Refresh-Path
}

Step "Verba herunterladen nach $Dir"
if (Test-Path (Join-Path $Dir ".git")) {
  git -C $Dir fetch origin $Branch
  git -C $Dir checkout $Branch
  git -C $Dir pull --ff-only origin $Branch
} else {
  git clone --branch $Branch $Repo $Dir
}
Set-Location $Dir

Step "Python-Umgebung und Spracherkennung (faster-whisper) installieren"
$venvPy = Join-Path $Dir "backend\.venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) { & py -3 -m venv (Join-Path $Dir "backend\.venv") }
& $venvPy -m pip install --upgrade pip
& $venvPy -m pip install -r backend\requirements.txt -r backend\requirements-whisper.txt
if ($LASTEXITCODE -ne 0) { throw "Python-Pakete konnten nicht installiert werden." }

Step "Whisper-Modell '$Model' herunterladen (einmalig)"
$modelsDir = Join-Path $Dir "backend\models"
$modelPath = Join-Path $modelsDir "faster-whisper-$Model"
if (-not (Test-Path (Join-Path $modelPath "model.bin"))) {
  & $venvPy -c "from faster_whisper import download_model; download_model('$Model', output_dir=r'$modelPath')"
  if ($LASTEXITCODE -ne 0) { throw "Modell-Download fehlgeschlagen." }
} else { Write-Host "   Modell bereits vorhanden" }

Step "Einstellungen schreiben (.env)"
$envFile = Join-Path $Dir ".env"
if (-not (Test-Path $envFile)) {
  @(
    "VERBA_WHISPER_MODEL=$Model",
    "VERBA_WHISPER_MODEL_DIR=$modelsDir",
    "VERBA_ALLOWED_PROVIDERS=faster-whisper,mock",
    "VERBA_DEFAULT_PROVIDER=auto"
  ) | Set-Content -Encoding UTF8 $envFile
}

Step "Weboberfläche installieren und bauen"
npm install --prefix frontend --no-audit --no-fund
if ($LASTEXITCODE -ne 0) { throw "npm install fehlgeschlagen." }
npm --prefix frontend run build
if ($LASTEXITCODE -ne 0) { throw "Build der Weboberfläche fehlgeschlagen." }

Step "Desktop-Verknüpfung anlegen"
$desktop = [Environment]::GetFolderPath("Desktop")
$shell = New-Object -ComObject WScript.Shell
$lnk = $shell.CreateShortcut((Join-Path $desktop "Verba.lnk"))
$lnk.TargetPath = Join-Path $Dir "windows\Verba-starten.bat"
$lnk.WorkingDirectory = $Dir
$lnk.IconLocation = Join-Path $Dir "frontend\public\brand\favicon.ico"
$lnk.Description = "Verba – Transkription"
$lnk.Save()

Step "Verba als Werkzeug in Claude Desktop eintragen"
try {
  $cfgDir = Join-Path $env:APPDATA "Claude"
  $cfg = Join-Path $cfgDir "claude_desktop_config.json"
  New-Item -ItemType Directory -Force $cfgDir | Out-Null
  if (Test-Path $cfg) {
    Copy-Item $cfg "$cfg.bak-verba" -Force
    $json = Get-Content $cfg -Raw | ConvertFrom-Json
  }
  if (-not $json) { $json = [pscustomobject]@{} }
  if (-not $json.PSObject.Properties["mcpServers"]) {
    $json | Add-Member -NotePropertyName mcpServers -NotePropertyValue ([pscustomobject]@{})
  }
  $entry = [pscustomobject]@{ command = $venvPy; args = @((Join-Path $Dir "backend\verba_mcp.py")) }
  $json.mcpServers | Add-Member -NotePropertyName verba -NotePropertyValue $entry -Force
  $text = $json | ConvertTo-Json -Depth 20
  [IO.File]::WriteAllText($cfg, $text, (New-Object Text.UTF8Encoding $false))
  Write-Host "   eingetragen in $cfg (Claude Desktop neu starten)"
} catch {
  Write-Host "   Konnte Claude Desktop nicht automatisch einrichten – siehe docs\CLAUDE_TOOL.md" -ForegroundColor Yellow
}

Write-Host "`nFertig! Doppelklick auf 'Verba' auf dem Desktop startet die App im Browser." -ForegroundColor Green
Write-Host "Das Fenster mit den Meldungen muss offen bleiben, solange du Verba benutzt."
Read-Host "Enter drücken zum Schließen"
