# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
Strongly related to subdir_data / test_subdir_data.
"""

from __future__ import annotations

import json
import multiprocessing
import sys
import time

import pytest

from conda.base.context import conda_tests_ctxt_mgmt_def_pol, context
from conda.common.io import env_vars
from conda.exceptions import (
    CondaDependencyError,
    CondaHTTPError,
    CondaSSLError,
    ProxyError,
    UnavailableInvalidChannel,
)
from conda.gateways.connection import HTTPError, InvalidSchema, RequestsProxyError, SSLError
from conda.gateways.repodata import (
    RepodataCache,
    RepodataIsEmpty,
    RepodataState,
    _lock,
    conda_http_errors,
)


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

    # lesser backdate.
    # excercise stale paths.
    original_ttl = context.local_repodata_ttl
    try:
        cache.state["refresh_ns"] = time.time_ns() - (31 * 10**9)  # type: ignore
        for ttl, expected in ((0, True), (1, True), (60, False)):
            # < 1 means max-age: 0; 1 means use cache header; >1 means use
            # local_repodata_ttl
            context.local_repodata_ttl = ttl  # type: ignore
            assert cache.stale() is expected
            cache.timeout()
    finally:
        context.local_repodata_ttl = original_ttl

    # since state's mtime_ns matches repodata.json stat(), these will be preserved
    assert cache.state.mod == MOD
    assert cache.state.cache_control == CACHE_CONTROL
    assert cache.state.etag == ETAG

    # XXX rewrite state without replacing repodata.json, assert still stale...

    # mismatched mtime empties cache headers
    state = dict(cache.state)
    assert state["etag"]
    assert cache.state.etag
    state["mtime_ns"] = 0
    cache.cache_path_state.write_text(json.dumps(state))
    cache.load_state()
    assert not cache.state.mod
    assert not cache.state.etag


def test_coverage_repodata_state(tmp_path):
    # now these should be loaded through RepodataCache instead.

    # assert invalid state is equal to no state
    state = RepodataState(
        tmp_path / "garbage.json", tmp_path / "garbage.state.json", "repodata.json"
    )
    state.cache_path_state.write_text("not json")
    assert dict(state.load()) == {}


from conda.gateways.connection import HTTPError, InvalidSchema, RequestsProxyError, SSLError
from conda.gateways.repodata import RepodataIsEmpty, conda_http_errors


def test_coverage_conda_http_errors():

    with pytest.raises(ProxyError), conda_http_errors(
        "https://conda.anaconda.org", "repodata.json"
    ):
        raise RequestsProxyError()

    with pytest.raises(CondaDependencyError), conda_http_errors(
        "https://conda.anaconda.org", "repodata.json"
    ):
        raise InvalidSchema("SOCKS")

    with pytest.raises(InvalidSchema), conda_http_errors(
        "https://conda.anaconda.org", "repodata.json"
    ):
        raise InvalidSchema("shoes")  # not a SOCKS problem

    with pytest.raises(CondaSSLError), conda_http_errors(
        "https://conda.anaconda.org", "repodata.json"
    ):
        raise SSLError()

    # strange url-ends-with-noarch-specific behavior
    with pytest.raises(UnavailableInvalidChannel), conda_http_errors(
        "https://conda.anaconda.org/noarch", "repodata.json"
    ):

        class Response:
            status_code = 404

        raise HTTPError(response=Response)

    with pytest.raises(RepodataIsEmpty), env_vars(
        {"CONDA_ALLOW_NON_CHANNEL_URLS": "1"},
        stack_callback=conda_tests_ctxt_mgmt_def_pol,
    ), conda_http_errors("https://conda.anaconda.org/noarch", "repodata.json"):

        class Response:
            status_code = 404

        raise HTTPError(response=Response)

    # A variety of helpful error messages should follow
    with pytest.raises(CondaHTTPError, match="invalid credentials"), conda_http_errors(
        "https://conda.anaconda.org/noarch", "repodata.json"
    ):

        class Response:
            status_code = 401

        raise HTTPError(response=Response)

    # A (random uuid) token should trigger a different message.
    with pytest.raises(CondaHTTPError, match="token"), conda_http_errors(
        "/t/dh-73683400-b3ee-4f87-ade8-37de6d395bdb/conda-forge/noarch", "repodata.json"
    ):

        class Response:
            status_code = 401

        raise HTTPError(response=Response)

    # Oh no
    with pytest.raises(CondaHTTPError, match="A 500-type"), conda_http_errors(
        "https://repo.anaconda.com/main/linux-64", "repodata.json"
    ):

        class Response:
            status_code = 500

        raise HTTPError(response=Response)

    # Ask to unblock URL
    with pytest.raises(CondaHTTPError, match="blocked"), conda_http_errors(
        "https://repo.anaconda.com/main/linux-64", "repodata.json"
    ):

        class Response:
            status_code = 418

        raise HTTPError(response=Response)

    # Just an error
    with pytest.raises(CondaHTTPError, match="An HTTP error"), conda_http_errors(
        "https://example.org/main/linux-64", "repodata.json"
    ):

        class Response:
            status_code = 418

        raise HTTPError(response=Response)

    # Don't know how to configure "context.channel_alias not in url"


def test_ssl_unavailable_error_message():
    try:
        # OpenSSL appears to be unavailable
        with pytest.raises(CondaSSLError, match="unavailable"), conda_http_errors(
            "https://conda.anaconda.org", "repodata.json"
        ):
            sys.modules["ssl"] = None
            raise SSLError()
    finally:
        del sys.modules["ssl"]
