$ErrorActionPreference = "Stop"

param(
  [Parameter(Mandatory = $true)]
  [string]$InputPdf,
  [string]$OutputDxf = ""
)

if (-not $OutputDxf) {
  $OutputDxf = [System.IO.Path]::ChangeExtension($InputPdf, ".dxf")
}

Invoke-WebRequest `
  -Uri "http://127.0.0.1:8765/convert/pdf-to-dxf?unit=mm&scale=1" `
  -Method Post `
  -InFile $InputPdf `
  -ContentType application/pdf `
  -Headers @{ "X-File-Name" = [System.IO.Path]::GetFileName($InputPdf) } `
  -OutFile $OutputDxf

Write-Host "Wrote $OutputDxf"
