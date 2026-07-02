# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from conda.common.serialize import json
from conda.core import launchers
from conda.models.records import PrefixRecord

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_mock import MockerFixture


def test_get_conda_launchers_file_from_package_record(tmp_path: Path):
    launcher_short_path = "Scripts/cli-64.exe"
    launcher_path = tmp_path / launcher_short_path
    launcher_path.parent.mkdir(parents=True)
    launcher_path.write_bytes(b"launcher")
    write_prefix_record(tmp_path, files=[launcher_short_path])

    assert launchers._get_conda_launchers_file(tmp_path, launcher_short_path) == str(
        launcher_path
    )


def test_get_conda_launchers_file_ignores_unowned_file(tmp_path: Path):
    launcher_short_path = "Scripts/cli-64.exe"
    launcher_path = tmp_path / launcher_short_path
    launcher_path.parent.mkdir(parents=True)
    launcher_path.write_bytes(b"launcher")
    write_prefix_record(tmp_path, files=["Scripts/cli-32.exe"])

    assert launchers._get_conda_launchers_file(tmp_path, launcher_short_path) is None


def test_get_windows_launcher_stub_path_prefers_conda_launchers(tmp_path: Path):
    launcher_short_path = "Scripts/cli-arm64.exe"
    launcher_path = tmp_path / launcher_short_path
    launcher_path.parent.mkdir(parents=True)
    launcher_path.write_bytes(b"launcher")
    write_prefix_record(tmp_path, files=[launcher_short_path])

    assert launchers.get_windows_launcher_stub_path(
        "win-arm64", prefixes=(tmp_path,)
    ) == str(launcher_path)


def test_get_windows_launcher_stub_path_uses_conda_launchers_api(
    tmp_path: Path, mocker: MockerFixture
):
    launcher_short_path = "Scripts/cli-64.exe"
    launcher_path = tmp_path / launcher_short_path
    launcher_path.parent.mkdir(parents=True)
    launcher_path.write_bytes(b"launcher")
    write_prefix_record(tmp_path, files=[launcher_short_path])
    get_launcher_short_path = mocker.patch(
        "conda.core.launchers._conda_launchers_get_launcher_short_path",
        return_value=launcher_short_path,
    )

    assert launchers.get_windows_launcher_stub_path(
        "win-64", prefixes=(tmp_path,)
    ) == str(launcher_path)

    get_launcher_short_path.assert_called_once_with("win-64")


def test_get_windows_launcher_stub_path_falls_back_to_bundled(mocker: MockerFixture):
    mocker.patch("conda.core.launchers._get_conda_launchers_file", return_value=None)

    assert launchers.get_windows_launcher_stub_path("win-64").endswith(
        "conda/shell/cli-64.exe"
    )


def test_get_windows_launcher_stub_path_reports_missing_conda_launchers_only_stub(
    mocker: MockerFixture,
):
    mocker.patch("conda.core.launchers._get_conda_launchers_file", return_value=None)
    mocker.patch.dict(launchers.WINDOWS_LAUNCHER_STUB_PATH, {}, clear=True)
    mocker.patch("conda.core.launchers._conda_launchers_get_launcher_short_path", None)

    with pytest.raises(FileNotFoundError, match="no bundled fallback"):
        launchers.get_windows_launcher_stub_path("win-arm64")


def test_get_windows_launcher_stub_path_rejects_unsupported_subdir():
    with pytest.raises(
        NotImplementedError, match="Windows entry point stub not available"
    ):
        launchers.get_windows_launcher_stub_path("linux-64")


def write_prefix_record(prefix: Path, files: list[str]) -> None:
    conda_meta = prefix / "conda-meta"
    conda_meta.mkdir()
    record = PrefixRecord(
        name="conda-launchers",
        version="24.7.1",
        build="h0_5",
        build_number=5,
        subdir="win-64",
        files=files,
    )
    (conda_meta / "conda-launchers-24.7.1-h0_5.json").write_text(
        json.dumps(record.dump()),
        encoding="utf-8",
    )
