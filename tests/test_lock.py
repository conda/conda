import pytest
import os
from os.path import basename, join, isfile
from conda.lock import Locked, LockError
from conda.install import on_win, rm_rf

def touch(file_name, times=None):
    """ Touch function like touch in Unix shell
    :param file_name: the name of file
    :param times: the access and modified time
    Examples:
        touch("hello_world.py")
    """
    with open(file_name, 'a'):
        os.utime(file_name, times)

def test_filelock_passes(tmpdir):
    package_name = "conda_file1"
    tmpfile = join(tmpdir.strpath, package_name)
    touch(tmpfile)
    with Locked(tmpfile) as lock:
        path = basename(lock.lock_file)
        assert tmpdir.join(path).exists() and tmpdir.join(path).isfile()

    rm_rf(tmpfile)
    assert not tmpdir.join(path).exists()


def test_filelock_locks(tmpdir):

    package_name = "conda_file_2"
    tmpfile = join(tmpdir.strpath, package_name)
    touch(tmpfile)
    with Locked(tmpfile) as lock1:
        path = basename(lock1.lock_file)
        assert tmpdir.join(path).exists()

        with pytest.raises(LockError) as execinfo:
            with Locked(tmpfile) as lock2:
                assert False  # this should never happen
            assert lock2.lock_file == lock1.lock_file

        if not on_win:
            assert "LOCKERROR" in str(execinfo.value)
            assert "conda is already doing something" in str(execinfo.value)

    rm_rf(tmpfile)
    assert not tmpdir.join(path).exists()


def test_filelock_folderlocks(tmpdir):
    import os
    package_name = "conda_file_2"
    tmpfile = join(tmpdir.strpath, package_name)
    os.makedirs(tmpfile)
    with Locked(tmpfile) as lock1:
        path = lock1.lock_file
        assert isfile(path)

        with pytest.raises(LockError) as execinfo:
            with Locked(tmpfile) as lock2:
                assert False  # this should never happen
            assert lock2.lock_file == lock1.lock_file

        if not on_win:
            assert "LOCKERROR" in str(execinfo.value)
            assert "conda is already doing something" in str(execinfo.value)
            assert lock1.lock_file in str(execinfo.value)

    rm_rf(tmpfile)
    assert not tmpdir.join(path).exists()


def lock_thread(tmpdir, file_path):
    with Locked(file_path) as lock1:
        path = basename(lock1.lock_file)
        assert tmpdir.join(path).exists() and tmpdir.join(path).isfile()


def test_lock_thread(tmpdir):

    from threading import Thread
    package_name = "conda_file_3"
    tmpfile = join(tmpdir.strpath, package_name)
    touch(tmpfile)
    t = Thread(target=lock_thread, args=(tmpdir, tmpfile))

    with Locked(tmpfile) as lock1:
        t.start()
        path = basename(lock1.lock_file)
        assert tmpdir.join(path).exists() and tmpdir.join(path).isfile()

    t.join()
    rm_rf(tmpfile)
    assert not tmpdir.join(path).exists()


