# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest

from conda.common.serialize import json
from conda.core import launchers
from conda.models.records import PrefixRecord

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_mock import MockerFixture


def test_get_windows_launcher_stub_path_uses_package_record(tmp_path: Path):
    pytest.importorskip("conda_launchers")
    launcher_short_path = "Scripts/cli-64.exe"
    launcher_path = tmp_path / launcher_short_path
    launcher_path.parent.mkdir(parents=True)
    launcher_path.write_bytes(b"launcher")
    write_prefix_record(tmp_path, files=[launcher_short_path])

    assert launchers.get_windows_launcher_stub_path(
        "win-64", source_prefixes=(tmp_path,)
    ) == str(launcher_path)


def test_get_windows_launcher_stub_path_ignores_unowned_file(tmp_path: Path):
    pytest.importorskip("conda_launchers")
    launcher_short_path = "Scripts/cli-64.exe"
    launcher_path = tmp_path / launcher_short_path
    launcher_path.parent.mkdir(parents=True)
    launcher_path.write_bytes(b"launcher")
    write_prefix_record(tmp_path, files=["Scripts/cli-32.exe"])

    with pytest.raises(FileNotFoundError, match="Scripts/cli-64.exe"):
        launchers.get_windows_launcher_stub_path("win-64", source_prefixes=(tmp_path,))


def test_get_windows_launcher_stub_path_prefers_conda_launchers(tmp_path: Path):
    pytest.importorskip("conda_launchers")
    launcher_short_path = "Scripts/cli-arm64.exe"
    launcher_path = tmp_path / launcher_short_path
    launcher_path.parent.mkdir(parents=True)
    launcher_path.write_bytes(b"launcher")
    write_prefix_record(tmp_path, files=[launcher_short_path])

    assert launchers.get_windows_launcher_stub_path(
        "win-arm64", source_prefixes=(tmp_path,)
    ) == str(launcher_path)


def test_get_windows_launcher_stub_path_uses_linked_package(
    tmp_path: Path, mocker: MockerFixture
):
    pytest.importorskip("conda_launchers")
    launcher_short_path = "Scripts/cli-64.exe"
    extracted_package_dir = tmp_path / "conda-launchers-26.7.0-h0_0"
    launcher_path = extracted_package_dir / launcher_short_path
    launcher_path.parent.mkdir(parents=True)
    launcher_path.write_bytes(b"launcher")
    package_info = SimpleNamespace(
        extracted_package_dir=str(extracted_package_dir),
        repodata_record=SimpleNamespace(name="conda-launchers"),
        paths_data=SimpleNamespace(paths=(SimpleNamespace(path=launcher_short_path),)),
    )
    prefix_data = mocker.patch("conda.core.launchers.PrefixData")

    assert launchers.get_windows_launcher_stub_path(
        "win-64",
        source_prefixes=("missing-prefix",),
        source_package_infos=(package_info,),
    ) == str(launcher_path)

    prefix_data.assert_not_called()


def test_get_windows_launcher_stub_path_uses_conda_launchers_api(
    tmp_path: Path, mocker: MockerFixture
):
    conda_launchers = pytest.importorskip("conda_launchers")
    launcher_short_path = "Scripts/cli-64.exe"
    launcher_path = tmp_path / launcher_short_path
    launcher_path.parent.mkdir(parents=True)
    launcher_path.write_bytes(b"launcher")
    write_prefix_record(tmp_path, files=[launcher_short_path])
    get_launcher_short_path = mocker.spy(conda_launchers, "get_launcher_short_path")

    assert launchers.get_windows_launcher_stub_path(
        "win-64", source_prefixes=(tmp_path,)
    ) == str(launcher_path)

    get_launcher_short_path.assert_called_once_with("win-64")


def test_get_windows_launcher_stub_path_reports_missing_conda_launchers_package(
    mocker: MockerFixture,
):
    pytest.importorskip("conda_launchers")
    mocker.patch("conda.core.launchers.PrefixData", side_effect=OSError)

    with pytest.raises(FileNotFoundError, match="conda-launchers"):
        launchers.get_windows_launcher_stub_path(
            "win-arm64", source_prefixes=("prefix",)
        )


def test_get_windows_launcher_stub_path_rejects_unsupported_subdir():
    pytest.importorskip("conda_launchers")
    with pytest.raises(
        NotImplementedError, match="Windows entry point stub not available"
    ):
        launchers.get_windows_launcher_stub_path("linux-64", source_prefixes=())


def write_prefix_record(prefix: Path, files: list[str]) -> None:
    conda_meta = prefix / "conda-meta"
    conda_meta.mkdir()
    record = PrefixRecord(
        name="conda-launchers",
        version="26.7.0",
        build="h0_0",
        build_number=0,
        subdir="win-64",
        files=files,
    )
    (conda_meta / "conda-launchers-26.7.0-h0_0.json").write_text(
        json.dumps(record.dump()),
        encoding="utf-8",
    )
