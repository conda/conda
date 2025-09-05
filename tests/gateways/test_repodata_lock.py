# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import multiprocessing
import sys
import traceback
from typing import TYPE_CHECKING

import pytest

from conda.base.context import context, reset_context
from conda.common.compat import on_win
from conda.gateways.repodata import RepodataCache, lock

if TYPE_CHECKING:
    from pathlib import Path

    from pytest import MonkeyPatch


def locker(cache: RepodataCache, qout, qin):
    print(f"Attempt to lock {cache.cache_path_state}")
    qout.put("ready")
    print("sent ready to parent")
    assert qin.get(timeout=6) == "locked"
    print("parent locked. try to save in child (should fail)")
    try:
        cache.save("{}")
        qout.put("not locked")
    except OSError as e:
        print("OSError", e)
        qout.put(e)
    except Exception as e:
        # The wrong exception!
        print("Not OSError", e, file=sys.stderr)
        traceback.print_exception(e)
        qout.put(e)
    else:
        # Speed up test failure if no exception thrown?
        print("no exception")
        qout.put(None)
    print("exit child")


@pytest.mark.parametrize("no_lock", [True, False])
def test_lock_no_lock(tmp_path: Path, monkeypatch: MonkeyPatch, no_lock: bool) -> None:
    """
    Open lockfile, then open it again in a spawned subprocess. Assert subprocess
    times out (should take 10 seconds).
    """
    # forked workers might share file handle and lock
    multiprocessing.set_start_method("spawn", force=True)

    monkeypatch.setenv("CONDA_NO_LOCK", str(no_lock))
    reset_context()
    assert context.no_lock is no_lock

    cache = RepodataCache(tmp_path / "lockme", "repodata.json")

    qout = multiprocessing.Queue()  # put here, get in subprocess
    qin = multiprocessing.Queue()  # get here, put in subprocess

    p = multiprocessing.Process(target=locker, args=(cache, qin, qout))
    p.start()

    assert qin.get(timeout=6) == "ready"
    print("subprocess ready")

    with cache.cache_path_state.open("a+") as lock_file, lock(lock_file):
        print("lock acquired in parent process")
        qout.put("locked")
        if no_lock:
            assert qin.get(timeout=5) == "not locked"
        else:
            assert isinstance(qin.get(timeout=13), OSError)
        p.join(1)
        assert p.exitcode == 0


@pytest.mark.skipif(on_win, reason="emulate windows behavior for code coverage")
def test_lock_rename(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    class PunyPath(type(tmp_path)):
        def rename(self, path):
            if path.exists():
                raise FileExistsError()
            return super().rename(path)

    monkeypatch.setenv("CONDA_EXPERIMENTAL", "lock")
    reset_context()
    assert "lock" in context.experimental

    cache = RepodataCache(tmp_path / "lockme", "puny.json")
    cache.save("{}")
    # RepodataCache first argument is the name of the cache file without an
    # extension, doesn't create tmp_path/lockme as a directory.
    puny = PunyPath(tmp_path, "puny.json.tmp")
    puny.write_text('{"info":{}}')
    cache.replace(puny)
