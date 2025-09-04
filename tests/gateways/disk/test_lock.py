# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause


from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from conda.common.compat import on_win
from conda.exceptions import LockError
from conda.gateways.disk.lock import _lock_impl


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
