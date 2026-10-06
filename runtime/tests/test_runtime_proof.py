# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Exercise local and published package records used by the update proof."""

from __future__ import annotations

import hashlib
import importlib.util
import sys
from pathlib import Path

import pytest
from ruamel.yaml import YAML

SCRIPT = Path(__file__).parents[1] / "scripts" / "prove-runtime-update.py"
SPEC = importlib.util.spec_from_file_location("runtime_runtime_proof", SCRIPT)
runtime_proof = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = runtime_proof
SPEC.loader.exec_module(runtime_proof)


@pytest.fixture
def write_lock(tmp_path):
    def create(url, *, version=7, subdir="linux-64", digest="a" * 64, size=12):
        data = {
            "version": version,
            "environments": {"ship": {"packages": {"linux-64": [{"conda": url}]}}},
            "packages": [
                {"conda": url, "subdir": subdir, "sha256": digest, "size": size}
            ],
        }
        if size is None:
            del data["packages"][0]["size"]
        lock = tmp_path / "pixi.lock"
        with lock.open("w") as stream:
            YAML().dump(data, stream)
        return lock

    return create


@pytest.mark.parametrize("version", [6, 7])
def test_selected_packages_reads_release_asset_subdir_from_record(write_lock, version):
    url = "https://github.com/conda/conda/releases/download/26.9.0/conda-26.9.0-release_linux_64_0.conda"
    lock = write_lock(url, version=version)
    packages = runtime_proof.selected_packages(lock, "linux-64")
    assert packages[0].url == url
    assert packages[0].subdir == "linux-64"
    assert runtime_proof.find_conda_package(packages)[1] == "26.9.0"


@pytest.mark.parametrize(
    "location_kind", ["relative-path", "absolute-path", "file-url"]
)
def test_selected_packages_resolves_local_package_paths(
    tmp_path, write_lock, location_kind
):
    archive = tmp_path / "source packages" / "conda-26.9.0-release_0.conda"
    location = {
        "relative-path": "source packages/conda-26.9.0-release_0.conda",
        "absolute-path": str(archive),
        "file-url": archive.as_uri(),
    }[location_kind]
    package = runtime_proof.selected_packages(write_lock(location), "linux-64")[0]
    assert package.url == archive.as_uri()


def test_copy_runtime_root_preserves_absolute_package_urls(tmp_path, write_lock):
    archive = tmp_path / "source packages" / "conda-26.9.0-release_0.conda"
    lock = write_lock(str(archive))
    source = lock.parent
    (source / "pixi.toml").write_text(
        '[tool.conda-ship.update]\nchannel = "https://conda.anaconda.org/conda"\n'
    )
    (source / "runtime.condarc").write_text("channels:\n  - conda-forge\n")
    destination = tmp_path / "proof" / "gen2"
    destination.parent.mkdir()
    channel = (tmp_path / "proof" / "channel").as_uri()
    runtime_proof.copy_runtime_root(source, destination, channel)
    package = runtime_proof.selected_packages(destination / "pixi.lock", "linux-64")[0]
    assert package.url == archive.as_uri()
    assert channel in (destination / "pixi.toml").read_text()


def test_selected_packages_rejects_wrong_platform(write_lock):
    lock = write_lock(
        "https://github.com/conda/conda/releases/download/26.9.0/conda-26.9.0-release_0.conda",
        subdir="win-64",
    )
    with pytest.raises(RuntimeError, match="expected 'noarch' or 'linux-64'"):
        runtime_proof.selected_packages(lock, "linux-64")


@pytest.mark.parametrize("digest,size", [("", 12), ("a" * 64, 0)])
def test_selected_packages_rejects_missing_archive_integrity(write_lock, digest, size):
    lock = write_lock(
        "https://conda.anaconda.org/conda/linux-64/conda-26.9.0-release_0.conda",
        digest=digest,
        size=size,
    )
    with pytest.raises(RuntimeError, match="invalid"):
        runtime_proof.selected_packages(lock, "linux-64")


@pytest.mark.parametrize("published", [False, True])
def test_selected_packages_accepts_direct_archive_without_size(
    tmp_path, write_lock, published
):
    filename = "conda-runtime-updater-26.9.0-py_0.conda"
    url = (
        f"https://github.com/conda/conda/releases/download/26.9.0/{filename}"
        if published
        else str(tmp_path / "source-packages" / "noarch" / filename)
    )
    lock = write_lock(url, subdir="noarch", size=None)
    package = runtime_proof.selected_packages(lock, "linux-64")[0]
    assert package.filename == filename
    assert package.subdir == "noarch"
    assert package.sha256 == "a" * 64
    assert package.size is None


@pytest.mark.parametrize("changed", [False, True])
@pytest.mark.parametrize("known_size", [False, True])
def test_download_validates_local_source_archives(tmp_path, changed, known_size):
    content = b"the exact release archive"
    source = tmp_path / "conda-26.9.0-release_0.conda"
    source.write_bytes(content)
    package = runtime_proof.LockedPackage(
        source.as_uri(),
        source.name,
        "linux-64",
        hashlib.sha256(content).hexdigest(),
        len(content) if known_size else None,
    )
    if changed:
        source.write_bytes(b"X" * len(content))
    destination = tmp_path / "mirror" / source.name
    destination.parent.mkdir()
    if changed:
        with pytest.raises(RuntimeError, match="SHA-256 mismatch"):
            runtime_proof.download(package, destination)
        assert not destination.exists()
    else:
        runtime_proof.download(package, destination)
        assert destination.read_bytes() == content
    assert not destination.with_suffix(".conda.part").exists()


def test_runtime_proof_disables_user_always_yes(monkeypatch, tmp_path):
    monkeypatch.setenv("CONDA_ALWAYS_YES", "true")
    scenario = runtime_proof.Scenario(
        root=tmp_path,
        prefix=tmp_path / "prefix",
        stable=tmp_path / "bin/conda",
        envs=tmp_path / "envs",
        packages=tmp_path / "packages",
        platform="osx-arm64",
    )
    assert runtime_proof.runtime_environment(scenario)["CONDA_ALWAYS_YES"] == "false"
