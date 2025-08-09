# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

import builtins
import sys

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


def test_locking_not_supported(monkeypatch: MonkeyPatch, tmp_path):
    tmp_file = tmp_path / "testfile"
    tmp_file.write_bytes(b"test")
    monkeypatch.delitem(sys.modules, "fcntl", raising=False)
    monkeypatch.delitem(sys.modules, "msvcrt", raising=False)
    monkeypatch.setattr(builtins, "__import__", monkey_import_ImportError)

    with pytest.raises(ImportError):
        lock(tmp_file)


def test_LockError_raised(mocker: MockerFixture, monkeypatch: MonkeyPatch, tmp_path):
    tmp_file = tmp_path / "testfile"
    tmp_file.write_bytes(b"test")

    mocker.patch("msvcrt.locking" if on_win else "fcntl.lockf", side_effect=OSError)
    with pytest.raises(LockError):
        with tmp_file.open("r+b") as f:
            with lock(f, lock_attempts=1):
                pass


def test_lock_acquired_success(mocker: MockerFixture, capsys: CaptureFixture, tmp_path):
    tmp_file = tmp_path / "testfile"
    tmp_file.write_bytes(b"test")

    mocker.patch("conda.gateways.disk.lock.lock", return_value=_lock_impl)

    with tmp_file.open("r+b") as f:
        with lock(f):
            pass
    stdout, _ = capsys.readouterr()
    assert "Failed to acquire lock." not in stdout


def lock_wrapper(path):
    import time

    try:
        with path.open("r+b") as fd:
            with lock(fd, lock_attempts=1):
                time.sleep(5)
            return "success"
    except LockError:
        return "lock_error"


def test_double_locking_fails(mocker: MockerFixture, tmp_path):
    from multiprocessing import Pool

    tmp_file = tmp_path / "testfile"
    tmp_file.touch()

    with Pool(processes=2) as p:
        result = p.map(lock_wrapper, [tmp_file, tmp_file])
        assert "success" in result
        assert "lock_error" in result
