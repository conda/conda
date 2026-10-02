#!/usr/bin/env python3
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Attach release assets without replacing previously published bytes."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

REPOSITORY = "conda/conda"


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def verify_asset(path: Path, asset: dict, version: str) -> None:
    digest = asset.get("digest")
    if not digest:
        with tempfile.TemporaryDirectory() as temporary:
            subprocess.run(
                [
                    "gh",
                    "release",
                    "download",
                    version,
                    "--repo",
                    REPOSITORY,
                    "--pattern",
                    path.name,
                    "--dir",
                    temporary,
                ],
                check=True,
            )
            digest = f"sha256:{sha256(Path(temporary) / path.name)}"
    if asset["size"] != path.stat().st_size or digest != f"sha256:{sha256(path)}":
        raise ValueError(f"Refusing to replace published asset {path.name}")


def publish(directory: Path, version: str, *, source_packages: bool = False) -> None:
    repository = REPOSITORY
    paths = sorted(
        directory.glob("**/*.conda") if source_packages else directory.iterdir()
    )
    if not paths or any(not path.is_file() for path in paths):
        raise ValueError("Expected a nonempty collection of release files")
    if len({path.name for path in paths}) != len(paths):
        raise ValueError("Release asset names must be unique across platforms")
    if source_packages:
        checksums = directory / "SHA256SUMS.sources"
        checksums.write_text(
            "".join(f"{sha256(path)}  {path.name}\n" for path in paths),
            encoding="utf-8",
        )
        paths.append(checksums)

    release = json.loads(
        subprocess.check_output(
            ["gh", "api", f"repos/{repository}/releases/tags/{version}"], text=True
        )
    )
    if release["draft"] or release["tag_name"] != version:
        raise ValueError("Expected the published release that triggered this workflow")
    existing = {asset["name"]: asset for asset in release["assets"]}
    for path in paths:
        if asset := existing.get(path.name):
            verify_asset(path, asset, version)
        elif release.get("immutable"):
            raise ValueError("Cannot add files to an immutable release")

    pending = [path for path in paths if path.name not in existing]
    for path in pending:
        subprocess.run(
            ["gh", "release", "upload", version, "--repo", repository, str(path)],
            check=True,
        )
    if pending:
        published = json.loads(
            subprocess.check_output(
                ["gh", "api", f"repos/{repository}/releases/tags/{version}"], text=True
            )
        )
        assets = {asset["name"]: asset for asset in published["assets"]}
        for path in pending:
            if path.name not in assets:
                raise ValueError(f"Uploaded release asset is missing: {path.name}")
            verify_asset(path, assets[path.name], version)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("version")
    parser.add_argument("--source-packages", action="store_true")
    args = parser.parse_args()
    publish(args.directory, args.version, source_packages=args.source_packages)
