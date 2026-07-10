from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


UNSIGNED_MODE = "unsigned"
AZURE_ARTIFACT_SIGNING_MODE = "azure-artifact-signing"
SIGNTOOL_STORE_MODE = "signtool-certificate-store"
SIGNTOOL_PFX_MODE = "signtool-pfx"
SUPPORTED_MODES = {
    UNSIGNED_MODE,
    AZURE_ARTIFACT_SIGNING_MODE,
    SIGNTOOL_STORE_MODE,
    SIGNTOOL_PFX_MODE,
}


@dataclass(frozen=True)
class SigningConfig:
    mode: str
    ready_to_sign: bool
    summary: str
    missing: list[str]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate Windows code-signing configuration.")
    parser.add_argument("--output", type=Path, help="Optional JSON output path.")
    parser.add_argument(
        "--allow-signed-modes",
        action="store_true",
        help="Allow configured signing modes to pass once all required inputs are present.",
    )
    args = parser.parse_args(argv)

    try:
        config = validate_signing_config(os.environ, allow_signed_modes=args.allow_signed_modes)
    except ValueError as error:
        payload = {"ok": False, "error": str(error)}
        print(json.dumps(payload, indent=2))
        if args.output:
            write_json(args.output, payload)
        return 1

    payload = {"ok": True, **config.to_dict()}
    print(json.dumps(payload, indent=2))
    if args.output:
        write_json(args.output, payload)
    return 0


def validate_signing_config(
    environ: dict[str, str] | os._Environ[str],
    *,
    allow_signed_modes: bool = False,
) -> SigningConfig:
    mode = normalize_mode(environ.get("WINDOWS_SIGNING_MODE", ""))
    if mode == UNSIGNED_MODE:
        return SigningConfig(
            mode=UNSIGNED_MODE,
            ready_to_sign=False,
            summary="Unsigned release; Windows SmartScreen warnings are expected.",
            missing=[],
        )

    if not allow_signed_modes:
        raise ValueError(
            f"WINDOWS_SIGNING_MODE is {mode!r}, but signed configuration is disabled for this invocation. "
            "Use --allow-signed-modes only from a release workflow that implements the matching signing step."
        )

    missing = missing_inputs_for_mode(mode, environ)
    if missing:
        return SigningConfig(
            mode=mode,
            ready_to_sign=False,
            summary=f"Signing mode {mode!r} is selected but required inputs are missing.",
            missing=missing,
        )

    return SigningConfig(
        mode=mode,
        ready_to_sign=True,
        summary=f"Signing mode {mode!r} has the required configuration inputs.",
        missing=[],
    )


def normalize_mode(raw_mode: str) -> str:
    mode = (raw_mode or "").strip().lower()
    if not mode:
        return UNSIGNED_MODE
    if mode not in SUPPORTED_MODES:
        raise ValueError(
            f"Unsupported WINDOWS_SIGNING_MODE {raw_mode!r}. "
            f"Supported modes: {', '.join(sorted(SUPPORTED_MODES))}."
        )
    return mode


def missing_inputs_for_mode(mode: str, environ: dict[str, str] | os._Environ[str]) -> list[str]:
    if mode == AZURE_ARTIFACT_SIGNING_MODE:
        required = [
            "AZURE_ARTIFACT_SIGNING_ENDPOINT",
            "AZURE_ARTIFACT_SIGNING_ACCOUNT",
            "AZURE_ARTIFACT_SIGNING_CERT_PROFILE",
            "AZURE_TENANT_ID",
            "AZURE_CLIENT_ID",
            "AZURE_SUBSCRIPTION_ID",
        ]
        return missing_names(required, environ)
    if mode == SIGNTOOL_STORE_MODE:
        return missing_names(["WINDOWS_SIGNING_CERT_SHA1"], environ)
    if mode == SIGNTOOL_PFX_MODE:
        return missing_names(["WINDOWS_SIGNING_PFX_B64", "WINDOWS_SIGNING_PFX_PASSWORD"], environ)
    return []


def missing_names(names: list[str], environ: dict[str, str] | os._Environ[str]) -> list[str]:
    return [name for name in names if not environ.get(name)]


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
