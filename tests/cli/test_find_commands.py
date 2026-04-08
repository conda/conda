# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import os
from typing import TYPE_CHECKING

import pytest

from conda.common.compat import on_win

with pytest.deprecated_call():
    from conda.cli.find_commands import find_commands, find_executable

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from pytest import MonkeyPatch


@pytest.fixture
def faux_path(tmp_path: Path, monkeypatch: MonkeyPatch) -> Iterator[Path]:
    if not on_win:
        # make a read-only location, none of these should show up in the tests
        permission = tmp_path / "permission"
        permission.mkdir(mode=0o333, exist_ok=True)
        (permission / "conda-permission").touch()
        (permission / "conda-permission.bat").touch()
        (permission / "conda-permission.exe").touch()
        monkeypatch.setenv("PATH", str(permission), prepend=os.pathsep)

    # missing directory
    missing_dir = tmp_path / "missing-directory"
    monkeypatch.setenv("PATH", str(missing_dir), prepend=os.pathsep)

    # not directory
    not_dir = tmp_path / "not-directory"
    not_dir.touch()
    monkeypatch.setenv("PATH", str(not_dir), prepend=os.pathsep)

    # incorrect syntax
    not_dir_2 = " C:\\path-may-not-start-with-space"
    monkeypatch.setenv("PATH", str(not_dir_2), prepend=os.pathsep)

    # bad executables
    bad = tmp_path / "bad"
    bad.mkdir(exist_ok=True)
    (bad / "non-conda-bad").touch()
    (bad / "non-conda-bad.bat").touch()
    (bad / "non-conda-bad.exe").touch()
    monkeypatch.setenv("PATH", str(bad), prepend=os.pathsep)

    # good executables
    bin_ = tmp_path / "bin"
    bin_.mkdir(exist_ok=True)
    (bin_ / "conda-bin").touch()
    monkeypatch.setenv("PATH", str(bin_), prepend=os.pathsep)

    bat = tmp_path / "bat"
    bat.mkdir(exist_ok=True)
    (bat / "conda-bat.bat").touch()
    monkeypatch.setenv("PATH", str(bat), prepend=os.pathsep)

    exe = tmp_path / "exe"
    exe.mkdir(exist_ok=True)
    (exe / "conda-exe.exe").touch()
    monkeypatch.setenv("PATH", str(exe), prepend=os.pathsep)

    find_commands.cache_clear()

    yield tmp_path

    if not on_win:
        # undo read-only for clean removal
        permission.chmod(permission.stat().st_mode | 0o444)

    find_commands.cache_clear()


@pytest.mark.parametrize(
    "executable,path",
    [
        ("conda-bin", "bin/conda-bin"),
        pytest.param(
            "conda-bat",
            "bat/conda-bat.bat",
            marks=pytest.mark.skipif(not on_win, reason="Windows-specific test"),
        ),
        pytest.param(
            "conda-exe",
            "exe/conda-exe.exe",
            marks=pytest.mark.skipif(not on_win, reason="Windows-specific test"),
        ),
    ],
)
def test_find_executable(faux_path: Path, executable: str, path: str):
    with pytest.deprecated_call():
        assert (faux_path / path).samefile(find_executable(executable))


@pytest.mark.parametrize(
    "subset",
    [
        pytest.param(
            {"bin", "bat", "exe"},
            marks=pytest.mark.skipif(not on_win, reason="Windows-specific test"),
        ),
        pytest.param(
            {"bin"}, marks=pytest.mark.skipif(on_win, reason="Windows-specific test")
        ),
    ],
)
def test_find_commands(faux_path: Path, subset: set[str]):
    with pytest.deprecated_call():
        assert subset.issubset(find_commands())
