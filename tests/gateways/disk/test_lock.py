# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause


from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from conda.common.compat import on_win
from conda.exceptions import LockError
from conda.gateways.disk.lock import _lock_impl, lock


def test_LockError_raised(mocker: MockerFixture, tmp_path: Path):
    tmp_file = tmp_path / "testfile"
    tmp_file.touch()

    mocker.patch("msvcrt.locking" if on_win else "fcntl.lockf", side_effect=OSError)
    with pytest.raises(LockError):
        with tmp_file.open("r+b") as f:
            with _lock_impl(f, lock_attempts=1):
                pass


def test_lock_acquired_success(tmp_path: Path):
    tmp_file = tmp_path / "testfile"
    tmp_file.touch()

    with tmp_file.open("r+b") as f:
        with _lock_impl(f, lock_attempts=1):
            # Because we are able to use lock(), that means lock acquisition succeeded.
            pass


def lock_wrapper(path):
    import time

    try:
        with path.open("r+b") as fd:
            with _lock_impl(fd, lock_attempts=1):
                time.sleep(12 if on_win else 1)
            return "success"
    except LockError:
        return "lock_error"


def test_double_locking_fails(mocker: MockerFixture, tmp_path: Path):
    from multiprocessing import Pool

    tmp_file = tmp_path / "testfile"
    tmp_file.touch()

    with Pool(processes=2) as p:
        result = p.map(lock_wrapper, [tmp_file, tmp_file])
        assert "success" in result
        assert "lock_error" in result


def test_required_lock_ignores_no_lock(mocker: MockerFixture, tmp_path: Path):
    mocker.patch("conda.gateways.disk.lock.context.no_lock", True)
    implementation = mocker.patch("conda.gateways.disk.lock._lock_impl")
    with (tmp_path / "lock").open("a+") as fd:
        with lock(fd, required=True):
            pass
        implementation.assert_called_once_with(fd, 10)


def test_required_lock_rejects_unavailable_locking(
    mocker: MockerFixture, tmp_path: Path
):
    mocker.patch("conda.gateways.disk.lock.locking_supported", return_value=False)
    with (tmp_path / "lock").open("a+") as fd:
        with pytest.raises(LockError, match="File locking is not available"):
            with lock(fd, required=True):
                pytest.fail("A required lock must not silently succeed")


def _required_lock_worker(path, connection):
    with path.open("a+") as fd:
        try:
            with lock(fd, lock_attempts=1, required=True):
                connection.send("unexpectedly acquired")
        except LockError:
            connection.send("blocked")
        connection.recv()
        with lock(fd, lock_attempts=1, required=True):
            connection.send("acquired")
    connection.close()


def test_required_lock_coordinates_processes(tmp_path: Path):
    from multiprocessing import get_context

    multiprocessing = get_context("spawn" if on_win else "fork")
    parent, child = multiprocessing.Pipe()
    path = tmp_path / "lock"
    process = multiprocessing.Process(target=_required_lock_worker, args=(path, child))
    try:
        with path.open("a+") as fd, lock(fd, required=True):
            process.start()
            assert parent.poll(20)
            assert parent.recv() == "blocked"
        parent.send("retry")
        assert parent.poll(20)
        assert parent.recv() == "acquired"
        process.join(10)
        assert process.exitcode == 0
    finally:
        if process.is_alive():
            process.terminate()
            process.join(10)
        parent.close()
        child.close()
