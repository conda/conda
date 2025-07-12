# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

import builtins
import sys
from tempfile import TemporaryFile

import pytest
from pytest import CaptureFixture, MonkeyPatch
from pytest_mock import MockerFixture

from conda.gateways.disk.lock import _lock_impl, _lock_noop, lock


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


def test_lock_acquired(mocker: MockerFixture, capsys: CaptureFixture):
    tmp_file = TemporaryFile()
    print(tmp_file)
    assert _lock_impl != _lock_noop
    mocker.patch("conda.gateways.disk.lock.lock", return_value=_lock_impl)
    with _lock_impl(tmp_file):
        with _lock_impl(tmp_file):
            pass
    stdout, stderr = capsys.readouterr()
    assert "Failed to acquire lock." in stdout


def test_lock_not_acquired(): ...


def test_lock_released(): ...


def test_lock_not_released(): ...


def test_lock_again(): ...
