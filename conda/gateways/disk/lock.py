# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
Record locking to manage potential repodata / repodata metadata file contention
between conda processes. Try to acquire a lock on a single byte in the metadat
file; modify both files; then release the lock.
"""

import time
import warnings
from contextlib import contextmanager

from ...base.context import context
from ...exceptions import LockError

LOCK_BYTE = 21  # mamba interop
LOCK_ATTEMPTS = 10
LOCK_SLEEP = 1


@contextmanager
def _lock_noop(fd, lock_attempts):
    """When locking is not available."""
    yield


try:  # pragma: no cover
    import msvcrt

    @contextmanager
    def _lock_impl(fd, lock_attempts):  # type: ignore
        tell = fd.tell()
        fd.seek(LOCK_BYTE)
        try:
            msvcrt.locking(fd.fileno(), msvcrt.LK_LOCK, 1)  # type: ignore
        except OSError:
            raise LockError("Failed to acquire lock.")
        else:
            try:
                fd.seek(tell)
                yield
            finally:
                fd.seek(LOCK_BYTE)
                try:
                    msvcrt.locking(fd.fileno(), msvcrt.LK_UNLCK, 1)  # type: ignore
                except OSError:
                    raise LockError("Failed to release lock.")


except ImportError:
    try:
        import fcntl
    except ImportError:  # pragma: no cover
        # "fcntl Availibility: not Emscripten, not WASI."
        warnings.warn("file locking not available")

        _lock_impl = _lock_noop  # type: ignore

    else:

        class _lock_impl:
            def __init__(self, fd, lock_attempts):
                self.fd = fd
                self.lock_attempts = lock_attempts

            def __enter__(self):
                for attempt in range(self.lock_attempts):
                    try:
                        # msvcrt locking does something similar
                        fcntl.lockf(
                            self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB, 1, LOCK_BYTE
                        )
                        break
                    except OSError:
                        if attempt > self.lock_attempts - 2:
                            raise LockError("Failed to acquire lock.")
                        time.sleep(LOCK_SLEEP)

            def __exit__(self, *exc):
                try:
                    fcntl.lockf(self.fd, fcntl.LOCK_UN, 1, LOCK_BYTE)
                except OSError:
                    raise LockError("Failed to release lock.")


def lock(fd, *, lock_attempts=LOCK_ATTEMPTS):
    if not context.no_lock:
        # locking required for jlap, now default for all
        return _lock_impl(fd, lock_attempts)
    return _lock_noop(fd, lock_attempts)


def locking_supported():
    "Return a bool to report whether file locking is supported or not"
    return _lock_impl is not _lock_noop
