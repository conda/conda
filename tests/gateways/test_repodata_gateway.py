# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
Strongly related to subdir_data / test_subdir_data.
"""

import json
import time
from conda.gateways.repodata import _lock, RepodataCache, RepodataState

import multiprocessing


def locker(cache: RepodataCache, qout, qin):
    print(f"Attempt to lock {cache.cache_path_state}")
    qout.put("ready")
    print("sent ready to parent")
    assert qin.get(timeout=6) == "locked"
    print("parent locked. try to save in child (should fail)")
    try:
        cache.save("{}")
    except OSError as e:
        print("OSError", e)
        qout.put(e)
    except Exception as e:
        # The wrong exception!
        print("Not OSError", e)
        qout.put(e)
    else:
        # Speed up test failure if no exception thrown?
        print("no exception")
        qout.put(None)
    print("exit child")


def test_lock_can_lock(tmp_path):
    """
    Open lockfile, then open it again in a spawned subprocess. Assert subprocess
    times out (should take 10 seconds).
    """
    # forked workers might share file handle and lock
    multiprocessing.set_start_method("spawn", force=True)

    cache = RepodataCache(tmp_path / "lockme", "repodata.json")

    qout = multiprocessing.Queue()  # put here, get in subprocess
    qin = multiprocessing.Queue()  # get here, put in subprocess

    p = multiprocessing.Process(target=locker, args=(cache, qin, qout))
    p.start()

    assert qin.get(timeout=6) == "ready"
    print("subprocess ready")

    with cache.cache_path_state.open("a+") as lock_file, _lock(lock_file):
        print("lock acquired in parent process")
        qout.put("locked")
        assert isinstance(qin.get(timeout=13), OSError)
        p.join(1)
        assert p.exitcode == 0


def test_save(tmp_path):
    """
    Check regular cache save, load operations.
    """
    TEST_DATA = "{}"
    cache = RepodataCache(tmp_path / "lockme", "repodata.json")
    cache.save(TEST_DATA)

    assert cache.load() == TEST_DATA

    state = dict(cache.state)

    json_stat = cache.cache_path_json.stat()

    time.sleep(0.1)  # may be necessary on Windows for time.time_ns() to advance

    # update last-checked-timestamp in .state.json
    cache.refresh()

    # repodata.json's mtime should be equal
    json_stat2 = cache.cache_path_json.stat()
    assert json_stat.st_mtime_ns == json_stat2.st_mtime_ns

    state2 = dict(cache.state)

    assert state2 != state

    # force reload repodata, .state.json from disk
    cache.load()
    state3 = dict(cache.state)

    assert state3 == state2


def test_stale(tmp_path):
    """
    RepodataCache should understand cache-control and modified time versus now.
    """
    TEST_DATA = "{}"
    cache = RepodataCache(tmp_path / "cacheme", "repodata.json")
    MOD = "Thu, 26 Jan 2023 19:34:01 GMT"
    cache.state.mod = MOD
    CACHE_CONTROL = "public, max-age=30"
    cache.state.cache_control = CACHE_CONTROL
    ETAG = '"etag"'
    cache.state.etag = ETAG
    cache.save(TEST_DATA)

    cache.load()
    assert not cache.stale()
    assert 29 < cache.timeout() < 30.1  # time difference between record and save timestamp

    # backdate
    cache.state["refresh_ns"] = time.time_ns() - (60 * 10**9)  # type: ignore
    cache.cache_path_state.write_text(json.dumps(dict(cache.state)))
    assert cache.load() == TEST_DATA
    assert cache.stale()

    # since state's mtime_ns matches repodata.json stat(), these will be preserved
    assert cache.state.mod == MOD
    assert cache.state.cache_control == CACHE_CONTROL
    assert cache.state.etag == ETAG

    # XXX rewrite state without replacing repodata.json, assert still stale...


def test_coverage_repodata_state(tmp_path):
    # now these should be loaded through RepodataCache instead.

    # assert invalid state is equal to no state
    state = RepodataState(
        tmp_path / "garbage.json", tmp_path / "garbage.state.json", "repodata.json"
    )
    state.cache_path_state.write_text("not json")
    assert dict(state.load()) == {}
