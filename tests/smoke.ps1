$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
if ($env:PYTHON) {
  $python = $env:PYTHON
} else {
  $python = "python"
}

Push-Location $root
try {
  & $python -m unittest discover -s tests
  & $python examples\make_sample_pdf.py examples\sample_vector.pdf
  & $python -m pdf_to_dxf convert examples\sample_vector.pdf examples\sample_vector.dxf --pages 1
  if (-not (Test-Path examples\sample_vector.dxf)) {
    throw "DXF was not created."
  }
  Select-String -Path examples\sample_vector.dxf -Pattern "POLYLINE" | Out-Null
  Select-String -Path examples\sample_vector.dxf -Pattern "VERTEX" | Out-Null
  Select-String -Path examples\sample_vector.dxf -Pattern "TEXT" | Out-Null
}
finally {
  Pop-Location
}
