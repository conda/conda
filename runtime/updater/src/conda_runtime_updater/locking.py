# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Cross-platform runtime update coordination locks."""

from __future__ import annotations

import sys
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path
    from typing import BinaryIO


def acquire_lock(lock_path: Path) -> BinaryIO:
    """Open and exclusively lock the runtime's pre-created one-byte lock file."""

    lock = lock_path.open("r+b", buffering=0)
    try:
        if sys.platform == "win32":
            import msvcrt

            while True:
                lock.seek(0)
                try:
                    msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
                    break
                except OSError:
                    time.sleep(0.1)
        else:
            import fcntl

            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        return lock
    except BaseException:
        lock.close()
        raise


def release_lock(lock: BinaryIO) -> None:
    """Unlock and close a coordinator lock handle."""

    try:
        lock.seek(0)
        if sys.platform == "win32":
            import msvcrt

            msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
    finally:
        lock.close()
