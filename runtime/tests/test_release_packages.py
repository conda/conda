# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

SCRIPT_PATH = Path(__file__).parents[1] / "scripts/publish-runtime-packages.py"
SPEC = importlib.util.spec_from_file_location("publish_runtime_packages", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
release_packages = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = release_packages
SPEC.loader.exec_module(release_packages)


def runtime_package(
    tmp_path: Path,
    subdir: str = "linux-64",
    version: str = "26.7.1.post3",
    *,
    name: str = "conda-runtime",
    build: str = "0",
):
    path = tmp_path / subdir / f"{name}-{version}-{build}.conda"
    path.parent.mkdir(parents=True)
    path.write_bytes(b"runtime")
    return release_packages.RuntimePackage(
        path=path,
        name=name,
        build=build,
        subdir=subdir,
        version=version,
        sha256=release_packages.file_sha256(path),
        size=path.stat().st_size,
    )


def api_metadata(package):
    return {
        "files": [
            {
                "basename": package.basename,
                "sha256": package.sha256,
                "size": package.size,
                "version": package.version,
                "labels": ["runtime"],
                "attrs": {
                    "build": package.build,
                    "build_number": 0,
                    "subdir": package.subdir,
                    **(
                        release_packages.NATIVE_IDENTITIES[package.subdir]
                        if package.name == "conda-runtime"
                        else {}
                    ),
                },
            }
        ]
    }


def test_remote_metadata_must_match_local_package(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    package = runtime_package(tmp_path)

    monkeypatch.setattr(
        release_packages,
        "get_json",
        lambda url, **_kwargs: (
            api_metadata(package)
            if "api.anaconda.org" in url
            else {
                "packages.conda": {
                    package.filename: {
                        "name": "conda-runtime",
                        "version": package.version,
                        "build": "0",
                        "build_number": 0,
                        "subdir": package.subdir,
                        "sha256": package.sha256,
                        "size": package.size,
                    }
                }
            }
        ),
    )
    assert release_packages.api_has(package)
    assert release_packages.repodata_has(package)

    mismatched = api_metadata(package)
    mismatched["files"][0]["sha256"] = "0" * 64
    monkeypatch.setattr(
        release_packages,
        "get_json",
        lambda _url, **_kwargs: mismatched,
    )
    with pytest.raises(release_packages.RemoteMismatch, match="sha256"):
        release_packages.api_has(package)

    mismatched = api_metadata(package)
    mismatched["files"][0]["attrs"]["target-triplet"] = "wrong"
    monkeypatch.setattr(
        release_packages,
        "get_json",
        lambda _url, **_kwargs: mismatched,
    )
    with pytest.raises(release_packages.RemoteMismatch, match="target-triplet"):
        release_packages.api_has(package)


@pytest.mark.parametrize(
    ("subdir", "expected"),
    [
        (
            "linux-64",
            {
                "platform": "linux",
                "arch": "x86_64",
                "machine": "x86_64",
                "operatingsystem": "linux",
                "target-triplet": "x86_64-any-linux",
            },
        ),
        (
            "linux-aarch64",
            {
                "platform": "linux",
                "arch": "aarch64",
                "machine": "aarch64",
                "operatingsystem": "linux",
                "target-triplet": "aarch64-any-linux",
            },
        ),
        (
            "osx-64",
            {
                "platform": "osx",
                "arch": "x86_64",
                "machine": "x86_64",
                "operatingsystem": "darwin",
                "target-triplet": "x86_64-any-darwin",
            },
        ),
        (
            "osx-arm64",
            {
                "platform": "osx",
                "arch": "arm64",
                "machine": "arm64",
                "operatingsystem": "darwin",
                "target-triplet": "arm64-any-darwin",
            },
        ),
        (
            "win-64",
            {
                "platform": "win",
                "arch": "x86_64",
                "machine": "x86_64",
                "operatingsystem": "win32",
                "target-triplet": "x86_64-any-win32",
            },
        ),
    ],
)
def test_native_identity_matches_anaconda_client(
    subdir: str,
    expected: dict[str, str],
):
    assert release_packages.NATIVE_IDENTITIES[subdir] == expected


def test_publish_skips_exact_files_and_uploads_only_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    existing = runtime_package(tmp_path / "existing")
    missing = runtime_package(tmp_path / "missing", "win-64")
    uploaded = set()
    commands = []

    def fake_has(package, *_args):
        return package is existing or package.basename in uploaded

    def fake_run(command, check):
        assert check is True
        commands.append(command)
        uploaded.add(missing.basename)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(release_packages, "api_has", fake_has)
    monkeypatch.setattr(release_packages, "repodata_has", fake_has)
    monkeypatch.setattr(release_packages.subprocess, "run", fake_run)

    release_packages.publish(
        [existing, missing],
        timeout=1,
        interval=0,
    )

    assert len(commands) == 1
    assert commands == [
        [
            "anaconda",
            "upload",
            "--user",
            "conda",
            "--label",
            "runtime",
            "--summary",
            "Conda runtime release packages",
            "--keep-basename",
            "--no-progress",
            str(missing.path),
        ]
    ]


@pytest.mark.parametrize("subdir", release_packages.SUBDIRS)
def test_all_platforms_use_conda_runtime(tmp_path: Path, subdir: str):
    package = runtime_package(tmp_path, subdir, "99.0.0")

    assert package.filename == "conda-runtime-99.0.0-0.conda"
    assert package.basename == f"{subdir}/conda-runtime-99.0.0-0.conda"


def staged_packages(tmp_path: Path, version: str = "99.0.0"):
    for subdir in release_packages.SUBDIRS:
        runtime_package(tmp_path / "update-packages", subdir, version)
        directory = tmp_path / "source-packages" / subdir
        directory.mkdir(parents=True)
        (
            directory / f"conda-{version}-runtime_{subdir.replace('-', '_')}_0.conda"
        ).write_bytes(b"conda")
    directory = tmp_path / "source-packages/noarch"
    directory.mkdir(parents=True)
    (directory / f"conda-runtime-updater-{version}-py_0.conda").write_bytes(b"updater")


def test_discovery_rejects_unexpected_windows_package(tmp_path: Path):
    version = "99.0.0"
    staged_packages(tmp_path, version)
    packages = release_packages.discover_packages(tmp_path, version)

    assert len(packages) == 11
    assert {package.name for package in packages} == {
        "conda",
        "conda-runtime",
        "conda-runtime-updater",
    }
    windows = tmp_path / "update-packages/win-64"
    (windows / f"conda-runtime-{version}-0.conda").rename(
        windows / f"other-runtime-{version}-0.conda"
    )

    with pytest.raises(SystemExit, match="expected"):
        release_packages.discover_packages(tmp_path, version)


def test_windows_remote_checks_use_conda_runtime(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    package = runtime_package(tmp_path, "win-64")
    urls = []

    def fake_get_json(url, **_kwargs):
        urls.append(url)
        if "api.anaconda.org" in url:
            return api_metadata(package)
        return {
            "packages.conda": {
                package.filename: {
                    "name": "conda-runtime",
                    "version": package.version,
                    "build": "0",
                    "build_number": 0,
                    "subdir": package.subdir,
                    "sha256": package.sha256,
                    "size": package.size,
                }
            }
        }

    monkeypatch.setattr(release_packages, "get_json", fake_get_json)

    assert release_packages.api_has(package)
    assert release_packages.repodata_has(package)
    assert any("/package/conda/conda-runtime" in url for url in urls)


@pytest.mark.parametrize("missing", ["conda", "conda-runtime-updater"])
def test_discovery_requires_source_packages(tmp_path, missing):
    staged_packages(tmp_path)
    package = next(
        package
        for package in release_packages.discover_packages(tmp_path, "99.0.0")
        if package.name == missing
    )
    package.path.unlink()
    with pytest.raises(SystemExit, match="expected"):
        release_packages.discover_packages(tmp_path, "99.0.0")


def test_publisher_verifies_source_packages_before_native_updates(
    tmp_path, monkeypatch
):
    staged_packages(tmp_path)
    batches = []
    monkeypatch.setattr(
        sys, "argv", ["publish-runtime-packages.py", str(tmp_path), "99.0.0"]
    )
    monkeypatch.setattr(
        release_packages,
        "publish",
        lambda packages, **_kwargs: batches.append(packages),
    )
    release_packages.main()
    assert [{package.name for package in batch} for batch in batches] == [
        {"conda", "conda-runtime-updater"},
        {"conda-runtime"},
    ]


def test_failed_source_publication_does_not_publish_native_updates(
    tmp_path, monkeypatch
):
    staged_packages(tmp_path)
    batches = []

    def failed_publish(packages, **_kwargs):
        batches.append(packages)
        raise release_packages.RemoteMismatch("source package differs")

    monkeypatch.setattr(
        sys, "argv", ["publish-runtime-packages.py", str(tmp_path), "99.0.0"]
    )
    monkeypatch.setattr(release_packages, "publish", failed_publish)
    with pytest.raises(release_packages.RemoteMismatch, match="source package differs"):
        release_packages.main()
    assert len(batches) == 1
    assert {package.name for package in batches[0]} == {
        "conda",
        "conda-runtime-updater",
    }


@pytest.mark.parametrize(
    ("name", "subdir", "build"),
    [
        ("conda", "osx-arm64", "runtime_osx_arm64_0"),
        ("conda-runtime-updater", "noarch", "py_0"),
    ],
)
def test_source_remote_metadata_uses_package_identity(
    tmp_path, monkeypatch, name, subdir, build
):
    package = runtime_package(tmp_path, subdir, name=name, build=build)
    urls = []

    def fake_get_json(url, **_kwargs):
        urls.append(url)
        if "api.anaconda.org" in url:
            return api_metadata(package)
        return {
            "packages.conda": {
                package.filename: {
                    "name": name,
                    "version": package.version,
                    "build": build,
                    "build_number": 0,
                    "subdir": subdir,
                    "sha256": package.sha256,
                    "size": package.size,
                }
            }
        }

    monkeypatch.setattr(release_packages, "get_json", fake_get_json)
    assert release_packages.api_has(package)
    assert release_packages.repodata_has(package)
    assert urls[0] == f"https://api.anaconda.org/package/conda/{name}"
    assert urls[1].startswith(
        f"https://conda.anaconda.org/conda/label/runtime/{subdir}/repodata.json?"
    )


def test_discovery_allows_source_checksum_manifest(tmp_path):
    staged_packages(tmp_path)
    manifest = tmp_path / "source-packages/SHA256SUMS.sources"
    manifest.write_text("source package checksums")
    assert len(release_packages.discover_packages(tmp_path, "99.0.0")) == 11
    manifest.rename(manifest.with_name("unexpected-manifest"))
    with pytest.raises(SystemExit, match="expected"):
        release_packages.discover_packages(tmp_path, "99.0.0")


def test_remote_package_requires_runtime_label(tmp_path, monkeypatch):
    package = runtime_package(tmp_path)
    metadata = api_metadata(package)
    metadata["files"][0]["labels"] = ["main"]
    monkeypatch.setattr(release_packages, "get_json", lambda _url, **_kwargs: metadata)
    with pytest.raises(release_packages.RemoteMismatch, match="not labeled 'runtime'"):
        release_packages.api_has(package)
