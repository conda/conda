# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
Strongly related to subdir_data / test_subdir_data.
"""

from conda.gateways.repodata import _lock

import multiprocessing


def locker(path, q):
    print(f"Attempt to lock {path}")
    try:
        with path.open("a+") as lock_file, _lock(lock_file):
            assert False
    except OSError as e:
        q.put(e)


def test_lock_can_lock(tmp_path):
    """
    Open lockfile, then open it again in a spawned subprocess. Assert subprocess
    times out (should take 10 seconds).
    """
    multiprocessing.set_start_method("spawn", force=True)

    lock = tmp_path / "locked.txt"

    with lock.open("a+") as lock_file, _lock(lock_file):
        q = multiprocessing.Queue()
        p = multiprocessing.Process(target=locker, args=(lock, q))
        p.start()
        p.join(11)
        assert p.exitcode == 0
        assert isinstance(q.get(timeout=0), OSError)
