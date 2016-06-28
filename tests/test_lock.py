import pytest
from os.path import basename, join
from conda.lock import FileLock, LOCKSTR, LOCKFN, LockError


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
            with FileLock(tmpfile, retries=1) as lock2:
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
            with FileLock(tmpfile, retries=1) as lock2:
                assert False  # this should never happen
            assert lock2.lock_path == lock1.lock_path
        assert "LOCKERROR" in str(execinfo)
        assert "conda is already doing something" in str(execinfo)

        assert tmpdir.join(path).exists() and tmpdir.join(path).isfile()

    # lock should clean up after itself
    assert not tmpdir.join(path).exists()

