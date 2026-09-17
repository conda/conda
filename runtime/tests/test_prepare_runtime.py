# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Check the release package identities embedded in conda binaries."""

from __future__ import annotations

import hashlib
import json
import runpy
import tomllib
from pathlib import Path

import pytest
from conda_package_handling.api import create as create_package

SCRIPT = Path(__file__).parents[1] / "scripts" / "prepare-runtime.py"
prepare_runtime = runpy.run_path(str(SCRIPT))["prepare_runtime"]


@pytest.fixture
def package_archive(tmp_path):
    def create(name, subdir, version="26.9.0", build="release_0", extension=".conda"):
        directory = tmp_path / "packages" / subdir
        directory.mkdir(parents=True, exist_ok=True)
        stem = f"{name}-{version}-{build}"
        archive = directory / f"{stem}{extension}"
        metadata = json.dumps(
            {"name": name, "version": version, "build": build, "subdir": subdir}
        )
        contents = tmp_path / "contents" / stem
        (contents / "info").mkdir(parents=True, exist_ok=True)
        (contents / "info" / "index.json").write_text(metadata)
        create_package(str(contents), ["info/index.json"], str(archive))
        return archive

    return create


@pytest.mark.parametrize("extension", [".conda", ".tar.bz2"])
@pytest.mark.parametrize("published", [False, True])
def test_prepare_runtime_uses_exact_archives(
    tmp_path, package_archive, extension, published
):
    conda = package_archive("conda", "linux-64", extension=extension)
    updater = package_archive("conda-runtime-updater", "noarch", extension=extension)
    release_url = "https://github.com/conda/conda/releases/download/26.9.0"
    local_channel = (tmp_path / "update-channel").as_uri()
    manifest_path = prepare_runtime(
        version="26.9.0",
        subdir="linux-64",
        packages_dir=tmp_path / "packages",
        output_dir=tmp_path / "runtime",
        release_url=release_url if published else None,
        update_channel=local_channel,
    )
    manifest = tomllib.loads(manifest_path.read_text())
    dependencies = manifest["feature"]["ship"]["dependencies"]
    for name, archive in (("conda", conda), ("conda-runtime-updater", updater)):
        assert dependencies[name] == {
            "url": f"{release_url}/{archive.name}" if published else archive.as_uri(),
            "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        }
    assert manifest["tool"]["conda-ship"]["update"]["channel"] == local_channel
    assert manifest["tool"]["conda-ship"]["install-name"] == "binary"
    if published:
        assert str(tmp_path) not in manifest_path.read_text().replace(local_channel, "")


@pytest.mark.parametrize(
    "name,subdir", [("conda", "linux-64"), ("conda-runtime-updater", "noarch")]
)
def test_prepare_runtime_rejects_mismatched_package_version(
    tmp_path, package_archive, name, subdir
):
    package_archive(name, subdir, version="26.7.2")
    with pytest.raises(ValueError, match="package version does not match"):
        prepare_runtime(
            version="26.9.0",
            subdir="linux-64",
            packages_dir=tmp_path / "packages",
            output_dir=tmp_path / "runtime",
        )
    assert not (tmp_path / "runtime").exists()


def test_prepare_runtime_rejects_duplicate_source_packages(tmp_path, package_archive):
    package_archive("conda", "linux-64", build="first_0")
    package_archive("conda", "linux-64", build="second_0")
    with pytest.raises(ValueError, match="more than one conda package"):
        prepare_runtime(
            version="26.9.0",
            subdir="linux-64",
            packages_dir=tmp_path / "packages",
            output_dir=tmp_path / "runtime",
        )


def test_prepare_runtime_rejects_package_in_wrong_subdir(tmp_path, package_archive):
    archive = package_archive("conda", "linux-64")
    (tmp_path / "packages" / "noarch").mkdir()
    archive.rename(tmp_path / "packages" / "noarch" / archive.name)
    with pytest.raises(ValueError, match="must belong to linux-64"):
        prepare_runtime(
            version="26.9.0",
            subdir="linux-64",
            packages_dir=tmp_path / "packages",
            output_dir=tmp_path / "runtime",
        )


def test_prepare_runtime_rejects_missing_updater(tmp_path, package_archive):
    package_archive("conda", "linux-64")
    with pytest.raises(
        ValueError, match="Missing release packages: conda-runtime-updater"
    ):
        prepare_runtime(
            version="26.9.0",
            subdir="linux-64",
            packages_dir=tmp_path / "packages",
            output_dir=tmp_path / "runtime",
        )


def test_prepare_runtime_rejects_renamed_archive(tmp_path, package_archive):
    archive = package_archive("conda", "linux-64", extension=".tar.bz2")
    archive.rename(archive.with_name("conda-26.9.0-changed_0.tar.bz2"))
    with pytest.raises(ValueError, match="filename does not match"):
        prepare_runtime(
            version="26.9.0",
            subdir="linux-64",
            packages_dir=tmp_path / "packages",
            output_dir=tmp_path / "runtime",
        )


@pytest.mark.parametrize(
    "release_url",
    [
        "file:///tmp/release",
        "https://user:password@example.org/release",
        "https://example.org/release?token=secret",
    ],
)
def test_prepare_runtime_rejects_invalid_publication_url(tmp_path, release_url):
    with pytest.raises(ValueError, match="Expected an absolute URL"):
        prepare_runtime(
            version="26.9.0",
            subdir="linux-64",
            packages_dir=tmp_path / "packages",
            output_dir=tmp_path / "runtime",
            release_url=release_url,
        )


@pytest.mark.parametrize(
    "version", ["26.9.0rc1", "26.9.0.post1", "26.9.0.dev1", "v26.9.0"]
)
def test_prepare_runtime_rejects_nonstable_version(tmp_path, version):
    with pytest.raises(ValueError, match="stable conda release version"):
        prepare_runtime(
            version=version,
            subdir="linux-64",
            packages_dir=tmp_path / "packages",
            output_dir=tmp_path / "runtime",
        )
