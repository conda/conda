# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Check immutable release asset handling before uploading new files."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

SCRIPT = Path(__file__).parents[1] / "scripts/publish-github-assets.py"
SPEC = importlib.util.spec_from_file_location("publish_github_assets", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
github_assets = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(github_assets)

VERSION = "26.9.0"


@pytest.fixture
def github(monkeypatch):
    release = {"draft": False, "tag_name": VERSION, "immutable": False, "assets": []}
    commands = []
    downloads = {}

    def check_output(command, *, text):
        assert text is True
        assert command == ["gh", "api", f"repos/conda/conda/releases/tags/{VERSION}"]
        commands.append(command)
        return json.dumps(release)

    def run(command, *, check):
        assert check is True
        commands.append(command)
        if command[:3] == ["gh", "release", "upload"]:
            release["assets"].append(asset_metadata(Path(command[-1])))
        if command[:3] == ["gh", "release", "download"]:
            name = command[command.index("--pattern") + 1]
            directory = Path(command[command.index("--dir") + 1])
            (directory / name).write_bytes(downloads[name])

    monkeypatch.setattr(github_assets.subprocess, "check_output", check_output)
    monkeypatch.setattr(github_assets.subprocess, "run", run)
    return SimpleNamespace(release=release, commands=commands, downloads=downloads)


def asset_metadata(path):
    return {
        "name": path.name,
        "size": path.stat().st_size,
        "digest": f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}",
    }


def uploads(github):
    return [
        command
        for command in github.commands
        if command[:3] == ["gh", "release", "upload"]
    ]


@pytest.mark.parametrize("field", ["size", "digest"])
def test_mismatch_rejects_entire_batch_before_upload(tmp_path, github, field):
    (tmp_path / "a-new").write_bytes(b"new executable")
    existing = tmp_path / "z-existing"
    existing.write_bytes(b"published executable")
    metadata = asset_metadata(existing)
    metadata[field] = 0 if field == "size" else "sha256:" + "0" * 64
    github.release["assets"] = [metadata]

    with pytest.raises(ValueError, match="Refusing to replace published asset"):
        github_assets.publish(tmp_path, VERSION)

    assert uploads(github) == []


@pytest.mark.parametrize("has_digest", [True, False], ids=["api-digest", "download"])
def test_exact_rerun_skips_published_assets(tmp_path, github, has_digest):
    existing = tmp_path / "conda-linux"
    existing.write_bytes(b"published executable")
    metadata = asset_metadata(existing)
    if not has_digest:
        metadata.pop("digest")
        github.downloads[existing.name] = existing.read_bytes()
    github.release["assets"] = [metadata]

    github_assets.publish(tmp_path, VERSION)

    assert uploads(github) == []
    downloads = [
        command
        for command in github.commands
        if command[:3] == ["gh", "release", "download"]
    ]
    assert len(downloads) == (0 if has_digest else 1)


def test_immutable_release_refuses_missing_assets(tmp_path, github):
    (tmp_path / "conda-linux").write_bytes(b"new executable")
    github.release["immutable"] = True

    with pytest.raises(ValueError, match="Cannot add files to an immutable release"):
        github_assets.publish(tmp_path, VERSION)

    assert uploads(github) == []


def test_duplicate_platform_basenames_are_rejected(tmp_path, github):
    for subdir in ("linux-64", "osx-arm64"):
        directory = tmp_path / subdir
        directory.mkdir()
        (directory / f"conda-{VERSION}-0.conda").write_bytes(subdir.encode())

    with pytest.raises(ValueError, match="Release asset names must be unique"):
        github_assets.publish(tmp_path, VERSION, source_packages=True)

    assert github.commands == []


def test_source_checksums_cover_every_uploaded_archive(tmp_path, github):
    packages = []
    for subdir, name in (
        ("linux-64", f"conda-{VERSION}-runtime_linux_64_0.conda"),
        ("noarch", f"conda-runtime-updater-{VERSION}-py_0.conda"),
    ):
        directory = tmp_path / subdir
        directory.mkdir()
        package = directory / name
        package.write_bytes(subdir.encode())
        packages.append(package)

    github_assets.publish(tmp_path, VERSION, source_packages=True)

    expected = "".join(
        f"{hashlib.sha256(package.read_bytes()).hexdigest()}  {package.name}\n"
        for package in packages
    )
    assert (tmp_path / "SHA256SUMS.sources").read_text() == expected
    uploaded = {Path(command[-1]).name for command in uploads(github)}
    assert uploaded == {package.name for package in packages} | {"SHA256SUMS.sources"}


def test_uploaded_bytes_are_verified_before_publication_finishes(
    tmp_path, github, monkeypatch
):
    (tmp_path / "conda-linux").write_bytes(b"new executable")
    upload = github_assets.subprocess.run

    def corrupt_upload(command, *, check):
        upload(command, check=check)
        github.release["assets"][-1]["digest"] = "sha256:" + "0" * 64

    monkeypatch.setattr(github_assets.subprocess, "run", corrupt_upload)

    with pytest.raises(ValueError, match="Refusing to replace published asset"):
        github_assets.publish(tmp_path, VERSION)
