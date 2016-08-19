import pytest
from os.path import basename, join
from conda.lock import FileLock, LOCKSTR, LOCK_EXTENSION, LockError
from conda.install import on_win

def test_filelock_passes(tmpdir):
    package_name = "conda_file1"
    tmpfile = join(tmpdir.strpath, package_name)
    with FileLock(tmpfile) as lock:
        path = basename(lock.lock_file_path)
        assert tmpdir.join(path).exists() and tmpdir.join(path).isfile()

    # lock should clean up after itself
    assert not tmpdir.join(path).exists()


def test_filelock_locks(tmpdir):

    package_name = "conda_file_2"
    tmpfile = join(tmpdir.strpath, package_name)
    with FileLock(tmpfile) as lock1:
        path = basename(lock1.lock_file_path)
        assert tmpdir.join(path).exists()

        with pytest.raises(LockError) as execinfo:
            with FileLock(tmpfile, retries=1) as lock2:
                assert False  # this should never happen
            assert lock2.path_to_lock == lock1.path_to_lock

        if not on_win:
            assert "LOCKERROR" in str(execinfo.value)
            assert "conda is already doing something" in str(execinfo.value)
        assert tmpdir.join(path).exists() and tmpdir.join(path).isfile()

    # lock should clean up after itself
    assert not tmpdir.join(path).exists()


def test_filelock_folderlocks(tmpdir):
    import os
    package_name = "conda_file_2"
    tmpfile = join(tmpdir.strpath, package_name)
    os.makedirs(tmpfile)
    with FileLock(tmpfile) as lock1:
        path = basename(lock1.lock_file_path)
        assert tmpdir.join(path).exists() and tmpdir.join(path).isfile()

        with pytest.raises(LockError) as execinfo:
            with FileLock(tmpfile, retries=1) as lock2:
                assert False  # this should never happen
            assert lock2.path_to_lock == lock1.path_to_lock

        if not on_win:
            assert "LOCKERROR" in str(execinfo.value)
            assert "conda is already doing something" in str(execinfo.value)
            assert lock1.path_to_lock in str(execinfo.value)

        assert tmpdir.join(path).exists() and tmpdir.join(path).isfile()

    # lock should clean up after itself
    assert not tmpdir.join(path).exists()


def lock_thread(tmpdir, file_path):
    with FileLock(file_path) as lock1:
        path = basename(lock1.lock_file_path)
        assert tmpdir.join(path).exists() and tmpdir.join(path).isfile()
    assert not tmpdir.join(path).exists()


def test_lock_thread(tmpdir):

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


def lock_thread_retries(tmpdir, file_path):
    with pytest.raises(LockError) as execinfo:
        with FileLock(file_path, retries=0):
            assert False  # should never enter here, since max_tires is 0
        assert  "LOCKERROR" in str(execinfo.value)

def test_lock_retries(tmpdir):

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

def test_delete_lock(tmpdir):
    from .test_create import make_temp_env
    from conda.base.context import context
    with make_temp_env() as prefix:
        assert False, context.pkgs_dirs