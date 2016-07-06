import pytest
from os.path import basename, join
from conda.lock import Locked, LOCKSTR, LOCK_EXTENSION, LockError
from conda.install import on_win

def test_filelock_passes(tmpdir):
    package_name = "conda_file1"
    tmpfile = join(tmpdir.strpath, package_name)
    with Locked(tmpfile) as lock:
        path = basename(lock.lock_path)
        assert tmpdir.join(path).exists() and tmpdir.join(path).isfile()

    # lock should clean up after itself
    assert not tmpdir.join(path).exists()


def test_filelock_locks(tmpdir):

    package_name = "conda_file_2"
    tmpfile = join(tmpdir.strpath, package_name)
    with Locked(tmpfile) as lock1:
        path = basename(lock1.lock_path)
        assert tmpdir.join(path).exists()

        with pytest.raises(LockError) as execinfo:
            with Locked(tmpfile, retries=1) as lock2:
                assert False  # this should never happen
            assert lock2.lock_path == lock1.lock_path

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
    with Locked(tmpfile) as lock1:
        path = basename(lock1.lock_path)
        assert tmpdir.join(path).exists() and tmpdir.join(path).isfile()

        with pytest.raises(LockError) as execinfo:
            with Locked(tmpfile, retries=1) as lock2:
                assert False  # this should never happen
            assert lock2.lock_path == lock1.lock_path

        if not on_win:
            assert "LOCKERROR" in str(execinfo.value)
            assert "conda is already doing something" in str(execinfo.value)
            assert lock1.lock_path in str(execinfo.value)

        assert tmpdir.join(path).exists() and tmpdir.join(path).isfile()

    # lock should clean up after itself
    assert not tmpdir.join(path).exists()


def lock_thread(tmpdir, file_path):
    with Locked(file_path) as lock1:
        path = basename(lock1.lock_path)
        assert tmpdir.join(path).exists() and tmpdir.join(path).isfile()
    assert not tmpdir.join(path).exists()


def test_lock_thread(tmpdir):

    from threading import Thread
    package_name = "conda_file_3"
    tmpfile = join(tmpdir.strpath, package_name)
    t = Thread(target=lock_thread, args=(tmpdir, tmpfile))

    with Locked(tmpfile) as lock1:
        t.start()
        path = basename(lock1.lock_path)
        assert tmpdir.join(path).exists() and tmpdir.join(path).isfile()

    t.join()
    # lock should clean up after itself
    assert not tmpdir.join(path).exists()


def lock_thread_retries(tmpdir, file_path):
    with pytest.raises(LockError) as execinfo:
        with Locked(file_path, retries=0):
            assert False  # should never enter here, since max_tires is 0
        assert  "LOCKERROR" in str(execinfo.value)

def test_lock_retries(tmpdir):

    from threading import Thread
    package_name = "conda_file_3"
    tmpfile = join(tmpdir.strpath, package_name)
    t = Thread(target=lock_thread_retries, args=(tmpdir, tmpfile))

    with Locked(tmpfile) as lock1:
        t.start()
        path = basename(lock1.lock_path)
        assert tmpdir.join(path).exists() and tmpdir.join(path).isfile()

    t.join()
    # lock should clean up after itself
    assert not tmpdir.join(path).exists()
