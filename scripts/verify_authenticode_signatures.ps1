param(
    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string[]]$Path,
    [string]$Output = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$records = @(
    foreach ($item in $Path) {
        if (-not (Test-Path -LiteralPath $item -PathType Leaf)) {
            throw "Signature verification target does not exist: $item"
        }

        $resolvedPath = (Resolve-Path -LiteralPath $item).Path
        $signature = Get-AuthenticodeSignature -LiteralPath $resolvedPath
        $signer = $signature.SignerCertificate
        $timestamp = $signature.TimeStamperCertificate

        [pscustomobject]@{
            path = $resolvedPath
            status = $signature.Status.ToString()
            status_message = $signature.StatusMessage
            signer_subject = if ($signer) { $signer.Subject } else { $null }
            signer_thumbprint = if ($signer) { $signer.Thumbprint } else { $null }
            timestamp_subject = if ($timestamp) { $timestamp.Subject } else { $null }
        }
    }
)

$invalid = @($records | Where-Object { $_.status -ne "Valid" })
$payload = [pscustomobject]@{
    ok = ($invalid.Count -eq 0)
    files = @($records)
}

if ($Output) {
    $parent = Split-Path -Parent $Output
    if ($parent) {
        New-Item -ItemType Directory -Force $parent | Out-Null
    }
    $payload | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $Output -Encoding utf8
}

if ($invalid.Count -gt 0) {
    $failedPaths = $invalid.path -join ", "
    throw "Authenticode signature verification failed: $failedPaths"
}

Write-Host "Authenticode signature verification passed for $($records.Count) file(s)."
