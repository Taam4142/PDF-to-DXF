param(
    [string]$Python = "",
    [string]$IsccPath = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$RepoRoot = Split-Path -Parent $PSScriptRoot

if ([string]::IsNullOrWhiteSpace($Python)) {
    $VenvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"
    if (Test-Path -LiteralPath $VenvPython) {
        $Python = $VenvPython
    } else {
        $Python = "python"
    }
}

$Candidates = @()
if (-not [string]::IsNullOrWhiteSpace($IsccPath)) {
    $Candidates += $IsccPath
}
$Candidates += @(
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
)

$Compiler = $Candidates | Where-Object { $_ -and (Test-Path -LiteralPath $_) } | Select-Object -First 1
if (-not $Compiler) {
    throw "Inno Setup 6 compiler was not found. Install it with: choco install innosetup -y"
}

$Validator = Join-Path $RepoRoot "scripts\validate_installer_assets.py"
$InstallerScript = Join-Path $RepoRoot "installer\pdf-to-dxf.iss"

Push-Location $RepoRoot
try {
    $AppVersion = (& $Python -c "from pdf_to_dxf.app_info import APP_VERSION; print(APP_VERSION)").Trim()
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }

    $AppExe = Join-Path $RepoRoot "dist\windows-native-app\PDF-to-DXF-Desktop.exe"
    if (-not (Test-Path -LiteralPath $AppExe)) {
        throw "Desktop executable not found at $AppExe. Build it with pyinstaller before building the installer."
    }

    $InstallerExe = Join-Path $RepoRoot "dist\installer\PDF-to-DXF-Desktop-Setup-$AppVersion.exe"

    & $Python $Validator --require-built-exe
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }

    & $Compiler $InstallerScript "/DAppVersion=$AppVersion"
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }

    & $Python $Validator --installer $InstallerExe --require-built-exe
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
} finally {
    Pop-Location
}

Write-Host "Installer created: $InstallerExe"
