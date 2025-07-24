# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

import builtins
import sys
from tempfile import TemporaryFile

import pytest
from pytest import CaptureFixture, MonkeyPatch
from pytest_mock import MockerFixture

from conda.common.compat import on_win
from conda.exceptions import LockError
from conda.gateways.disk.lock import (
    _lock_impl,
    lock,
)


# A function mocking the signature of the real import method in the builtein module
def monkey_import_ImportError(name, globals=None, locals=None, fromlist=(), level=0):
    if name in ("msvcrt", "fcntl"):
        raise ImportError("Mocked import error")


def test_locking_not_supported(monkeypatch: MonkeyPatch):
    tmp_file = TemporaryFile()
    monkeypatch.delitem(sys.modules, "fcntl", raising=False)
    monkeypatch.delitem(sys.modules, "msvcrt", raising=False)
    monkeypatch.setattr(builtins, "__import__", monkey_import_ImportError)

    with pytest.raises(ImportError):
        lock(tmp_file)


@pytest.mark.skipif(not on_win, reason="windows-specific test")
def test_LockError_raised_windows(mocker: MockerFixture, monkeypatch: MonkeyPatch):
    tmp_file = TemporaryFile()
    mocker.patch("msvcrt.locking", side_effect=OSError)
    monkeypatch.setattr("conda.gateways.disk.lock.LOCK_ATTEMPTS", 1)
    with pytest.raises(LockError):
        with lock(tmp_file):
            pass


def test_LockError_raised_not_windows(mocker: MockerFixture, monkeypatch: MonkeyPatch):
    tmp_file = TemporaryFile()
    mocker.patch("fcntl.lockf", side_effect=OSError)
    monkeypatch.setattr("conda.gateways.disk.lock.LOCK_ATTEMPTS", 1)
    with pytest.raises(LockError):
        with lock(tmp_file):
            pass


def test_lock_acquired_success(mocker: MockerFixture, capsys: CaptureFixture):
    tmp_file = TemporaryFile()
    mocker.patch("conda.gateways.disk.lock.lock", return_value=_lock_impl)
    with lock(tmp_file):
        pass
    stdout, stderr = capsys.readouterr()
    assert "Failed to acquire lock." not in stdout


def test_lock_released(): ...


def test_lock_not_released(): ...
