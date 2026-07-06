from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import validate_release_version as release_version  # noqa: E402
from pdf_to_dxf.app_info import APP_VERSION  # noqa: E402


class ReleaseVersionTests(unittest.TestCase):
    def test_validates_app_version_and_tag(self) -> None:
        release = release_version.validate_release_version(tag=f"v{APP_VERSION}")

        self.assertEqual(release.release_version, APP_VERSION)
        self.assertEqual(release.release_tag, f"v{APP_VERSION}")
        self.assertEqual(release.project_version, APP_VERSION)

    def test_validates_manual_version_input(self) -> None:
        release = release_version.validate_release_version(version=APP_VERSION)

        self.assertEqual(release.release_tag, f"v{APP_VERSION}")

    def test_rejects_mismatched_release_version(self) -> None:
        with self.assertRaisesRegex(ValueError, "does not match APP_VERSION"):
            release_version.validate_release_version(version="9.9.9")

    def test_rejects_non_semver_tag(self) -> None:
        with self.assertRaisesRegex(ValueError, "vMAJOR.MINOR.PATCH"):
            release_version.validate_release_version(tag="v1")

    def test_rejects_version_with_leading_v(self) -> None:
        with self.assertRaisesRegex(ValueError, "without the leading v"):
            release_version.validate_release_version(version=f"v{APP_VERSION}")

    def test_release_workflow_uses_version_guard_and_release_assets(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "windows-release.yml").read_text(encoding="utf-8")

        self.assertIn('tags:', workflow)
        self.assertIn('"v*.*.*"', workflow)
        self.assertIn("contents: write", workflow)
        self.assertIn("scripts\\validate_release_version.py", workflow)
        self.assertIn("scripts/smoke_native_app.py", workflow)
        self.assertIn("scripts\\build_windows_installer.ps1", workflow)
        self.assertIn("gh release create", workflow)
        self.assertIn("PDF-to-DXF-Desktop-$env:APP_VERSION.exe", workflow)
        self.assertIn("PDF-to-DXF-Desktop-Setup-$env:APP_VERSION.exe", workflow)


if __name__ == "__main__":
    unittest.main()
