# Native App Risk And Quality Plan

Last updated: 2026-07-03

This document preserves the native Windows app hardening plan so decisions and
next steps are not lost in chat history. It tracks the high-risk items first,
then quality improvements and release polish.

## Status Legend

- Done: implemented, tested locally, and pushed to GitHub.
- Partial: some protection exists, but the risk is not fully closed.
- Todo: not started yet.

## Highest Risk Items

| Status | Item | Current State | Next Action |
| --- | --- | --- | --- |
| Done | Overwrite protection | Native export asks before replacing an existing `.dxf`. | Keep covered by manual UI checks. |
| Done | Atomic DXF writes | Converter writes to a temp file and replaces the final DXF only after success. | Keep unit test coverage. |
| Done | Persistent error logs | Native app writes logs to `%LOCALAPPDATA%\PDF-to-DXF\logs\app.log` with a temp fallback. | Add log path to an About/Help dialog later. |
| Done | Worker process isolation | Native export runs through a worker process with a 300-second timeout. | Add Cancel button if long conversions become common. |
| Partial | Input limits | The app limits PDF size and curve segments. | Add max page count, entity-count estimates, and clearer "too large" guidance. |

## Quality Improvements

| Status | Item | Current State | Next Action |
| --- | --- | --- | --- |
| Partial | Native app tests | Helper, validation, worker, and packaged smoke paths are tested. | Add UI workflow tests or a documented manual QA checklist. |
| Done | Windows CI build | GitHub Actions builds, tests, smoke-tests, and uploads the desktop `.exe`. | Watch first runs and tune if dependency/package behavior changes. |
| Partial | Version info, icon, installer | App metadata, `.exe` icon, Windows version resource, and About diagnostics are implemented. The app is still not installer-packaged. | Add an installer target. |
| Todo | Code signing | SmartScreen can warn because the `.exe` is unsigned. | Decide certificate strategy before public distribution. |
| Partial | User-facing warnings | Conversion report already includes raster/no-vector warnings. | Promote important warnings into a visible warning panel. |
| Todo | Preview and validation | No PDF or DXF preview is available in the native UI. | Add PDF page preview first, then optional DXF geometry preview. |

## Recommended Next Work Order

1. Add an installer build, likely Inno Setup or WiX, so users install from a
   normal setup wizard instead of running a loose `.exe`.
2. Add page/entity-count safety estimates before conversion starts.
3. Add a warning summary area in the native app so raster-heavy or image-only
   PDFs are impossible to miss.
4. Add a manual QA checklist or UI automation path for selecting a PDF,
   inspecting it, exporting it, and confirming overwrite behavior.
5. Create a GitHub Release workflow that attaches the verified Windows artifact
   to a versioned release.
6. Plan code signing before sharing the app outside trusted internal users.
7. Add preview support after the export workflow is stable.

## Current Verification Coverage

- Unit tests: `python -m unittest discover -s tests`
- Native helper and worker tests: `tests/test_windows_native_app.py`
- Packaged app smoke test: `scripts/smoke_native_app.py`
- CI workflow: `.github/workflows/windows-desktop.yml`

## Important Product Limits

- This is a vector-first converter. Scanned or image-only PDFs are reported but
  not traced into editable CAD geometry.
- Generated DXF should still be reviewed in CAD software before production use.
- The desktop `.exe` is not code-signed yet, so Windows SmartScreen warnings are
  expected.
