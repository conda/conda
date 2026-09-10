# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from conda import CONDA_PACKAGE_ROOT
from conda.base.constants import WINDOWS_LAUNCHER_STUB_PATH
from conda.common.serialize import json
from conda.core.launchers import get_windows_launcher_stub, verify_windows_launcher
from conda.exceptions import SafetyError
from conda.models.channel import Channel
from conda.models.enums import PathEnum
from conda.models.package_info import PackageInfo
from conda.models.records import PathDataV1, PathsData, PrefixRecord

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


def write_record(prefix: Path, name: str, subdir: str, paths=()) -> PrefixRecord:
    record = PrefixRecord(
        name=name,
        version="24.7.1" if name == "conda-launchers" else "3.14.0",
        build="h0_0",
        build_number=0,
        subdir=subdir,
        files=[path.path for path in paths],
        paths_data=PathsData(paths_version=1, paths=paths),
    )
    conda_meta = prefix / "conda-meta"
    conda_meta.mkdir(parents=True, exist_ok=True)
    (conda_meta / f"{name}-{record.version}-h0_0.json").write_text(
        json.dumps(record.dump()), encoding="utf-8"
    )
    return record


@pytest.fixture
def launcher_prefix(tmp_path: Path) -> Path:
    prefix = tmp_path / "source"
    paths = []
    for subdir, short_path in WINDOWS_LAUNCHER_STUB_PATH.items():
        path = prefix / short_path
        path.parent.mkdir(parents=True, exist_ok=True)
        data = subdir.encode()
        path.write_bytes(data)
        paths.append(
            PathDataV1(
                _path=short_path,
                path_type=PathEnum.hardlink,
                sha256=sha256(data).hexdigest(),
                size_in_bytes=len(data),
            )
        )
    write_record(prefix, "conda-launchers", "noarch", paths)
    return prefix


@pytest.mark.parametrize("subdir", WINDOWS_LAUNCHER_STUB_PATH)
def test_launcher_matches_target_python(
    tmp_path: Path, launcher_prefix: Path, subdir: str
):
    target = tmp_path / "target"
    write_record(target, "python", subdir)

    path, digest = get_windows_launcher_stub(target, source_prefixes=(launcher_prefix,))

    assert path == str(launcher_prefix / WINDOWS_LAUNCHER_STUB_PATH[subdir])
    assert digest == sha256(subdir.encode()).hexdigest()
    verify_windows_launcher(path, digest)


def test_launcher_matches_python_in_transaction(tmp_path: Path, launcher_prefix: Path):
    target = tmp_path / "target"
    write_record(target, "python", "win-64")
    python_record = PrefixRecord(
        name="python",
        version="3.14.0",
        build="h0_0",
        build_number=0,
        subdir="win-arm64",
    )
    python_info = PackageInfo(
        extracted_package_dir=str(tmp_path / "python"),
        package_tarball_full_path=str(tmp_path / "python.conda"),
        channel=Channel("https://example.org"),
        url="https://example.org/win-arm64/python.conda",
        repodata_record=python_record,
        paths_data=PathsData(paths_version=1, paths=()),
    )

    path, _ = get_windows_launcher_stub(
        target, source_prefixes=(launcher_prefix,), source_package_infos=(python_info,)
    )

    assert path == str(launcher_prefix / WINDOWS_LAUNCHER_STUB_PATH["win-arm64"])


def test_launcher_uses_extracted_package_during_upgrade(
    tmp_path: Path, launcher_prefix: Path
):
    target = tmp_path / "target"
    write_record(target, "python", "win-arm64")
    short_path = WINDOWS_LAUNCHER_STUB_PATH["win-arm64"]
    source = tmp_path / "extracted"
    path = source / short_path
    path.parent.mkdir(parents=True)
    path.write_bytes(b"new launcher")
    record = write_record(
        source,
        "conda-launchers",
        "noarch",
        [
            PathDataV1(
                _path=short_path,
                path_type=PathEnum.hardlink,
                sha256=sha256(b"new launcher").hexdigest(),
            )
        ],
    )
    package_info = PackageInfo(
        extracted_package_dir=str(source),
        package_tarball_full_path=str(tmp_path / "launchers.conda"),
        channel=Channel("https://example.org"),
        url="https://example.org/noarch/launchers.conda",
        repodata_record=record,
        paths_data=record.paths_data,
    )

    actual_path, digest = get_windows_launcher_stub(
        target, source_prefixes=(launcher_prefix,), source_package_infos=(package_info,)
    )

    assert actual_path == str(path)
    assert digest == sha256(b"new launcher").hexdigest()


