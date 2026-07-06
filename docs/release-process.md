# Release Process

Use this process to publish a versioned Windows desktop release. The release
workflow rebuilds from source, runs tests, smoke-tests the packaged app, builds
the installer, then attaches both Windows artifacts to a GitHub Release.

## Release Rules

- `pdf_to_dxf/app_info.py` `APP_VERSION` and `pyproject.toml` `project.version`
  must match.
- Release tags use `vMAJOR.MINOR.PATCH`, for example `v0.1.0`.
- The tag or manual workflow version must match `APP_VERSION`.
- Manual workflow releases are drafts by default.
- Tag-push releases are published immediately.
- The Windows app and installer are not code-signed yet, so SmartScreen
  warnings are expected.

## Before Release

1. Update `APP_VERSION` in `pdf_to_dxf/app_info.py`.
2. Update `project.version` in `pyproject.toml`.
3. Run tests:

   ```powershell
   .\.venv\Scripts\python.exe -m unittest discover -s tests
   ```

4. Run the native manual QA checklist:

   ```powershell
   .\.venv\Scripts\python.exe scripts\make_native_qa_fixtures.py --output-dir out\native-qa
   ```

   Then follow `docs\native-app-manual-qa.md`.

5. Commit and push the version update.

## Draft Release From GitHub UI

1. Open **Actions** in GitHub.
2. Select **Windows Release**.
3. Choose **Run workflow**.
4. Enter the version without `v`, for example `0.1.0`.
5. Leave **Create the release as a draft** enabled unless you are ready to
   publish immediately.

The workflow creates a release tag named `v<version>` and attaches:

- `PDF-to-DXF-Desktop-<version>.exe`
- `PDF-to-DXF-Desktop-Setup-<version>.exe`

## Published Release From Tag

Create and push a version tag:

```powershell
git tag v0.1.0
git push origin v0.1.0
```

The tag-triggered workflow verifies the tag already exists and publishes a
GitHub Release with the Windows artifacts attached.

## Recovery

- If version validation fails, fix `APP_VERSION`, `pyproject.toml`, or the tag
  so all three agree.
- If a release already exists, delete or edit the existing draft/release in
  GitHub before rerunning.
- If the packaged smoke test fails, do not publish the release; fix the app and
  create a new commit/tag.
