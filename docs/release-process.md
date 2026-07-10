# Release Process

Use this process to publish a versioned Windows desktop release. The release
workflow rebuilds from source, runs tests, smoke-tests the packaged app, builds
the installer, then attaches both Windows artifacts to a GitHub Release.

Release dry-run results are tracked in `docs\release-rehearsals.md`.

## Release Rules

- `pdf_to_dxf/app_info.py` `APP_VERSION` and `pyproject.toml` `project.version`
  must match.
- Release tags use `vMAJOR.MINOR.PATCH`, for example `v0.1.0`.
- The tag or manual workflow version must match `APP_VERSION`.
- Manual workflow releases are drafts by default.
- Tag-push releases are published immediately.
- The Windows app and installer remain unsigned until Azure Artifact Signing is
  configured. In unsigned mode, the workflow records the status in release
  notes and SmartScreen warnings are expected.
- When `WINDOWS_SIGNING_MODE=azure-artifact-signing` is fully configured, the
  workflow signs the portable app before creating the installer, signs the
  installer afterwards, and verifies both signatures before release assets are
  attached.

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

5. For downloaded release artifacts, run the automated artifact QA companion:

   ```powershell
   .\.venv\Scripts\python.exe scripts\qa_release_artifacts.py --release-dir out\release-v0.1.0 --work-dir out\release-v0.1.0-artifact-qa
   ```

6. Commit and push the version update.
7. Confirm the current signing decision in `docs\code-signing-plan.md`.
   For a public release, complete its Azure and GitHub setup section and run a
   signed draft release before publishing.

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

Until signing is configured, keep the draft release as a trusted test artifact
or mark the release notes clearly as unsigned. After the first signed draft,
run the manual native QA checklist against both signed artifacts before
publishing.

For draft releases, GitHub may display an `untagged-...` release URL until the
release is published even when the release metadata uses the requested tag name.
Re-check the final release URL and tag before publishing.

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
- If signing validation fails, unset `WINDOWS_SIGNING_MODE` or implement the
  matching signing step before releasing.
- If the packaged smoke test fails, do not publish the release; fix the app and
  create a new commit/tag.
