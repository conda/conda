#!/usr/bin/env python3
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Publish conda runtime packages to the official Anaconda.org channel."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

API_URL = "https://api.anaconda.org"
CHANNEL_URL = "https://conda.anaconda.org"
CHANNEL = "runtime"
OWNER = "conda"
PACKAGE_NAME = "conda-runtime"
SUBDIRS = ("linux-64", "linux-aarch64", "osx-64", "osx-arm64", "win-64")
NATIVE_IDENTITIES = {
    "linux-64": {
        "platform": "linux",
        "arch": "x86_64",
        "machine": "x86_64",
        "operatingsystem": "linux",
        "target-triplet": "x86_64-any-linux",
    },
    "linux-aarch64": {
        "platform": "linux",
        "arch": "aarch64",
        "machine": "aarch64",
        "operatingsystem": "linux",
        "target-triplet": "aarch64-any-linux",
    },
    "osx-64": {
        "platform": "osx",
        "arch": "x86_64",
        "machine": "x86_64",
        "operatingsystem": "darwin",
        "target-triplet": "x86_64-any-darwin",
    },
    "osx-arm64": {
        "platform": "osx",
        "arch": "arm64",
        "machine": "arm64",
        "operatingsystem": "darwin",
        "target-triplet": "arm64-any-darwin",
    },
    "win-64": {
        "platform": "win",
        "arch": "x86_64",
        "machine": "x86_64",
        "operatingsystem": "win32",
        "target-triplet": "x86_64-any-win32",
    },
}


class RemoteMismatch(RuntimeError):
    """A published package does not match the local package."""


@dataclass(frozen=True)
class RuntimePackage:
    path: Path
    subdir: str
    version: str
    sha256: str
    size: int
    name: str = PACKAGE_NAME
    build: str = "0"

    @property
    def filename(self) -> str:
        return f"{self.name}-{self.version}-{self.build}.conda"

    @property
    def basename(self) -> str:
        return f"{self.subdir}/{self.filename}"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def discover_packages(root: Path, version: str) -> list[RuntimePackage]:
    expected = {
        Path("source-packages")
        / subdir
        / f"conda-{version}-runtime_{subdir.replace('-', '_')}_0.conda": (
            "conda",
            subdir,
            f"runtime_{subdir.replace('-', '_')}_0",
        )
        for subdir in SUBDIRS
    }
    expected[
        Path("source-packages/noarch") / f"conda-runtime-updater-{version}-py_0.conda"
    ] = ("conda-runtime-updater", "noarch", "py_0")
    expected.update(
        {
            Path("update-packages") / subdir / f"{PACKAGE_NAME}-{version}-0.conda": (
                PACKAGE_NAME,
                subdir,
                "0",
            )
            for subdir in SUBDIRS
        }
    )
    actual = {
        path.relative_to(root)
        for directory in ("source-packages", "update-packages")
        for path in (root / directory).rglob("*")
        if path.is_file()
        and path.relative_to(root) != Path("source-packages/SHA256SUMS.sources")
    }
    if actual != set(expected):
        raise SystemExit(
            f"expected {sorted(map(str, expected))!r}, received "
            f"{sorted(map(str, actual))!r}"
        )
    return [
        RuntimePackage(
            path=root / relative,
            name=name,
            subdir=subdir,
            version=version,
            build=build,
            sha256=file_sha256(root / relative),
            size=(root / relative).stat().st_size,
        )
        for relative, (name, subdir, build) in sorted(expected.items())
    ]


def get_json(url: str, *, missing_ok: bool = False) -> dict[str, object] | None:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "Cache-Control": "no-cache",
            "User-Agent": "conda-runtime-release",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            value = json.load(response)
    except urllib.error.HTTPError as error:
        if missing_ok and error.code == 404:
            return None
        raise
    if not isinstance(value, dict):
        raise RuntimeError(f"{url} returned invalid JSON")
    return value


def verify_fields(
    source: str,
    actual: dict[str, object],
    expected: dict[str, object],
) -> None:
    differences = {
        key: (actual.get(key), value)
        for key, value in expected.items()
        if actual.get(key) != value
    }
    if differences:
        raise RemoteMismatch(f"{source} differs from local: {differences!r}")


