import pytest
from os.path import basename, join, exists
from conda.lock import FileLock, LOCKSTR, LOCK_EXTENSION, LockError


def test_filelock_passes(tmpdir):
    package_name = "conda_file1"
    tmpfile = join(tmpdir.strpath, package_name)
    with FileLock(tmpfile) as lock:
        path = basename(lock.lock_path)
        assert tmpdir.join(path).exists() and tmpdir.join(path).isfile()

    # lock should clean up after itself
    assert not tmpdir.join(path).exists()



def test_filelock_locks(tmpdir):

    package_name = "conda_file_2"
    tmpfile = join(tmpdir.strpath, package_name)
    with FileLock(tmpfile) as lock1:
        path = basename(lock1.lock_path)
        assert tmpdir.join(path).exists()

        with pytest.raises(LockError) as execinfo:
            with FileLock(tmpfile, max_tries=1) as lock2:
                assert False  # this should never happen
            assert lock2.lock_path == lock1.lock_path
        assert "LOCKERROR" in str(execinfo)
        assert "conda is already doing something" in str(execinfo)

        assert tmpdir.join(path).exists() and tmpdir.join(path).isfile()

    # lock should clean up after itself
    assert not tmpdir.join(path).exists()


def test_filelock_folderlocks(tmpdir):
    import os
    package_name = "conda_file_2"
    tmpfile = join(tmpdir.strpath, package_name)
    os.makedirs(tmpfile)
    with FileLock(tmpfile) as lock1:
        path = basename(lock1.lock_path)
        assert tmpdir.join(path).exists() and tmpdir.join(path).isfile()

        with pytest.raises(LockError) as execinfo:
            with FileLock(tmpfile, max_tries=1) as lock2:
                assert False  # this should never happen
            assert lock2.lock_path == lock1.lock_path
        assert "LOCKERROR" in str(execinfo)
        assert "conda is already doing something" in str(execinfo)
        assert lock1.lock_path in str(execinfo), "haha {0}".format(str(execinfo))

        assert tmpdir.join(path).exists() and tmpdir.join(path).isfile()

    # lock should clean up after itself
    assert not tmpdir.join(path).exists()


def lock_thread(tmpdir, file_path):
    with FileLock(file_path) as lock1:
        path = basename(lock1.lock_path)
        assert tmpdir.join(path).exists() and tmpdir.join(path).isfile()
    assert not tmpdir.join(path).exists()

def test_lock_thread(tmpdir):

    from threading import Thread
    package_name = "conda_file_3"
    tmpfile = join(tmpdir.strpath, package_name)
    t = Thread(target=lock_thread, args=(tmpdir, tmpfile))

    with FileLock(tmpfile) as lock1:
        t.start()
        path = basename(lock1.lock_path)
        assert tmpdir.join(path).exists() and tmpdir.join(path).isfile()

    t.join()
    # lock should clean up after itself
    assert not tmpdir.join(path).exists()



def lock_thread_retries(tmpdir, file_path):
    with FileLock(file_path, max_tries=0) as lock1:
        assert  False # should never enter here, since max_tires is 0


def test_lock_retries(tmpdir):

    from threading import Thread
    package_name = "conda_file_3"
    tmpfile = join(tmpdir.strpath, package_name)
    t = Thread(target=lock_thread_retries, args=(tmpdir, tmpfile))

    with FileLock(tmpfile) as lock1:
        t.start()
        path = basename(lock1.lock_path)
        assert tmpdir.join(path).exists() and tmpdir.join(path).isfile()

    t.join()
    # lock should clean up after itself
    assert not tmpdir.join(path).exists()