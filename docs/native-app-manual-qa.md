# Native App Manual QA

Use this checklist before a release, after native UI changes, or when validating
a downloaded GitHub Actions artifact. It focuses on workflows that are awkward
to cover with unit tests: file pickers, overwrite prompts, visible warnings, and
packaged app behavior.

## Prepare

1. Build or download the native app.
   - Local executable:
     `dist\windows-native-app\PDF-to-DXF-Desktop.exe`
   - GitHub Actions artifact:
     `PDF-to-DXF-Desktop-installer-windows`
2. Generate QA PDFs:

   ```powershell
   .\.venv\Scripts\python.exe scripts\make_native_qa_fixtures.py --output-dir out\native-qa
   ```

3. Create a scratch output folder:

   ```powershell
   New-Item -ItemType Directory -Force out\native-qa\exports
   ```

4. For downloaded release artifacts, run the automated artifact QA companion
   before the interactive checks:

   ```powershell
   python scripts\qa_release_artifacts.py --release-dir out\release-v0.1.0 --work-dir out\release-v0.1.0-artifact-qa
   ```

5. Launch the app.

## Checklist

| Check | Steps | Expected Result |
| --- | --- | --- |
| About dialog | Click **About**. | Version, executable name, Python/Tk versions, and log path are visible. |
| Clean vector inspect | Select `out\native-qa\vector_basic.pdf`, then click **Inspect**. | Metrics show 1 page, vectors greater than 0, images 0, and warnings show `No warnings reported.` |
| Clean vector export | Save to `out\native-qa\exports\vector_basic.dxf`, then click **Export DXF**. | Success dialog appears, DXF exists, and report shows generated entities. |
| Overwrite cancel | Export `vector_basic.pdf` to the same DXF path again and choose **No** in the overwrite prompt. | Existing DXF remains, no success dialog appears, and app returns to ready state. |
| Overwrite confirm | Repeat the same export and choose **Yes**. | Existing DXF is replaced only after successful conversion. |
| Raster with vector warning | Inspect `out\native-qa\raster_with_vector.pdf`. | Metrics show vectors greater than 0 and images greater than 0; warning summary says raster images are skipped but vector geometry still exports. |
| Raster-only warning | Inspect `out\native-qa\raster_only.pdf`. | Metrics show vectors 0 and images greater than 0; warning summary says no vector geometry was found and raster tracing is not implemented. |
| Multi-page selection | Select `out\native-qa\multi_page.pdf`, set **Pages** to `2`, and inspect. | Report shows `page_count` 3 and `selected_pages` containing only 2. |
| Invalid page input | Set **Pages** to `0` and click **Inspect**. | A warning dialog appears and the warning summary explains pages must be 1 or greater. |
| Curve segment limit | Set **Curve Segments** to `999` and click **Inspect**. | A warning dialog appears and the warning summary explains the maximum curve segment limit. |

## Notes

- Keep generated fixtures under `out\native-qa`; this folder is intentionally
  untracked.
- Run the packaged smoke test as an automated companion check:

  ```powershell
  .\dist\windows-native-app\PDF-to-DXF-Desktop.exe --self-test-convert out\native-qa\vector_basic.pdf out\native-qa\exports\self_test.dxf
  ```

- For release assets, prefer `scripts\qa_release_artifacts.py` because it
  checks both the portable executable and installer path.

- Manual QA is still needed for native dialogs because the automated worker
  smoke test intentionally avoids opening interactive windows.
