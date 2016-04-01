import os.path
import pytest

from conda.lock import Locked, LockError


def test_lock_passes(tmpdir):
    with Locked(tmpdir.strpath) as lock:
        path = os.path.basename(lock.lock_path)
        assert tmpdir.join(path).exists() and tmpdir.join(path).isdir()

    # lock should clean up after itself
    assert not tmpdir.join(path).exists()
    assert not tmpdir.exists()

def test_lock_locks(tmpdir):
    with Locked(tmpdir.strpath) as lock1:
        path = os.path.basename(lock1.lock_path)
        assert tmpdir.join(path).exists() and tmpdir.join(path).isdir()

        with pytest.raises(LockError) as execinfo:
            with Locked(tmpdir.strpath, retries=1) as lock2:
                assert False  # this should never happen
            assert lock2.lock_path == lock1.lock_path
        assert "LOCKERROR" in str(execinfo)
        assert "conda is already doing something" in str(execinfo)

        assert tmpdir.join(path).exists() and tmpdir.join(path).isdir()

    # lock should clean up after itself
    assert not tmpdir.join(path).exists()
    assert not tmpdir.exists()
