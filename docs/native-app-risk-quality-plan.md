# Native App Risk And Quality Plan

Last updated: 2026-07-06

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
| Done | Input limits | The app limits PDF size, selected page count, curve segments, estimated source/vector load, estimated DXF entities, and estimated curve vertices before conversion starts. | Tune thresholds if real user PDFs need more room. |

## Quality Improvements

| Status | Item | Current State | Next Action |
| --- | --- | --- | --- |
| Partial | Native app tests | Helper, validation, worker, and packaged smoke paths are tested. | Add UI workflow tests or a documented manual QA checklist. |
| Done | Windows CI build | GitHub Actions builds, tests, smoke-tests, and uploads the desktop `.exe` plus installer artifact. | Watch first runs and tune if dependency/package behavior changes. |
| Done | Version info, icon, installer | App metadata, `.exe` icon, Windows version resource, About diagnostics, and Inno Setup installer packaging are implemented. | Add code signing before public distribution. |
| Todo | Code signing | SmartScreen can warn because the `.exe` is unsigned. | Decide certificate strategy before public distribution. |
| Done | User-facing warnings | Native inspect/export results show a visible warning summary above the raw JSON report, including raster-heavy and image-only cases. | Add manual QA coverage for warning visibility. |
| Todo | Preview and validation | No PDF or DXF preview is available in the native UI. | Add PDF page preview first, then optional DXF geometry preview. |

## Recommended Next Work Order

1. Add a manual QA checklist or UI automation path for selecting a PDF,
   inspecting it, exporting it, and confirming overwrite behavior.
2. Create a GitHub Release workflow that attaches the verified Windows artifact
   to a versioned release.
3. Plan code signing before sharing the app outside trusted internal users.
4. Add preview support after the export workflow is stable.

## Current Verification Coverage

- Unit tests: `python -m unittest discover -s tests`
- Native helper, warning summary, preflight, and worker tests:
  `tests/test_windows_native_app.py`
- Packaged app smoke test: `scripts/smoke_native_app.py`
- Installer asset validation: `scripts/validate_installer_assets.py`
- CI workflow: `.github/workflows/windows-desktop.yml`

## Important Product Limits

- This is a vector-first converter. Scanned or image-only PDFs are reported but
  not traced into editable CAD geometry.
- Generated DXF should still be reviewed in CAD software before production use.
- The desktop `.exe` and installer are not code-signed yet, so Windows
  SmartScreen warnings are expected.
