# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Create a conda-ship manifest from the exact release package archives."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import quote, urlsplit

from conda_package_streaming.package_streaming import stream_conda_info

PLATFORMS = ("linux-64", "linux-aarch64", "osx-64", "osx-arm64", "win-64")
CHANNEL = "https://conda.anaconda.org/conda/label/runtime"
CONDA_FORGE = "https://conda.anaconda.org/conda-forge"


def package_metadata(archive: Path) -> dict:
    """Read package identity without extracting files from the archive."""
    for tar, member in stream_conda_info(str(archive)):
        if member.name == "info/index.json" and member.isfile():
            with tar.extractfile(member) as index:
                return json.load(index)
    raise ValueError(f"Package has no info/index.json: {archive.name}")


def source_packages(packages_dir: Path, subdir: str, version: str) -> dict[str, Path]:
    """Require one matching conda package and one matching updater package."""
    selected = {}
    expected = {"conda": subdir, "conda-runtime-updater": "noarch"}
    for package_subdir in (subdir, "noarch"):
        for archive in sorted((packages_dir / package_subdir).glob("*")):
            if not archive.name.endswith((".conda", ".tar.bz2")):
                continue
            if archive.is_symlink() or not archive.is_file():
                raise ValueError(f"Package must be a regular file: {archive.name}")
            metadata = package_metadata(archive)
            name = metadata.get("name")
            if name not in expected:
                continue
            if name in selected:
                raise ValueError(f"Found more than one {name} package")
            if metadata.get("version") != version:
                raise ValueError(f"{name} package version does not match {version}")
            if (
                metadata.get("subdir") != expected[name]
                or package_subdir != expected[name]
            ):
                raise ValueError(f"{name} package must belong to {expected[name]}")
            stem = f"{name}-{version}-{metadata.get('build')}"
            if archive.name not in (f"{stem}.conda", f"{stem}.tar.bz2"):
                raise ValueError(
                    f"Package filename does not match its metadata: {archive.name}"
                )
            selected[name] = archive.resolve()
    missing = expected.keys() - selected.keys()
    if missing:
        raise ValueError(f"Missing release packages: {', '.join(sorted(missing))}")
    return selected


def validate_url(value: str, *, allow_file: bool = False) -> str:
    """Reject credentials and ambiguous release or update URLs."""
    parsed = urlsplit(value)
    valid_scheme = parsed.scheme == "https" and bool(parsed.netloc)
    if allow_file and parsed.scheme == "file":
        valid_scheme = parsed.path.startswith("/") and parsed.netloc in (
            "",
            "localhost",
        )
    if (
        not valid_scheme
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or any(character.isspace() for character in value)
    ):
        raise ValueError(
            "Expected an absolute URL without credentials, queries, or fragments"
        )
    return value.rstrip("/")


def prepare_runtime(
    *,
    version: str,
    subdir: str,
    packages_dir: Path,
    output_dir: Path,
    release_url: str | None = None,
    update_channel: str = CHANNEL,
) -> Path:
    """Write build policy, exact source package URLs, and persistent conda settings."""
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version):
        raise ValueError("Expected a stable conda release version in X.Y.Z form")
    if subdir not in PLATFORMS:
        raise ValueError(f"Unsupported runtime platform: {subdir}")
    update_channel = validate_url(update_channel, allow_file=True)
    if release_url is not None:
        release_url = validate_url(release_url)
    packages = source_packages(packages_dir.resolve(), subdir, version)
    dependencies = []
    for name, archive in sorted(packages.items()):
        url = (
            f"{release_url}/{quote(archive.name)}" if release_url else archive.as_uri()
        )
        with archive.open("rb") as package:
            digest = hashlib.file_digest(package, "sha256").hexdigest()
        dependencies.append(
            f'{name} = {{ url = {json.dumps(url)}, sha256 = "{digest}" }}'
        )
    manifest = f"""[workspace]
name = "conda-runtime"
channels = ["{CONDA_FORGE}"]
platforms = ["{subdir}"]
channel-priority = "strict"

[feature.ship.dependencies]
python = "3.12.*"
conda-self = ">=0.2.1"
{chr(10).join(dependencies)}

[environments]
ship = {{ features = ["ship"], no-default-feature = true }}

[tool.conda-ship]
runtime-name = "conda"
runtime-version = {json.dumps(version)}
delegate-executable = "conda"
artifact-layout = "embedded"
source-environment = "ship"
docs-url = "https://docs.conda.io/projects/conda/en/stable/"
install-scheme = "user-data"
install-name = "binary"
condarc-file = "runtime.condarc"
freeze-base = true

[tool.conda-ship.update]
channel = {json.dumps(update_channel)}
package = "conda-runtime"
build-number = 0
"""
    condarc = f"""channels:
  - {CHANNEL}
  - {CONDA_FORGE}
channel_priority: strict
envs_dirs:
  - ~/.conda/envs
pkgs_dirs:
  - ~/.conda/pkgs
plugins:
  self_permanent_packages:
    - conda-runtime-updater
"""
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "runtime.condarc").write_text(condarc, encoding="utf-8")
    manifest_path = output_dir / "pixi.toml"
    manifest_path.write_text(manifest, encoding="utf-8")
    return manifest_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True)
    parser.add_argument("--subdir", required=True, choices=PLATFORMS)
    parser.add_argument("--packages-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--release-url")
    parser.add_argument("--update-channel", default=CHANNEL)
    args = parser.parse_args()
    try:
        prepare_runtime(**vars(args))
    except ValueError as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
