# Code Signing Plan

This document captures the Windows signing strategy before we add signing
credentials to CI. The app can be released unsigned today, but public sharing is
better with Authenticode signatures on both the portable `.exe` and installer.

## Current Decision

Keep releases unsigned until a signing provider is chosen. The release workflow
now records signing status and fails if a signed mode is configured before the
actual signing step exists. This avoids a half-signed or accidentally mislabeled
release.

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
- If `WINDOWS_SIGNING_MODE` is set to a signed mode, release fails until the
  matching signing step is deliberately added.

Future Artifact Signing configuration will likely need:

- `WINDOWS_SIGNING_MODE=azure-artifact-signing`
- `AZURE_ARTIFACT_SIGNING_ENDPOINT`
- `AZURE_ARTIFACT_SIGNING_ACCOUNT`
- `AZURE_ARTIFACT_SIGNING_CERT_PROFILE`
- Azure authentication through workload identity or service principal secrets.

## Implementation Checklist

1. Choose signing provider and account owner.
2. Complete provider identity validation.
3. Create signing certificate/profile.
4. Add CI authentication through GitHub repository or environment secrets.
5. Add a signing step between installer build and release asset preparation.
6. Sign portable `.exe`.
7. Sign installer `.exe`.
8. Verify both signatures with SignTool.
9. Update `docs/release-process.md` from unsigned/draft to signed release
   instructions.
10. Run manual QA on a signed installer before publishing.

## References

- Microsoft Artifact Signing overview:
  https://learn.microsoft.com/en-us/azure/artifact-signing/overview
- Microsoft Artifact Signing integrations:
  https://learn.microsoft.com/en-us/azure/artifact-signing/how-to-signing-integrations
- Microsoft SignTool documentation:
  https://learn.microsoft.com/en-us/windows/win32/seccrypto/signtool
- GitHub Actions secrets:
  https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets
