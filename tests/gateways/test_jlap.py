# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
Test that SubdirData is able to use (or skip) incremental jlap downloads.
"""
import datetime
import json
import time
from pathlib import Path
from socket import socket
from unittest.mock import Mock

import jsonpatch
import pytest
import requests
import zstandard

from conda.base.context import conda_tests_ctxt_mgmt_def_pol, context
from conda.common.io import env_vars
from conda.core.subdir_data import SubdirData
from conda.exceptions import CondaHTTPError, CondaSSLError
from conda.gateways.connection.session import CondaSession
from conda.gateways.repodata import (
    CACHE_CONTROL_KEY,
    CACHE_STATE_SUFFIX,
    ETAG_KEY,
    LAST_MODIFIED_KEY,
    URL_KEY,
    CondaRepoInterface,
    RepodataCache,
    RepodataOnDisk,
    RepodataState,
    Response304ContentUnchanged,
    get_repo_interface,
)
from conda.gateways.repodata.jlap import core, fetch, interface
from conda.models.channel import Channel


def test_server_available(package_server: socket):
    port = package_server.getsockname()[1]
    response = requests.get(f"http://127.0.0.1:{port}/notfound")
    assert response.status_code == 404


def test_jlap_fetch(package_server: socket, tmp_path: Path, mocker):
    """Check that JlapRepoInterface doesn't raise exceptions."""
    host, port = package_server.getsockname()
    base = f"http://{host}:{port}/test"

    cache = RepodataCache(base=tmp_path / "cache", repodata_fn="repodata.json")

    url = f"{base}/osx-64"
    repo = interface.JlapRepoInterface(
        url,
        repodata_fn="repodata.json",
        cache=cache,
        cache_path_json=Path(tmp_path, "repodata.json"),
        cache_path_state=Path(tmp_path, f"repodata{CACHE_STATE_SUFFIX}"),
    )

    patched = mocker.patch(
        "conda.gateways.repodata.jlap.fetch.download_and_hash",
        wraps=fetch.download_and_hash,
    )

    state = {}
    with pytest.raises(RepodataOnDisk):
        repo.repodata(state)

    # however it may make two requests - one to look for .json.zst, the second
    # to look for .json
    assert patched.call_count == 2

    # second will try to fetch (non-existent) .jlap, then fall back to .json
    with pytest.raises(RepodataOnDisk):
        repo.repodata(state)  # a 304?

    with pytest.raises(RepodataOnDisk):
        repo.repodata(state)

    # we may be able to do better than this by setting "zst unavailable" sooner
    assert patched.call_count == 4


def test_jlap_fetch_file(package_repository_base: Path, tmp_path: Path, mocker):
    """Check that JlapRepoInterface can fetch from a file:/// URL"""
    base = package_repository_base.as_uri()
    cache = RepodataCache(base=tmp_path / "cache", repodata_fn="repodata.json")
    url = f"{base}/osx-64"
    repo = interface.JlapRepoInterface(
        url,
        repodata_fn="repodata.json",
        cache=cache,
        cache_path_json=Path(tmp_path, "repodata.json"),
        cache_path_state=Path(tmp_path, f"repodata{CACHE_STATE_SUFFIX}"),
    )

    patched = mocker.patch(
        "conda.gateways.repodata.jlap.fetch.download_and_hash",
        wraps=fetch.download_and_hash,
    )

    state = {}
    with pytest.raises(RepodataOnDisk):
        repo.repodata(state)

    # however it may make two requests - one to look for .json.zst, the second
    # to look for .json
    # assert patched.call_count == 2

    # second will try to fetch (non-existent) .jlap, then fall back to .json
    with pytest.raises(RepodataOnDisk):
        repo.repodata(state)  # a 304?

    with pytest.raises(RepodataOnDisk):
        repo.repodata(state)

    # we may be able to do better than this by setting "zst unavailable" sooner
    assert patched.call_count >= 3

    # how do we test if jlap against file returns partial response?


@pytest.mark.parametrize("verify_ssl", [True, False])
def test_jlap_fetch_ssl(
    package_server_ssl: socket, tmp_path: Path, mocker, verify_ssl: bool
):
    """Check that JlapRepoInterface doesn't raise exceptions."""
    host, port = package_server_ssl.getsockname()
    base = f"https://{host}:{port}/test"

    cache = RepodataCache(base=tmp_path / "cache", repodata_fn="repodata.json")

    url = f"{base}/osx-64"
    repo = interface.JlapRepoInterface(
        url,
        repodata_fn="repodata.json",
        cache=cache,
        cache_path_json=Path(tmp_path, f"repodata_{verify_ssl}.json"),
        cache_path_state=Path(tmp_path, f"repodata_{verify_ssl}{CACHE_STATE_SUFFIX}"),
    )

    expected_exception = CondaSSLError if verify_ssl else RepodataOnDisk

    # clear session cache to avoid leftover wrong-ssl-verify Session()
    try:
        del CondaSession._thread_local.session
    except AttributeError:
        pass

    state = {}
    with env_vars(
        {"CONDA_SSL_VERIFY": str(verify_ssl).lower()},
        stack_callback=conda_tests_ctxt_mgmt_def_pol,
    ), pytest.raises(expected_exception), pytest.warns() as record:
        repo.repodata(state)

    # If we didn't disable warnings, we will see two 'InsecureRequestWarning'
    assert len(record) == 0, f"Unexpected warning {record[0]._category_name}"

    # clear session cache to avoid leftover wrong-ssl-verify Session()
    try:
        del CondaSession._thread_local.session
    except AttributeError:
        pass


def test_download_and_hash(
    package_server: socket,
    tmp_path: Path,
    package_repository_base: Path,
):
    host, port = package_server.getsockname()
    base = f"http://{host}:{port}/test"

    url = base + "/notfound.json.zst"
    session = CondaSession()
    state = RepodataState()
    destination = tmp_path / "download_not_found"
    # 404 is raised as an exception
    try:
        fetch.download_and_hash(fetch.hash(), url, destination, session, state)
    except requests.HTTPError as e:
        assert e.response.status_code == 404
        assert not destination.exists()
    else:
        assert False, "must raise"

    destination = tmp_path / "repodata.json"
    url2 = base + "/osx-64/repodata.json"
    hasher2 = fetch.hash()
    response = fetch.download_and_hash(
        hasher2,
        url2,
        destination,
        session,
        state,
        dest_path=destination,
    )
    print(response)
    print(state)
    t = destination.read_text()
    assert len(t)

    # assert we don't clobber if 304 not modified
    response2 = fetch.download_and_hash(
        fetch.hash(),
        url2,
        destination,
        session,
        RepodataState(dict={"_etag": response.headers["etag"]}),
    )
    assert response2.status_code == 304
    assert destination.read_text() == t
    # however the hash will not be recomputed

    (package_repository_base / "osx-64" / "repodata.json.zst").write_bytes(
        zstandard.ZstdCompressor().compress(
            (package_repository_base / "osx-64" / "repodata.json").read_bytes()
        )
    )

    url3 = base + "/osx-64/repodata.json.zst"
    dest_zst = tmp_path / "repodata.json.from-zst"  # should be decompressed
    assert not dest_zst.exists()
    hasher3 = fetch.hash()
    response3 = fetch.download_and_hash(
        hasher3, url3, dest_zst, session, RepodataState(), is_zst=True
    )
    assert response3.status_code == 200
    assert int(response3.headers["content-length"]) < dest_zst.stat().st_size

    assert destination.read_text() == dest_zst.read_text()

    # hashes the decompressed data
    assert hasher2.digest() == hasher3.digest()


@pytest.mark.parametrize("use_jlap", [True, False])
def test_repodata_state(
    package_server: socket,
    use_jlap: bool,
):
    """Test that cache metadata file works correctly."""
    host, port = package_server.getsockname()
    base = f"http://{host}:{port}/test"
    channel_url = f"{base}/osx-64"

    if use_jlap:
        repo_cls = interface.JlapRepoInterface
    else:
        repo_cls = CondaRepoInterface

    with env_vars(
        {"CONDA_PLATFORM": "osx-64", "CONDA_EXPERIMENTAL": "jlap" if use_jlap else ""},
        stack_callback=conda_tests_ctxt_mgmt_def_pol,
    ):
        SubdirData.clear_cached_local_channel_data(
            exclude_file=False
        )  # definitely clears them, including normally-excluded file:// urls

        # possibly file cache is left over from test run

        test_channel = Channel(channel_url)
        sd = SubdirData(channel=test_channel)

        # change SubdirData base path, or set something in context
        # assert not Path(sd.cache_path_json).exists()

        # parameterize whether this is used?
        assert isinstance(sd._repo, repo_cls)

        print(sd.repodata_fn)

        assert sd._loaded is False

        # shoud automatically fetch and load
        assert len(list(sd.iter_records()))

        assert sd._loaded is True

        # now let's check out state file
        state = json.loads(Path(sd.cache_path_state).read_text())

        # not all required depending on server response, but our test server
        # will include them
        for field in (
            LAST_MODIFIED_KEY,
            ETAG_KEY,
            CACHE_CONTROL_KEY,
            URL_KEY,
            "size",
            "mtime_ns",
        ):
            assert field in state
            assert f"_{field}" not in state


@pytest.mark.parametrize("use_jlap", ["jlap", "jlapopotamus", "jlap,another", ""])
def test_jlap_flag(use_jlap):
    """Test that CONDA_EXPERIMENTAL is a comma-delimited list."""
    with env_vars(
        {"CONDA_EXPERIMENTAL": use_jlap},
        stack_callback=conda_tests_ctxt_mgmt_def_pol,
    ):
        expected = "jlap" in use_jlap.split(",")
        assert ("jlap" in context.experimental) is expected

        expected_cls = interface.JlapRepoInterface if expected else CondaRepoInterface
        assert get_repo_interface() is expected_cls


def test_jlap_sought(
    package_server: socket,
    tmp_path: Path,
    package_repository_base: Path,
):
    """Test that we try to fetch the .jlap file."""
    host, port = package_server.getsockname()
    base = f"http://{host}:{port}/test"
    channel_url = f"{base}/osx-64"

    with env_vars(
        {
            "CONDA_PLATFORM": "osx-64",
            "CONDA_EXPERIMENTAL": "jlap",
            "CONDA_PKGS_DIRS": str(tmp_path),
        },
        stack_callback=conda_tests_ctxt_mgmt_def_pol,
    ):
        SubdirData.clear_cached_local_channel_data(
            exclude_file=False
        )  # definitely clears cache, including normally-excluded file:// urls

        test_channel = Channel(channel_url)
        sd = SubdirData(channel=test_channel)

        # isolated by setting CONDA_PKGS_DIRS
        assert not sd.cache_path_state.exists()
        assert not sd.cache_path_json.exists()

        sd.load()

        cache = sd.repo_cache

        # now let's check out state file
        state = json.loads(Path(cache.cache_path_state).read_text())

        print("first fetch", state)

        # test server sets cache-control: no-cache, so we will make a request
        # each time but could receive a 304 Not Modified

        # now try to re-download or use cache
        # unfortunately this is using devenv/.../pkgs/cache/<x>.json not a tmpdir
        SubdirData.clear_cached_local_channel_data(exclude_file=False)

        # Pretend it's older. (mtime is only used to compare the state
        # and repodata files, and is no longer used to store the 'last checked
        # remote' time.)
        state["refresh_ns"] = state["refresh_ns"] - int(1e9 * 60)
        cache.cache_path_state.write_text(json.dumps(state))

        # set context.local_repodata_ttl = 0?
        # 1 = use cache header which is none for the flask web server
        sd = SubdirData(channel=test_channel)
        sd.load()

        print(list(sd.iter_records()))

        state_object = cache.load_state()

        print(state_object)

        assert state_object.should_check_format("jlap") is False

        # This test can be sensitive to whether osx-64/repodata.json is saved
        # with \n or \r\n newlines, since we need its exact hash. Change all
        # data paths to be binary safe.

        test_jlap = make_test_jlap(cache.cache_path_json.read_bytes(), 8)
        test_jlap.terminate()
        test_jlap.write(package_repository_base / "osx-64" / "repodata.jlap")

        SubdirData.clear_cached_local_channel_data(
            exclude_file=False
        )  # definitely clears them, including normally-excluded file:// urls

        test_channel = Channel(channel_url)
        sd = SubdirData(channel=test_channel)

        # clear jlap_unavailable state flag, or it won't look (test this also)
        state = cache.load_state()
        state.clear_has_format("jlap")
        state["refresh_ns"] = state["refresh_ns"] - int(1e9 * 60)
        cache.cache_path_state.write_text(json.dumps(dict(state)))

        sd.load()

        patched = json.loads(sd.cache_path_json.read_text())
        assert len(patched["info"]) == 9

        # get 304 not modified on the .jlap file (test server doesn't return 304
        # not modified on range requests)
        with pytest.raises(RepodataOnDisk):
            sd._repo.repodata(cache.load_state())

        # When desired hash is unavailable

        # XXX produces 'Requested range not satisfiable' (check retry whole jlap
        # after failed fetch)

        test_jlap = make_test_jlap(cache.cache_path_json.read_bytes(), 4)
        footer = test_jlap.pop()
        test_jlap.pop()  # patch taking us to "latest"
        test_jlap.add(footer[1])
        test_jlap.terminate()
        test_jlap.write(package_repository_base / "osx-64" / "repodata.jlap")

        SubdirData.clear_cached_local_channel_data(
            exclude_file=False
        )  # definitely clears them, including normally-excluded file:// urls

        test_channel = Channel(channel_url)
        sd = SubdirData(channel=test_channel)

        # clear jlap_unavailable state flag, or it won't look (test this also)
        state = cache.load_state()
        assert state.has_format("jlap")[0] is True
        state["refresh_ns"] = state["refresh_ns"] - int(1e9 * 60)
        cache.cache_path_state.write_text(json.dumps(dict(state)))

        sd.load()

        patched = json.loads(sd.cache_path_json.read_text())
        assert len(patched["info"]) == 9

        # Bad jlap file. Should produce a 416 Range Not Satisfiable, retry,
        # produce a ValueError, and then fetch the entire repodata.json, setting
        # the jlap_unavailable flag
        (package_repository_base / "osx-64" / "repodata.jlap").write_text("")

        # clear jlap_unavailable state flag, or it won't look (test this also)
        state = cache.load_state()
        # avoid 304 to actually overwrite cached data
        state.etag = ""
        assert fetch.JLAP_UNAVAILABLE not in state  # from previous portion of test
        state["refresh_ns"] = state["refresh_ns"] - int(1e9 * 60)
        cache.cache_path_state.write_text(json.dumps(dict(state)))

        sd.load()

        patched = json.loads(sd.cache_path_json.read_text())
        assert len(patched["info"]) == 1  # patches not found in bad jlap file


def test_jlap_errors(
    package_server: socket, tmp_path: Path, package_repository_base: Path, mocker
):
    """Test that we handle 304 Not Modified responses, other errors."""
    host, port = package_server.getsockname()
    base = f"http://{host}:{port}/test"
    channel_url = f"{base}/osx-64"

    with env_vars(
        {
            "CONDA_PLATFORM": "osx-64",
            "CONDA_EXPERIMENTAL": "jlap",
            "CONDA_PKGS_DIRS": str(tmp_path),
        },
        stack_callback=conda_tests_ctxt_mgmt_def_pol,
    ):
        SubdirData.clear_cached_local_channel_data(
            exclude_file=False
        )  # definitely clears cache, including normally-excluded file:// urls

        test_channel = Channel(channel_url)
        sd = SubdirData(channel=test_channel)

        # normal full-fetch
        sd.load()

        cache = sd.repo_cache
        state = cache.load_state()

        # now try to re-download or use cache
        SubdirData.clear_cached_local_channel_data(exclude_file=False)

        # Pretend it's older. (mtime is only used to compare the state
        # and repodata files, and is no longer used to store the 'last checked
        # remote' time.)
        cache.refresh(state["refresh_ns"] - int(1e9 * 60))

        test_jlap = make_test_jlap(cache.cache_path_json.read_bytes(), 8)
        test_jlap.terminate()
        test_jlap_path = package_repository_base / "osx-64" / "repodata.jlap"
        test_jlap.write(test_jlap_path)

        sd.load()

        state = cache.load_state()
        has, when = state.has_format("jlap")
        assert has is True and isinstance(when, datetime.datetime)

        patched = json.loads(sd.cache_path_json.read_text())
        assert len(patched["info"]) == 9

        # Get a checksum error on the jlap file
        with test_jlap_path.open("a") as test_jlap_file:
            test_jlap_file.write("x")
        state = cache.load_state()
        state["refresh_ns"] -= int(60 * 1e9)
        with pytest.raises(RepodataOnDisk):
            sd._repo.repodata(state)  # type: ignore

        # Get an IndexError on a too-short file
        test_jlap_path.write_text(core.DEFAULT_IV.hex())
        # clear any jlap failures
        state.pop("has_jlap", None)
        state.pop("jlap", None)
        # gets the failure, falls back to non-jlap path, writes to disk
        with pytest.raises(RepodataOnDisk):
            sd._repo.repodata(state)  # type: ignore

        # above call newly saves cache state, write a clean one again.
        # clear any jlap failures
        state.pop("has_jlap", None)
        state.pop("jlap", None)
        cache.cache_path_state.write_text(json.dumps(dict(state)))

        # force 304 not modified on the .jlap file (test server doesn't return 304
        # not modified on range requests)
        with mocker.patch.object(
            CondaSession, "get", return_value=Mock(status_code=304, headers={})
        ), pytest.raises(Response304ContentUnchanged):
            sd._repo.repodata(cache.load_state())  # type: ignore


@pytest.mark.parametrize("use_jlap", [True, False])
def test_jlap_cache_clock(
    package_server: socket,
    tmp_path: Path,
    package_repository_base: Path,
    mocker,
    use_jlap: bool,
):
    """
    Test that we add another "local_repodata_ttl" (an alternative to
    "cache-control: max-age=x") seconds to the clock once the cache expires,
    whether the response was "200" or "304 Not Modified".
    """
    host, port = package_server.getsockname()
    base = f"http://{host}:{port}/test"
    channel_url = f"{base}/osx-64"

    now = time.time_ns()

    # mock current time to avoid waiting for CONDA_LOCAL_REPODATA_TTL
    mocker.patch("time.time_ns", return_value=now)
    assert time.time_ns() == now

    local_repodata_ttl = 30

    with env_vars(
        {
            "CONDA_PLATFORM": "osx-64",
            "CONDA_EXPERIMENTAL": "jlap" if use_jlap else "",
            "CONDA_PKGS_DIRS": str(tmp_path),
            "CONDA_LOCAL_REPODATA_TTL": local_repodata_ttl,
        },
        stack_callback=conda_tests_ctxt_mgmt_def_pol,
    ):
        SubdirData.clear_cached_local_channel_data(
            exclude_file=False
        )  # definitely clears cache, including normally-excluded file:// urls

        test_channel = Channel(channel_url)
        sd = SubdirData(channel=test_channel)
        cache = sd.repo_cache

        # normal full-fetch
        sd.load()
        assert cache.load_state()["refresh_ns"] == time.time_ns()

        # now try to re-download or use cache
        SubdirData.clear_cached_local_channel_data(exclude_file=False)

        test_jlap = make_test_jlap(cache.cache_path_json.read_bytes(), 8)
        test_jlap.terminate()
        test_jlap_path = package_repository_base / "osx-64" / "repodata.jlap"
        test_jlap.write(test_jlap_path)

        later0 = now + (local_repodata_ttl + 1) * int(1e9)
        mocker.patch("time.time_ns", return_value=later0)

        assert cache.stale()
        sd.load()

        later1 = now + (2 * local_repodata_ttl + 2) * int(1e9)
        mocker.patch("time.time_ns", return_value=later1)

        # force 304 not modified on the .jlap file (test server doesn't return 304
        # not modified on range requests)
        with mocker.patch.object(
            CondaSession, "get", return_value=Mock(status_code=304, headers={})
        ):
            assert cache.stale()
            sd.load()

        assert cache.load_state()["refresh_ns"] == later1
        assert not cache.stale()

        later2 = now + ((3 * local_repodata_ttl + 3) * int(1e9))
        mocker.patch("time.time_ns", return_value=later2)

        assert cache.stale()
        sd.load()

        assert cache.load_state()["refresh_ns"] == later2

        # check that non-expried cache avoids updating refresh_ns.
        mocker.patch(
            "time.time_ns", return_value=now + ((3 * local_repodata_ttl + 4) * int(1e9))
        )

        sd.load()
        assert cache.load_state()["refresh_ns"] == later2


def test_jlap_zst_not_404(mocker, package_server, tmp_path):
    """
    Test that exception is raised if `repodata.json.zst` produces something
    other than a 404. For code coverage.
    """
    host, port = package_server.getsockname()
    base = f"http://{host}:{port}/test"

    url = f"{base}/osx-64"
    cache = RepodataCache(base=tmp_path / "cache", repodata_fn="repodata.json")
    repo = interface.JlapRepoInterface(
        url,
        repodata_fn="repodata.json",
        cache=cache,
        cache_path_json=Path(tmp_path, "repodata.json"),
        cache_path_state=Path(tmp_path, f"repodata{CACHE_STATE_SUFFIX}"),
    )

    def error(*args, **kwargs):
        class Response:
            status_code = 405

        raise fetch.HTTPError(response=Response())

    mocker.patch(
        "conda.gateways.repodata.jlap.fetch.download_and_hash", side_effect=error
    )

    with pytest.raises(CondaHTTPError, match="HTTP 405"):
        repo.repodata({})


def test_jlap_core(tmp_path: Path):
    """Code paths not excercised by other tests."""
    with pytest.raises(ValueError):
        # incorrect trailing hash
        core.JLAP.from_lines(
            [core.DEFAULT_IV.hex().encode("utf-8")] * 3, iv=core.DEFAULT_IV, verify=True
        )

    with pytest.raises(IndexError):
        # Not enough lines to compare trailing hash with previous. This
        # exception might change.
        core.JLAP.from_lines(
            [core.DEFAULT_IV.hex().encode("utf-8")] * 1, iv=core.DEFAULT_IV, verify=True
        )

    jlap = core.JLAP.from_lines(
        [core.DEFAULT_IV.hex().encode("utf-8")] * 2, iv=core.DEFAULT_IV, verify=True
    )

    with pytest.raises(ValueError):
        # a line cannot contain \n
        jlap.add("two\nlines")

    test_jlap = tmp_path / "minimal.jlap"

    jlap.write(test_jlap)

    jlap2 = jlap.from_path(test_jlap)

    assert jlap2 == jlap

    # helper properties
    assert jlap2.last == jlap2[-1]
    assert jlap2.penultimate == jlap2[-2]
    assert jlap2.body == jlap2[1:-2]


def make_test_jlap(original: bytes, changes=1):
    """:original: as bytes, to avoid any newline confusion."""

    def jlap_lines():
        yield core.DEFAULT_IV.hex().encode("utf-8")

        before = json.loads(original)
        after = json.loads(original)

        # add changes junk keys to info for test data
        h = fetch.hash()
        h.update(original)
        starting_digest = h.digest().hex()

        for i in range(changes):
            after["info"][f"test{i}"] = i

            patch = jsonpatch.make_patch(before, after)
            row = {"from": starting_digest}
            h = fetch.hash()
            h.update(json.dumps(after).encode("utf-8"))
            starting_digest = h.digest().hex()
            row["to"] = starting_digest
            # poor man's copy.deepcopy() and quite fast
            before = json.loads(json.dumps(after))
            row["patch"] = patch.patch

            yield json.dumps(row).encode("utf-8")

        footer = {"url": "repodata.json", "latest": starting_digest}
        yield json.dumps(footer).encode("utf-8")

    j = core.JLAP.from_lines(jlap_lines(), iv=core.DEFAULT_IV, verify=False)

    return j


def test_hashwriter():
    """Test that HashWriter closes its backing file in a context manager."""
    closed = False

    class backing:
        def close(self):
            nonlocal closed
            closed = True

    writer = fetch.HashWriter(backing(), None)
    with writer:
        pass
    assert closed