@pytest.mark.parametrize("missing", ["file", "ownership", "package"])
def test_launcher_requires_owned_file(
    tmp_path: Path, launcher_prefix: Path, missing: str
):
    target = tmp_path / "target"
    write_record(target, "python", "win-arm64")
    if missing == "file":
        (launcher_prefix / WINDOWS_LAUNCHER_STUB_PATH["win-arm64"]).unlink()
    elif missing == "ownership":
        write_record(launcher_prefix, "conda-launchers", "noarch")
    else:
        (launcher_prefix / "conda-meta/conda-launchers-24.7.1-h0_0.json").unlink()

    with pytest.raises(FileNotFoundError, match="cli-arm64.exe"):
        get_windows_launcher_stub(target, source_prefixes=(launcher_prefix,))


@pytest.mark.parametrize("missing", ["ownership", "package"])
def test_launcher_win32_fallback(tmp_path: Path, launcher_prefix: Path, missing: str):
    target = tmp_path / "target"
    write_record(target, "python", "win-32")
    if missing == "ownership":
        write_record(launcher_prefix, "conda-launchers", "noarch")
    else:
        (launcher_prefix / "conda-meta/conda-launchers-24.7.1-h0_0.json").unlink()

    path, digest = get_windows_launcher_stub(target, source_prefixes=(launcher_prefix,))

    assert path == str(Path(CONDA_PACKAGE_ROOT, "shell", "cli-32.exe"))
    verify_windows_launcher(path, digest)


def test_launcher_win32_missing_owned_file(tmp_path: Path, launcher_prefix: Path):
    target = tmp_path / "target"
    write_record(target, "python", "win-32")
    (launcher_prefix / WINDOWS_LAUNCHER_STUB_PATH["win-32"]).unlink()

    with pytest.raises(FileNotFoundError, match="cli-32.exe"):
        get_windows_launcher_stub(target, source_prefixes=(launcher_prefix,))


def test_launcher_win32_fallback_during_upgrade(tmp_path: Path, launcher_prefix: Path):
    target = tmp_path / "target"
    write_record(target, "python", "win-32")
    source = tmp_path / "extracted"
    record = write_record(source, "conda-launchers", "noarch")
    package_info = PackageInfo(
        extracted_package_dir=str(source),
        package_tarball_full_path=str(tmp_path / "launchers.conda"),
        channel=Channel("https://example.org"),
        url="https://example.org/noarch/launchers.conda",
        repodata_record=record,
        paths_data=record.paths_data,
    )

    path, digest = get_windows_launcher_stub(
        target, source_prefixes=(launcher_prefix,), source_package_infos=(package_info,)
    )

    assert path == str(Path(CONDA_PACKAGE_ROOT, "shell", "cli-32.exe"))
    verify_windows_launcher(path, digest)


def test_launcher_win32_corrupt_fallback(tmp_path: Path, mocker: MockerFixture):
    target = tmp_path / "target"
    write_record(target, "python", "win-32")
    bundled = tmp_path / "conda"
    (bundled / "shell").mkdir(parents=True)
    (bundled / "shell/cli-32.exe").write_bytes(b"corrupt launcher")
    mocker.patch("conda.core.launchers.CONDA_PACKAGE_ROOT", str(bundled))

    path, digest = get_windows_launcher_stub(target, source_prefixes=())

    with pytest.raises(SafetyError, match="SHA-256 mismatch"):
        verify_windows_launcher(path, digest)


def test_launcher_requires_package_hash(tmp_path: Path, launcher_prefix: Path):
    target = tmp_path / "target"
    write_record(target, "python", "win-64")
    write_record(
        launcher_prefix,
        "conda-launchers",
        "noarch",
        [
            PathDataV1(
                _path=WINDOWS_LAUNCHER_STUB_PATH["win-64"], path_type=PathEnum.hardlink
            )
        ],
    )

    with pytest.raises(SafetyError, match="Missing SHA-256"):
        get_windows_launcher_stub(target, source_prefixes=(launcher_prefix,))


def test_launcher_does_not_search_target_prefix(tmp_path: Path, launcher_prefix: Path):
    write_record(launcher_prefix, "python", "win-64")

    with pytest.raises(FileNotFoundError, match="conda-launchers"):
        get_windows_launcher_stub(launcher_prefix, source_prefixes=())


def test_launcher_rejects_unsupported_target(tmp_path: Path, launcher_prefix: Path):
    target = tmp_path / "target"
    write_record(target, "python", "linux-64")

    with pytest.raises(
        NotImplementedError, match="Windows entry point stub not available"
    ):
        get_windows_launcher_stub(target, source_prefixes=(launcher_prefix,))


def test_launcher_uses_context_before_python_is_installed(
    tmp_path: Path, launcher_prefix: Path, mocker: MockerFixture
):
    mocker.patch("conda.core.launchers.context", subdir="win-arm64")

    path, _ = get_windows_launcher_stub(
        tmp_path / "target", source_prefixes=(launcher_prefix,)
    )

    assert path == str(launcher_prefix / WINDOWS_LAUNCHER_STUB_PATH["win-arm64"])
