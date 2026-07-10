from __future__ import annotations

import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import qa_release_artifacts as release_qa  # noqa: E402
from pdf_to_dxf.app_info import APP_EXECUTABLE_NAME, APP_VERSION  # noqa: E402


class ReleaseArtifactQaTests(unittest.TestCase):
    def test_release_asset_paths_use_app_executable_name_and_version(self) -> None:
        portable, installer = release_qa.release_asset_paths(Path("dist/release"), APP_VERSION)

        self.assertEqual(portable, Path("dist/release") / f"{APP_EXECUTABLE_NAME}-{APP_VERSION}.exe")
        self.assertEqual(installer, Path("dist/release") / f"{APP_EXECUTABLE_NAME}-Setup-{APP_VERSION}.exe")

    def test_sha256_file_hashes_file_contents(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "artifact.exe"
            path.write_bytes(b"release artifact")

            self.assertEqual(release_qa.sha256_file(path), hashlib.sha256(b"release artifact").hexdigest())

    def test_validate_expected_hash_accepts_case_insensitive_match(self) -> None:
        release_qa.validate_expected_hash(Path("artifact.exe"), "abc123", "ABC123")

    def test_validate_expected_hash_rejects_mismatch(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "SHA-256 mismatch"):
            release_qa.validate_expected_hash(Path("artifact.exe"), "abc123", "def456")

    def test_require_file_rejects_missing_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            with self.assertRaisesRegex(FileNotFoundError, "Required file not found"):
                release_qa.require_file(Path(tmpdir) / "missing.exe")


if __name__ == "__main__":
    unittest.main()
