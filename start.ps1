$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
if ($env:PYTHON) {
  $python = $env:PYTHON
} elseif (Test-Path (Join-Path $root ".venv\Scripts\python.exe")) {
  $python = Join-Path $root ".venv\Scripts\python.exe"
} else {
  $python = "python"
}

Set-Location $root
Write-Host "Starting PDF to DXF service at http://127.0.0.1:8765"
& $python -m pdf_to_dxf serve --host 127.0.0.1 --port 8765
