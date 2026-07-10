"""QA downloaded Windows release artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pdf_to_dxf.app_info import APP_EXECUTABLE_NAME, APP_VERSION  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="QA downloaded Windows release artifacts.")
    parser.add_argument("--release-dir", required=True, type=Path, help="Folder containing downloaded release assets.")
    parser.add_argument("--version", default=APP_VERSION, help="Release version without leading v.")
    parser.add_argument("--work-dir", default=Path("out/release-artifact-qa"), type=Path)
    parser.add_argument("--expected-portable-sha256", help="Expected SHA-256 for the portable .exe.")
    parser.add_argument("--expected-installer-sha256", help="Expected SHA-256 for the installer .exe.")
    parser.add_argument("--skip-installer", action="store_true", help="Only QA the portable executable.")
    args = parser.parse_args(argv)

    summary = run_release_artifact_qa(
        release_dir=args.release_dir,
        version=args.version,
        work_dir=args.work_dir,
        expected_portable_sha256=args.expected_portable_sha256,
        expected_installer_sha256=args.expected_installer_sha256,
        skip_installer=args.skip_installer,
    )
    print(json.dumps(summary, indent=2))
    return 0


def run_release_artifact_qa(
    release_dir: Path,
    version: str,
    work_dir: Path,
    expected_portable_sha256: str | None = None,
    expected_installer_sha256: str | None = None,
    skip_installer: bool = False,
) -> dict[str, Any]:
    if os.name != "nt":
        raise RuntimeError("Windows release artifact QA must run on Windows.")

    release_dir = release_dir.resolve()
    work_dir = work_dir.resolve()
    portable_exe, installer_exe = release_asset_paths(release_dir, version)
    require_file(portable_exe)
    if not skip_installer:
        require_file(installer_exe)

    work_dir.mkdir(parents=True, exist_ok=True)
    portable_hash = sha256_file(portable_exe)
    validate_expected_hash(portable_exe, portable_hash, expected_portable_sha256)

    summary: dict[str, Any] = {
        "ok": True,
        "version": version,
        "release_dir": str(release_dir),
        "portable": {
            "path": str(portable_exe),
            "sha256": portable_hash,
            "smoke": run_packaged_smoke(portable_exe, work_dir / "portable-smoke"),
        },
    }

    if skip_installer:
        summary["installer"] = {"skipped": True}
        return summary

    installer_hash = sha256_file(installer_exe)
    validate_expected_hash(installer_exe, installer_hash, expected_installer_sha256)
    install_dir = work_dir / "installed-app"
    install_log = work_dir / "install.log"
    uninstall_log = work_dir / "uninstall.log"
    installed_exe = install_dir / f"{APP_EXECUTABLE_NAME}.exe"

    uninstaller = install_dir / "unins000.exe"
    installed_smoke: dict[str, Any] | None = None
    try:
        run_installer(installer_exe, install_dir, install_log)
        require_file(installed_exe)
        installed_smoke = run_packaged_smoke(installed_exe, work_dir / "installed-smoke")
    finally:
        if uninstaller.is_file():
            run_uninstaller(uninstaller, uninstall_log)

    assert installed_smoke is not None

    summary["installer"] = {
        "path": str(installer_exe),
        "sha256": installer_hash,
        "install_dir": str(install_dir),
        "install_log": str(install_log),
        "uninstall_log": str(uninstall_log),
        "install_log_ok": log_contains(install_log, "Installation process succeeded."),
        "uninstall_log_ok": log_contains(uninstall_log, "Uninstallation process succeeded."),
        "restart_required": log_contains(install_log, "Need to restart Windows? Yes")
        or log_contains(uninstall_log, "Need to restart Windows? Yes"),
        "smoke": installed_smoke,
    }
    if not summary["installer"]["install_log_ok"]:
        raise RuntimeError(f"Installer log does not confirm success: {install_log}")
    if not summary["installer"]["uninstall_log_ok"]:
        raise RuntimeError(f"Uninstaller log does not confirm success: {uninstall_log}")
    if summary["installer"]["restart_required"]:
        raise RuntimeError("Installer or uninstaller reported that Windows needs a restart.")
    return summary


def release_asset_paths(release_dir: Path, version: str) -> tuple[Path, Path]:
    portable_exe = release_dir / f"{APP_EXECUTABLE_NAME}-{version}.exe"
    installer_exe = release_dir / f"{APP_EXECUTABLE_NAME}-Setup-{version}.exe"
    return portable_exe, installer_exe


def require_file(path: Path) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"Required file not found: {path}")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_expected_hash(path: Path, actual: str, expected: str | None) -> None:
    if expected and actual.lower() != expected.lower():
        raise RuntimeError(f"SHA-256 mismatch for {path}: expected {expected.lower()}, got {actual.lower()}")


def run_packaged_smoke(exe_path: Path, work_dir: Path) -> dict[str, Any]:
    result = run_command(
        [
            sys.executable,
            str(ROOT / "scripts" / "smoke_native_app.py"),
            "--exe",
            str(exe_path),
            "--work-dir",
            str(work_dir),
        ],
        label=f"smoke test {exe_path.name}",
        timeout_seconds=180,
    )
    return json.loads(result.stdout)


def run_installer(installer_exe: Path, install_dir: Path, log_path: Path) -> None:
    install_dir.mkdir(parents=True, exist_ok=True)
    run_command(
        [
            str(installer_exe),
            "/VERYSILENT",
            "/SUPPRESSMSGBOXES",
            "/NORESTART",
            "/NOICONS",
            f"/DIR={install_dir}",
            f"/LOG={log_path}",
        ],
        label=f"install {installer_exe.name}",
        timeout_seconds=180,
    )
    wait_for_log(log_path, "Installation process succeeded.")


def run_uninstaller(uninstaller_exe: Path, log_path: Path) -> None:
    run_command(
        [
            str(uninstaller_exe),
            "/VERYSILENT",
            "/SUPPRESSMSGBOXES",
            "/NORESTART",
            f"/LOG={log_path}",
        ],
        label=f"uninstall {uninstaller_exe.name}",
        timeout_seconds=180,
    )
    wait_for_log(log_path, "Uninstallation process succeeded.")


def run_command(command: list[str], label: str, timeout_seconds: int) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"{label} failed with exit code {result.returncode}.\n\n"
            f"stdout:\n{result.stdout}\n\nstderr:\n{result.stderr}"
        )
    return result


def log_contains(path: Path, needle: str) -> bool:
    if not path.is_file():
        return False
    return needle in path.read_text(encoding="utf-8", errors="replace")


def wait_for_log(path: Path, needle: str, timeout_seconds: float = 20.0) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if log_contains(path, needle):
            return
        time.sleep(0.25)
    raise RuntimeError(f"Timed out waiting for {needle!r} in {path}")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
