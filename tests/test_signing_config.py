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

    def test_rejects_signed_mode_when_signed_configuration_is_not_explicitly_enabled(self) -> None:
        with self.assertRaisesRegex(ValueError, "disabled for this invocation"):
            signing_config.validate_signing_config(
                {
                    "WINDOWS_SIGNING_MODE": signing_config.AZURE_ARTIFACT_SIGNING_MODE,
                    "AZURE_ARTIFACT_SIGNING_ENDPOINT": "https://eus.codesigning.azure.net",
                    "AZURE_ARTIFACT_SIGNING_ACCOUNT": "account",
                    "AZURE_ARTIFACT_SIGNING_CERT_PROFILE": "profile",
                    "AZURE_TENANT_ID": "tenant",
                    "AZURE_CLIENT_ID": "client",
                    "AZURE_SUBSCRIPTION_ID": "subscription",
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
                "AZURE_SUBSCRIPTION_ID": "subscription",
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
        self.assertIn("AZURE_SUBSCRIPTION_ID", config.missing)

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

    def test_release_workflow_uses_guarded_azure_artifact_signing(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "windows-release.yml").read_text(encoding="utf-8")
        verifier = (ROOT / "scripts" / "verify_authenticode_signatures.ps1").read_text(encoding="utf-8")

        self.assertIn("Validate signing configuration", workflow)
        self.assertIn("scripts\\validate_signing_config.py", workflow)
        self.assertIn("--allow-signed-modes", workflow)
        self.assertIn("WINDOWS_SIGNING_MODE", workflow)
        self.assertIn("signing-status.json", workflow)
        self.assertIn("id-token: write", workflow)
        self.assertIn("azure/login@v3", workflow)
        self.assertIn("azure/artifact-signing-action@v2", workflow)
        self.assertIn("verify_authenticode_signatures.ps1", workflow)
        self.assertIn("portable-authenticode-verification.json", workflow)
        self.assertIn("installer-authenticode-verification.json", workflow)
        self.assertLess(workflow.index("Sign portable executable"), workflow.index("Build installer"))
        self.assertLess(workflow.index("Build installer"), workflow.index("Sign installer"))
        self.assertLess(workflow.index("Sign installer"), workflow.index("Prepare release assets"))
        self.assertIn("Get-AuthenticodeSignature", verifier)
        self.assertIn('status -ne "Valid"', verifier)


if __name__ == "__main__":
    unittest.main()
