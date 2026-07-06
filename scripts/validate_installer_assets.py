from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pdf_to_dxf.app_info import (  # noqa: E402
    APP_COMPANY,
    APP_DIR_NAME,
    APP_DISPLAY_NAME,
    APP_EXECUTABLE_NAME,
    APP_VERSION,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate Windows installer inputs.")
    parser.add_argument(
        "--installer",
        type=Path,
        help="Optional built installer .exe to validate.",
    )
    parser.add_argument(
        "--require-built-exe",
        action="store_true",
        help="Fail if the PyInstaller desktop executable is missing.",
    )
    args = parser.parse_args(argv)

    errors: list[str] = []
    warnings: list[str] = []

    required_files = {
        "installer script": ROOT / "installer" / "pdf-to-dxf.iss",
        "app icon": ROOT / "assets" / "app_icon.ico",
        "PyInstaller spec": ROOT / "windows_native_app.spec",
        "native app entry point": ROOT / "windows_native_app.py",
    }
    for label, path in required_files.items():
        if not path.is_file():
            errors.append(f"Missing {label}: {path}")
        elif path.stat().st_size <= 0:
            errors.append(f"Empty {label}: {path}")

    project_version = read_project_version(errors)
    if project_version and project_version != APP_VERSION:
        errors.append(
            f"pyproject.toml version {project_version!r} does not match "
            f"APP_VERSION {APP_VERSION!r}."
        )

    script_path = required_files["installer script"]
    if script_path.is_file():
        script_text = script_path.read_text(encoding="utf-8")
        expected_fragments = {
            "app name define": f'#define AppName "{APP_DISPLAY_NAME}"',
            "app exe define": f'#define AppExeName "{APP_EXECUTABLE_NAME}"',
            "app dir define": f'#define AppDirName "{APP_DIR_NAME}"',
            "publisher define": f'#define AppPublisher "{APP_COMPANY}"',
            "default version define": f'#define AppVersion "{APP_VERSION}"',
            "per-user install": r"DefaultDirName={localappdata}\Programs\{#AppDirName}",
            "no admin requirement": "PrivilegesRequired=lowest",
            "installer output": r"OutputDir={#RepoRoot}dist\installer",
            "desktop exe source": r'Source: "{#RepoRoot}dist\windows-native-app\{#AppExeName}.exe"',
            "post-install launch": r'Filename: "{app}\{#AppExeName}.exe"',
        }
        for label, fragment in expected_fragments.items():
            if fragment not in script_text:
                errors.append(f"Installer script missing {label}: {fragment}")

    built_exe = ROOT / "dist" / "windows-native-app" / f"{APP_EXECUTABLE_NAME}.exe"
    if built_exe.is_file():
        if built_exe.stat().st_size < 1_000_000:
            errors.append(f"Built executable looks too small: {built_exe}")
    elif args.require_built_exe:
        errors.append(f"Built executable is required but missing: {built_exe}")
    else:
        warnings.append(f"Built executable not present, skipped size check: {built_exe}")

    if args.installer:
        installer_path = args.installer.resolve()
        if not installer_path.is_file():
            errors.append(f"Installer not found: {installer_path}")
        elif installer_path.suffix.lower() != ".exe":
            errors.append(f"Installer does not have .exe suffix: {installer_path}")
        elif installer_path.stat().st_size < 1_000_000:
            errors.append(f"Installer looks too small: {installer_path}")

    summary = {
        "app_name": APP_DISPLAY_NAME,
        "app_version": APP_VERSION,
        "built_exe": str(built_exe),
        "installer": str(args.installer.resolve()) if args.installer else None,
        "warnings": warnings,
        "errors": errors,
    }
    print(json.dumps(summary, indent=2))

    if errors:
        return 1
    return 0


def read_project_version(errors: list[str]) -> str | None:
    pyproject_path = ROOT / "pyproject.toml"
    if not pyproject_path.is_file():
        errors.append(f"Missing pyproject.toml: {pyproject_path}")
        return None

    raw = pyproject_path.read_text(encoding="utf-8")
    try:
        import tomllib
    except ModuleNotFoundError:
        match = re.search(r'(?m)^version\s*=\s*"([^"]+)"', raw)
        return match.group(1) if match else None

    data = tomllib.loads(raw)
    project = data.get("project")
    if not isinstance(project, dict):
        errors.append("pyproject.toml is missing a [project] table.")
        return None
    version = project.get("version")
    if not isinstance(version, str):
        errors.append("pyproject.toml is missing project.version.")
        return None
    return version


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