def api_has(package: RuntimePackage) -> bool:
    metadata = get_json(
        f"{API_URL}/package/{OWNER}/{package.name}",
        missing_ok=True,
    )
    if metadata is None:
        return False
    files = metadata.get("files")
    if not isinstance(files, list):
        raise RuntimeError("Anaconda.org package metadata has no files list")
    matches = [
        item
        for item in files
        if isinstance(item, dict) and item.get("basename") == package.basename
    ]
    if not matches:
        return False
    if len(matches) != 1:
        raise RemoteMismatch(f"multiple remote files match {package.basename}")

    distribution = matches[0]
    verify_fields(
        f"Anaconda.org file {package.basename}",
        distribution,
        {
            "basename": package.basename,
            "sha256": package.sha256,
            "size": package.size,
            "version": package.version,
        },
    )
    labels = distribution.get("labels")
    if not isinstance(labels, list) or CHANNEL not in labels:
        raise RemoteMismatch(f"{package.basename} is not labeled {CHANNEL!r}")
    attrs = distribution.get("attrs")
    if not isinstance(attrs, dict):
        raise RemoteMismatch(f"{package.basename} has invalid attributes")
    verify_fields(
        f"Anaconda.org attributes for {package.basename}",
        attrs,
        {
            "build": package.build,
            "build_number": 0,
            "subdir": package.subdir,
            **(
                NATIVE_IDENTITIES[package.subdir]
                if package.name == PACKAGE_NAME
                else {}
            ),
        },
    )
    return True


def repodata_has(package: RuntimePackage) -> bool:
    metadata = get_json(
        f"{CHANNEL_URL}/{OWNER}/label/{CHANNEL}/{package.subdir}/repodata.json"
        f"?conda-runtime-release={time.time_ns()}",
        missing_ok=True,
    )
    if metadata is None:
        return False
    records = metadata.get("packages.conda")
    if not isinstance(records, dict):
        raise RuntimeError(f"{package.subdir} repodata has no packages.conda mapping")
    record = records.get(package.filename)
    if record is None:
        return False
    if not isinstance(record, dict):
        raise RemoteMismatch(f"{package.basename} has invalid repodata")
    verify_fields(
        f"repodata for {package.basename}",
        record,
        {
            "name": package.name,
            "version": package.version,
            "build": package.build,
            "build_number": 0,
            "subdir": package.subdir,
            "sha256": package.sha256,
            "size": package.size,
        },
    )
    return True


def publish(
    packages: list[RuntimePackage],
    *,
    timeout: float,
    interval: float,
) -> None:
    for package in packages:
        if api_has(package) or repodata_has(package):
            print(f"Anaconda.org already contains {package.basename}")
            continue
        subprocess.run(
            [
                "anaconda",
                "upload",
                "--user",
                OWNER,
                "--label",
                CHANNEL,
                "--summary",
                "Conda runtime release packages",
                "--keep-basename",
                "--no-progress",
                str(package.path),
            ],
            check=True,
        )

    deadline = time.monotonic() + timeout
    while True:
        pending = []
        for package in packages:
            try:
                if not api_has(package) or not repodata_has(package):
                    pending.append(package.basename)
            except (OSError, urllib.error.URLError):
                pending.append(package.basename)
        if not pending:
            return
        if time.monotonic() >= deadline:
            raise SystemExit(f"timed out waiting for Anaconda.org: {pending!r}")
        print(f"Waiting for Anaconda.org metadata: {pending!r}")
        time.sleep(interval)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("version")
    parser.add_argument("--timeout", type=float, default=300)
    parser.add_argument("--interval", type=float, default=5)
    args = parser.parse_args()

    packages = discover_packages(args.root, args.version)
    for names in ({"conda", "conda-runtime-updater"}, {PACKAGE_NAME}):
        publish(
            [package for package in packages if package.name in names],
            timeout=args.timeout,
            interval=args.interval,
        )
    print(f"Published and verified conda {args.version} packages for all platforms.")


if __name__ == "__main__":
    main()
