from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pdf_to_dxf.app_info import APP_VERSION  # noqa: E402


SEMVER_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")


@dataclass(frozen=True)
class ReleaseVersion:
    app_version: str
    project_version: str
    release_version: str
    release_tag: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate release version metadata.")
    parser.add_argument("--version", help="Release version without the leading v.")
    parser.add_argument("--tag", help="Release tag, for example v0.1.0.")
    args = parser.parse_args(argv)

    try:
        release = validate_release_version(version=args.version, tag=args.tag)
    except ValueError as error:
        print(json.dumps({"ok": False, "error": str(error)}, indent=2))
        return 1

    print(json.dumps({"ok": True, **release.to_dict()}, indent=2))
    return 0


def validate_release_version(version: str | None = None, tag: str | None = None) -> ReleaseVersion:
    project_version = read_project_version()
    if project_version != APP_VERSION:
        raise ValueError(
            f"pyproject.toml version {project_version!r} does not match APP_VERSION {APP_VERSION!r}."
        )

    normalized_version = normalize_version(version) if version else None
    normalized_tag_version = normalize_tag(tag) if tag else None
    release_version = normalized_tag_version or normalized_version or APP_VERSION
    if normalized_version and normalized_tag_version and normalized_version != normalized_tag_version:
        raise ValueError(f"Release version {normalized_version!r} does not match tag {tag!r}.")
    if release_version != APP_VERSION:
        raise ValueError(f"Release version {release_version!r} does not match APP_VERSION {APP_VERSION!r}.")

    return ReleaseVersion(
        app_version=APP_VERSION,
        project_version=project_version,
        release_version=release_version,
        release_tag=f"v{release_version}",
    )


def normalize_version(value: str) -> str:
    version = value.strip()
    if version.startswith("v"):
        raise ValueError("Use --tag for v-prefixed release tags, or pass --version without the leading v.")
    if not SEMVER_PATTERN.match(version):
        raise ValueError(f"Release version {value!r} must use MAJOR.MINOR.PATCH format.")
    return version


def normalize_tag(value: str) -> str:
    tag = value.strip()
    if not tag.startswith("v"):
        raise ValueError(f"Release tag {value!r} must start with v.")
    version = tag[1:]
    if not SEMVER_PATTERN.match(version):
        raise ValueError(f"Release tag {value!r} must use vMAJOR.MINOR.PATCH format.")
    return version


def read_project_version() -> str:
    pyproject_path = ROOT / "pyproject.toml"
    raw = pyproject_path.read_text(encoding="utf-8")
    try:
        import tomllib
    except ModuleNotFoundError:
        match = re.search(r'(?m)^version\s*=\s*"([^"]+)"', raw)
        if not match:
            raise ValueError("pyproject.toml is missing project.version.")
        return match.group(1)

    data = tomllib.loads(raw)
    project = data.get("project")
    if not isinstance(project, dict):
        raise ValueError("pyproject.toml is missing a [project] table.")
    version = project.get("version")
    if not isinstance(version, str):
        raise ValueError("pyproject.toml is missing project.version.")
    return version


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
