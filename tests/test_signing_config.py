from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import validate_signing_config as signing_config  # noqa: E402


class SigningConfigTests(unittest.TestCase):
    def test_defaults_to_unsigned_mode(self) -> None:
        config = signing_config.validate_signing_config({})

        self.assertEqual(config.mode, signing_config.UNSIGNED_MODE)
        self.assertFalse(config.ready_to_sign)
        self.assertIn("Unsigned release", config.summary)

    def test_rejects_unknown_mode(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unsupported"):
            signing_config.validate_signing_config({"WINDOWS_SIGNING_MODE": "surprise"})

    def test_rejects_signed_mode_until_ci_signing_step_exists(self) -> None:
        with self.assertRaisesRegex(ValueError, "not enabled in CI yet"):
            signing_config.validate_signing_config(
                {
                    "WINDOWS_SIGNING_MODE": signing_config.AZURE_ARTIFACT_SIGNING_MODE,
                    "AZURE_ARTIFACT_SIGNING_ENDPOINT": "https://eus.codesigning.azure.net",
                    "AZURE_ARTIFACT_SIGNING_ACCOUNT": "account",
                    "AZURE_ARTIFACT_SIGNING_CERT_PROFILE": "profile",
                    "AZURE_TENANT_ID": "tenant",
                    "AZURE_CLIENT_ID": "client",
                    "AZURE_CLIENT_SECRET": "secret",
                }
            )

    def test_allows_complete_azure_artifact_signing_config_when_explicitly_enabled(self) -> None:
        config = signing_config.validate_signing_config(
            {
                "WINDOWS_SIGNING_MODE": signing_config.AZURE_ARTIFACT_SIGNING_MODE,
                "AZURE_ARTIFACT_SIGNING_ENDPOINT": "https://eus.codesigning.azure.net",
                "AZURE_ARTIFACT_SIGNING_ACCOUNT": "account",
                "AZURE_ARTIFACT_SIGNING_CERT_PROFILE": "profile",
                "AZURE_TENANT_ID": "tenant",
                "AZURE_CLIENT_ID": "client",
                "AZURE_CLIENT_SECRET": "secret",
            },
            allow_signed_modes=True,
        )

        self.assertTrue(config.ready_to_sign)
        self.assertEqual(config.missing, [])

    def test_reports_missing_azure_artifact_signing_inputs(self) -> None:
        config = signing_config.validate_signing_config(
            {"WINDOWS_SIGNING_MODE": signing_config.AZURE_ARTIFACT_SIGNING_MODE},
            allow_signed_modes=True,
        )

        self.assertFalse(config.ready_to_sign)
        self.assertIn("AZURE_ARTIFACT_SIGNING_ENDPOINT", config.missing)
        self.assertIn("AZURE_CLIENT_SECRET or AZURE_FEDERATED_TOKEN_FILE", config.missing)

    def test_reports_complete_signtool_pfx_config(self) -> None:
        config = signing_config.validate_signing_config(
            {
                "WINDOWS_SIGNING_MODE": signing_config.SIGNTOOL_PFX_MODE,
                "WINDOWS_SIGNING_PFX_B64": "base64",
                "WINDOWS_SIGNING_PFX_PASSWORD": "password",
            },
            allow_signed_modes=True,
        )

        self.assertTrue(config.ready_to_sign)

    def test_release_workflow_records_signing_status_without_requiring_secrets(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "windows-release.yml").read_text(encoding="utf-8")

        self.assertIn("Validate signing configuration", workflow)
        self.assertIn("scripts\\validate_signing_config.py", workflow)
        self.assertIn("WINDOWS_SIGNING_MODE", workflow)
        self.assertIn("signing-status.json", workflow)


if __name__ == "__main__":
    unittest.main()
