# Code Signing Plan

This document captures the Windows signing strategy before we add signing
credentials to CI. The app can be released unsigned today, but public sharing is
better with Authenticode signatures on both the portable `.exe` and installer.

## Current Decision

Microsoft Artifact Signing is the chosen signing provider. The Windows Release
workflow now supports it with GitHub OIDC, signs the portable application before
building the installer, signs the installer afterwards, and verifies both
Authenticode signatures before release assets are prepared.

The workflow remains unsigned by default until the Azure account, certificate
profile, federated credential, repository settings, and roles below are
configured. A partially configured signing mode fails the release instead of
silently publishing unsigned artifacts.

## Recommended Path

Use Microsoft Artifact Signing when the project is ready for public or repeated
external distribution.

Reasons:

- Microsoft positions Artifact Signing as a managed signing service with
  certificate lifecycle management in FIPS 140-2 Level 3 HSMs.
- It supports SignTool and GitHub Actions integrations.
- It avoids committing or uploading a long-lived private key file to the
  repository or workflow workspace.
- The signing model fits a future CI release workflow better than a local,
  manual certificate process.

Keep the current unsigned release path if this app is only for local/internal
testing or if release signing cost and account validation are not worth it yet.

## Alternatives

| Option | Use When | Risks And Notes |
| --- | --- | --- |
| Unsigned release | Private testing, internal handoff, or early prototype distribution. | Windows SmartScreen warnings are expected. Users must trust the source manually. |
| Microsoft Artifact Signing | Public or repeated release distribution where CI signing should be managed and auditable. | Requires Azure setup, identity validation, roles, and signing integration work. |
| Traditional certificate with SignTool certificate store | You already have a compliant certificate and signing host. | Requires secure key storage and runner access to the certificate. |
| PFX secret in GitHub Actions | Internal-only or temporary signing where policy allows it. | Not recommended for public-trust signing because private key handling is weaker and certificate policies may disallow exportable keys. |
| EV certificate | You need stronger publisher identity and reputation behavior. | Higher cost/friction; still requires secure hardware-backed key handling. |

## Signing Scope

When signing is implemented, sign both release artifacts:

- `PDF-to-DXF-Desktop-<version>.exe`
- `PDF-to-DXF-Desktop-Setup-<version>.exe`

Sign after PyInstaller and installer build, before release asset upload. Verify
both signatures before creating the GitHub Release.

## CI Contract

The release workflow currently defaults to unsigned mode.

Supported planning modes in `scripts/validate_signing_config.py`:

- `unsigned`
- `azure-artifact-signing`
- `signtool-certificate-store`
- `signtool-pfx`

Current release workflow behavior:

- If `WINDOWS_SIGNING_MODE` is unset or `unsigned`, release proceeds and records
  that SmartScreen warnings are expected.
- If `WINDOWS_SIGNING_MODE=azure-artifact-signing`, the workflow requires a
  complete OIDC configuration, signs both release executables, and verifies
  them with `Get-AuthenticodeSignature` before creating the release.
- Any other signed planning mode fails safely because it does not have an
  implemented release step.

## Azure And GitHub Setup

Complete these steps in the Azure account that will own the public publisher
identity. None of these credentials belong in source control.

1. Create an Artifact Signing account, complete identity validation, and create
   a public-trust code-signing certificate profile.
2. Create an Azure application/service principal for GitHub Actions and assign
   it the `Artifact Signing Certificate Profile Signer` role for that profile.
3. Add a GitHub OIDC federated credential to the application and scope it to
   this repository and the release refs that are permitted to sign. Standard
   configurations may need separate credentials for tag releases and manual
   workflow runs from `main`.
4. Add these **GitHub Actions repository variables**:

   - `WINDOWS_SIGNING_MODE=azure-artifact-signing`
   - `AZURE_ARTIFACT_SIGNING_ENDPOINT`, matching the Azure signing account's
     region
   - `AZURE_ARTIFACT_SIGNING_ACCOUNT`
   - `AZURE_ARTIFACT_SIGNING_CERT_PROFILE`

5. Add these **GitHub Actions repository secrets**:

   - `AZURE_TENANT_ID`
   - `AZURE_CLIENT_ID`
   - `AZURE_SUBSCRIPTION_ID`

6. Run a draft release. It must show a successful signing step and an
   Authenticode verification report for both artifacts before it can be
   published.

OIDC is used instead of a long-lived Azure client secret or an exported signing
private key. The Microsoft Artifact Signing action supports GitHub-hosted
Windows runners and recommends OIDC authentication.

## Implementation Checklist

1. Complete the Azure and GitHub setup above.
2. Run a signed draft release.
3. Confirm both signatures in the workflow's verification report.
4. Run manual QA on the signed portable app and signed installer.
5. Update the published-release notes to remove the unsigned warning.

## References

- Microsoft Artifact Signing overview:
  https://learn.microsoft.com/en-us/azure/artifact-signing/overview
- Microsoft Artifact Signing integrations:
  https://learn.microsoft.com/en-us/azure/artifact-signing/how-to-signing-integrations
- Microsoft SignTool documentation:
  https://learn.microsoft.com/en-us/windows/win32/seccrypto/signtool
- GitHub Actions secrets:
  https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets
- Azure Login Action OIDC guidance:
  https://github.com/Azure/login
- Microsoft Artifact Signing GitHub Action:
  https://github.com/Azure/artifact-signing-action
