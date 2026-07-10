# Release Rehearsals

This log records release dry runs and draft releases that are useful for future
release decisions.

## 2026-07-10 - v0.1.0 Draft Windows Release

Status: Passed.

Links:

- GitHub Actions run:
  https://github.com/Taam4142/PDF-to-DXF/actions/runs/29063911883
- Draft release:
  https://github.com/Taam4142/PDF-to-DXF/releases/tag/untagged-15f0cf3563649c0e8521

Release assets:

- `PDF-to-DXF-Desktop-0.1.0.exe`
  - Size: `34,811,099` bytes
  - SHA-256:
    `ac2f4bc6070dac1db650e8a977edc7b7c7b765b48df4662deb0a6e195f18fb3b`
- `PDF-to-DXF-Desktop-Setup-0.1.0.exe`
  - Size: `35,978,724` bytes
  - SHA-256:
    `ec52e0530c2009201700d27d31440afbf6a815c50edfb98d4835aa923bb7731f`

Checks performed:

- Local release version validation passed for `0.1.0`.
- Local signing configuration validation passed in `unsigned` mode.
- Local unit test suite passed: `44` tests.
- Latest pushed Windows Desktop Build for commit `256a296` was already green.
- Windows Release workflow completed successfully.
- Remote workflow tests passed.
- Remote workflow packaged executable smoke test passed.
- Remote workflow installer build passed.
- Remote workflow signing-status validation passed as unsigned.
- Downloaded release assets matched the GitHub SHA-256 digests.
- Downloaded portable executable passed worker smoke testing:
  - `vector_entity_count`: `3`
  - `generated_entity_count`: `5`
- Downloaded installer completed a silent user-level install into a workspace
  QA folder with no restart required.
- Installed executable passed worker smoke testing:
  - `vector_entity_count`: `3`
  - `generated_entity_count`: `5`
- Silent uninstall completed successfully with no restart required.
- The same artifact path now passes `scripts\qa_release_artifacts.py`, including
  hash checks, portable smoke, silent install, installed-app smoke, uninstall,
  and cleanup verification.

Notes:

- The release is still unsigned. Windows SmartScreen warnings are expected.
- The draft release shows an `untagged-...` URL while the release metadata keeps
  `tagName` as `v0.1.0`. Re-check tag and URL behavior before publishing if the
  draft is promoted.
- Run the manual GUI checklist before publishing outside trusted internal
  testing.
