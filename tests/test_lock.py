# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

import pytest
from conda.lock import DirectoryLock, FileLock, LockError
from os.path import basename, exists, isfile, join


def test_filelock_passes(tmpdir):
    """
        Normal test on file lock
    """
    package_name = "conda_file1"
    tmpfile = join(tmpdir.strpath, package_name)
    with FileLock(tmpfile) as lock:
        path = basename(lock.lock_file_path)
        assert tmpdir.join(path).exists() and tmpdir.join(path).isfile()

    # lock should clean up after itself
    assert not tmpdir.join(path).exists()


def test_filelock_locks(tmpdir):
    """
        Test on file lock, multiple lock on same file
        Lock error should raised
    """
    package_name = "conda_file_2"
    tmpfile = join(tmpdir.strpath, package_name)
    with FileLock(tmpfile) as lock1:
        path = basename(lock1.lock_file_path)
        assert tmpdir.join(path).exists()

        with pytest.raises(LockError) as execinfo:
            with FileLock(tmpfile, retries=1) as lock2:
                assert False  # this should never happen
            assert lock2.path_to_lock == lock1.path_to_lock

        assert tmpdir.join(path).exists() and tmpdir.join(path).isfile()

    # lock should clean up after itself
    assert not tmpdir.join(path).exists()


def test_folder_locks(tmpdir):
    """
        Test on Directory lock
    """
    package_name = "dir_1"
    tmpfile = join(tmpdir.strpath, package_name)
    with DirectoryLock(tmpfile) as lock1:

        assert exists(lock1.lock_file_path) and isfile(lock1.lock_file_path)

        with pytest.raises(LockError) as execinfo:
            with DirectoryLock(tmpfile, retries=1) as lock2:
                assert False  # this should never happen

        assert exists(lock1.lock_file_path) and isfile(lock1.lock_file_path)

    # lock should clean up after itself
    assert not exists(lock1.lock_file_path)


def test_lock_thread(tmpdir):
    """
        2 thread want to lock a file
        One thread will have LockError Raised
    """
    def lock_thread(tmpdir, file_path):
        with FileLock(file_path) as lock1:
            path = basename(lock1.lock_file_path)
            assert tmpdir.join(path).exists() and tmpdir.join(path).isfile()
        assert not tmpdir.join(path).exists()

    from threading import Thread
    package_name = "conda_file_3"
    tmpfile = join(tmpdir.strpath, package_name)
    t = Thread(target=lock_thread, args=(tmpdir, tmpfile))

    with FileLock(tmpfile) as lock1:
        t.start()
        path = basename(lock1.lock_file_path)
        assert tmpdir.join(path).exists() and tmpdir.join(path).isfile()

    t.join()
    # lock should clean up after itself
    assert not tmpdir.join(path).exists()


def test_lock_retries(tmpdir):
    """
        2 thread want to lock a same file
        Lock has zero retries
        One thread will have LockError raised
    """
    def lock_thread_retries(tmpdir, file_path):
        with pytest.raises(LockError) as execinfo:
            with FileLock(file_path, retries=0):
                assert False  # should never enter here, since max_tries is 0
            assert "LOCKERROR" in str(execinfo.value)

    from threading import Thread
    package_name = "conda_file_3"
    tmpfile = join(tmpdir.strpath, package_name)
    t = Thread(target=lock_thread_retries, args=(tmpdir, tmpfile))

    with FileLock(tmpfile) as lock1:
        t.start()
        path = basename(lock1.lock_file_path)
        assert tmpdir.join(path).exists() and tmpdir.join(path).isfile()

    t.join()
    # lock should clean up after itself
    assert not tmpdir.join(path).exists()


def test_permission_file():
    """
        Test when lock cannot be created due to permission
        Make sure no exception raised
    """
    from conda.auxlib.compat import Utf8NamedTemporaryFile
    from conda.common.compat import text_type
    with Utf8NamedTemporaryFile(mode='r') as f:
        if not isinstance(f.name, text_type):
            return
        with FileLock(f.name) as lock:

            path = basename(lock.lock_file_path)
            assert not exists(join(f.name, path))
