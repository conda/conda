# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import os
from pathlib import Path

import pytest
from pytest import MonkeyPatch

from conda.cli.find_commands import find_commands, find_executable
from conda.common.compat import on_win


@pytest.fixture
def faux_path(tmp_path: Path, monkeypatch: MonkeyPatch) -> Path:
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

    yield tmp_path

    if not on_win:
        # undo read-only for clean removal
        permission.chmod(permission.stat().st_mode | 0o444)


def test_find_executable(faux_path: Path):
    assert (faux_path / "bin" / "conda-bin").samefile(find_executable("conda-bin"))
    if on_win:
        assert (faux_path / "bat" / "conda-bat.bat").samefile(
            find_executable("conda-bat")
        )
        assert (faux_path / "exe" / "conda-exe.exe").samefile(
            find_executable("conda-exe")
        )


def test_find_commands(faux_path: Path):
    find_commands.cache_clear()
    if on_win:
        assert {"bin", "bat", "exe"}.issubset(find_commands())
    else:
        assert {"bin"}.issubset(find_commands())
