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


@pytest.mark.skipif(not on_win, reason="windows-specific test")
def test_LockError_raised_windows(
    mocker: MockerFixture, monkeypatch: MonkeyPatch, tmp_path
):
    tmp_file = tmp_path / "testfile"
    tmp_file.write_bytes(b"test")
    mocker.patch("msvcrt.locking", side_effect=OSError)
    monkeypatch.setattr("conda.gateways.disk.lock.LOCK_ATTEMPTS", 1)
    with pytest.raises(LockError):
        with tmp_file.open("r+b") as f:
            with lock(f):
                pass


@pytest.mark.skipif(on_win, reason="non windows test")
def test_LockError_raised_not_windows(
    mocker: MockerFixture, monkeypatch: MonkeyPatch, tmp_path
):
    tmp_file = tmp_path / "testfile"
    tmp_file.write_bytes(b"test")

    mocker.patch("fcntl.lockf", side_effect=OSError)
    monkeypatch.setattr("conda.gateways.disk.lock.LOCK_ATTEMPTS", 1)
    with pytest.raises(LockError):
        with tmp_file.open("r+b") as f:
            with lock(f):
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


def lock_wrapper(path, q):
    import time

    try:
        with path.open("r+b") as fd:
            with lock(fd):
                # sleep needs to be long enough to keep p1 process running while p2 starts
                time.sleep(12)
            q.put("success")
    except LockError:
        q.put("lock_error")


def test_double_locking_fails(mocker: MockerFixture, capsys: CaptureFixture, tmp_path):
    from multiprocessing import Process, Queue

    tmp_file = tmp_path / "testfile"
    tmp_file.write_bytes(b"test")

    q = Queue()

    p1 = Process(target=lock_wrapper, args=(tmp_file, q))
    p2 = Process(target=lock_wrapper, args=(tmp_file, q))

    p1.start()
    p2.start()
    p1.join()
    p2.join()

    result = [q.get() for _ in range(2)]

    assert "success" in result
    assert "lock_error" in result
