# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
Test that SubdirData is able to use (or skip) incremental jlap downloads.
"""

import datetime
import json
import time
import warnings
from pathlib import Path
from socket import socket
from unittest.mock import Mock

import jsonpatch
import pytest
import requests
import zstandard
from pytest import FixtureRequest, MonkeyPatch

import conda.gateways.repodata
from conda.base.context import conda_tests_ctxt_mgmt_def_pol, context, reset_context
from conda.common.io import env_vars
from conda.core.subdir_data import SubdirData
from conda.exceptions import CondaHTTPError, CondaSSLError
from conda.gateways.connection.session import CondaSession, get_session
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


@pytest.mark.benchmark
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


@pytest.mark.benchmark
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

    test_jlap = make_test_jlap(
        (package_repository_base / "osx-64" / "repodata.json").read_bytes(), 8
    )
    test_jlap.terminate()
    test_jlap.write(package_repository_base / "osx-64" / "repodata.jlap")

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

    # second will try to fetch .jlap
    with pytest.raises(RepodataOnDisk):
        repo.repodata(state)  # a 304?

    with pytest.raises(RepodataOnDisk):
        repo.repodata(state)

    assert patched.call_count == 2  # for some reason it's 2?


@pytest.mark.parametrize("verify_ssl", [True, False])
@pytest.mark.benchmark
def test_jlap_fetch_ssl(
    package_server_ssl: socket,
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
    verify_ssl: bool,
    request: FixtureRequest,
):
    """Check that JlapRepoInterface doesn't raise exceptions."""
    # clear leftover wrong-ssl-verify sessions
    CondaSession.cache_clear()
    request.addfinalizer(CondaSession.cache_clear)

    # clear lru_cache from the `get_session` function
    request.addfinalizer(get_session.cache_clear)

    monkeypatch.setenv("CONDA_SSL_VERIFY", str(verify_ssl))
    reset_context()
    assert context.ssl_verify is verify_ssl

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
    with pytest.raises(expected_exception), warnings.catch_warnings():
        # warnings are disabled internally otherwise we would see InsecureRequestWarning
        # detect accidental warnings by treating them as errors
        warnings.simplefilter("error")

        repo.repodata({})


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

        if use_jlap:
            assert isinstance(sd._repo, interface.JlapRepoInterface)

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


@pytest.mark.parametrize("use_jlap", [True, False])
def test_repodata_info_jsondecodeerror(
    package_server: socket,
    use_jlap: bool,
    monkeypatch,
):
    """Test that cache metadata file works correctly."""
    host, port = package_server.getsockname()
    base = f"http://{host}:{port}/test"
    channel_url = f"{base}/osx-64"

    with env_vars(
        {"CONDA_PLATFORM": "osx-64", "CONDA_EXPERIMENTAL": "jlap" if use_jlap else ""},
        stack_callback=conda_tests_ctxt_mgmt_def_pol,
    ):
        SubdirData.clear_cached_local_channel_data(
            exclude_file=False
        )  # definitely clears them, including normally-excluded file:// urls

        test_channel = Channel(channel_url)
        sd = SubdirData(channel=test_channel)

        print(sd.repodata_fn)

        assert sd._loaded is False
        # shoud automatically fetch and load
        assert len(list(sd.iter_records()))
        assert sd._loaded is True

        # Corrupt the cache state. Double json could happen when (unadvisably)
        # running conda in parallel, before we added locks-by-default.
        sd.cache_path_state.write_text(sd.cache_path_state.read_text() * 2)

        # now try to re-download
        SubdirData.clear_cached_local_channel_data(exclude_file=False)
        sd2 = SubdirData(channel=test_channel)

        # caplog fixture was able to capture urllib3 logs but not conda's. Could
        # be due to setting propagate=False on conda's root loggers. Instead,
        # mock warning() to save messages.
        records = []

        def warning(*args, **kwargs):
            records.append(args)

        monkeypatch.setattr(conda.gateways.repodata.log, "warning", warning)

        sd2.load()

        assert any(record[0].startswith("JSONDecodeError") for record in records)


@pytest.mark.parametrize("use_jlap", ["jlap", "jlapopotamus", "jlap,another", ""])
def test_jlap_flag(use_jlap):
    """Test that CONDA_EXPERIMENTAL is a comma-delimited list."""
    with env_vars(
        {"CONDA_EXPERIMENTAL": use_jlap},
        stack_callback=conda_tests_ctxt_mgmt_def_pol,
    ):
        expected = "jlap" in use_jlap.split(",")
        assert ("jlap" in context.experimental) is expected

        # now using a subclass of JlapRepoInterface for "check zstd but not jlap"
        if expected:
            assert get_repo_interface() is interface.JlapRepoInterface


@pytest.mark.parametrize("repodata_use_zst", [True, False])
def test_repodata_use_zst(repodata_use_zst):
    expected = (
        CondaRepoInterface if not repodata_use_zst else interface.ZstdRepoInterface
    )
    with env_vars(
        {"CONDA_REPODATA_USE_ZST": repodata_use_zst},
        stack_callback=conda_tests_ctxt_mgmt_def_pol,
    ):
        assert get_repo_interface() is expected


def test_jlap_sought(
    package_server: socket,
    tmp_path: Path,
    package_repository_base: Path,
):
    """Test that we try to fetch the .jlap file."""
    (package_repository_base / "osx-64" / "repodata.jlap").unlink(missing_ok=True)

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

        # clear availability flag, or it won't look (test this also)
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

        # clear availability flag, or it won't look (test this also)
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

        # clear availability flag, or it won't look (test this also)
        state = cache.load_state()
        # avoid 304 to actually overwrite cached data
        state.etag = ""
        state["refresh_ns"] = state["refresh_ns"] - int(1e9 * 60)
        cache.cache_path_state.write_text(json.dumps(dict(state)))

        sd.load()

        patched = json.loads(sd.cache_path_json.read_text())
        assert len(patched["info"]) == 1  # patches not found in bad jlap file


def test_jlap_coverage():
    """
    Force raise RepodataOnDisk() at end of JlapRepoInterface.repodata() function.
    """

    class JlapCoverMe(interface.JlapRepoInterface):
        def repodata_parsed(self, state):
            return

    with pytest.raises(RepodataOnDisk):
        JlapCoverMe("", "", cache=None).repodata({})  # type: ignore


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
        with (
            mocker.patch.object(
                CondaSession, "get", return_value=Mock(status_code=304, headers={})
            ),
            pytest.raises(Response304ContentUnchanged),
        ):
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


def test_jlap_zst_not_zst(package_server, package_repository_base: Path, tmp_path):
    """
    Test that fallback is taken if repodata.json.zst is not decompressible.
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

    (package_repository_base / "osx-64" / "repodata.json.zst").write_text(
        "404 page that returns a 200 error code"
    )

    # will check
    assert cache.state.has_format("zst")[0]

    with pytest.raises(RepodataOnDisk):
        # repodata was written to disk without being parsed
        repo.repodata_parsed({})

    # won't check until the timeout interval (days)
    assert not cache.state.has_format("zst")[0]

    assert len(json.loads(cache.cache_path_json.read_text())["packages"])


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

        # Coverage for the branch that skips irrelevant patches in the series,
        # when deciding which patches take us from our current to desired
        # state.
        yield json.dumps(
            {"from": core.DEFAULT_IV.hex(), "to": core.DEFAULT_IV.hex(), "patch": []}
        ).encode("utf-8")

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


def test_request_url_jlap_state(tmp_path, package_server, package_repository_base):
    """
    Code coverage for case intended to catch "repodata.json written while we
    were downloading its patches".

    When this happens, we do not write a new repodata.json and instruct the
    caller to defer to the on-disk cache.
    """
    host, port = package_server.getsockname()
    base = f"http://{host}:{port}/test"
    url = f"{base}/osx-64/repodata.json"

    cache = RepodataCache(base=tmp_path / "cache", repodata_fn="repodata.json")
    cache.state.set_has_format("jlap", True)
    cache.save(json.dumps({"info": {}}))

    test_jlap = make_test_jlap(cache.cache_path_json.read_bytes(), 8)
    test_jlap.terminate()
    test_jlap_path = package_repository_base / "osx-64" / "repodata.jlap"
    test_jlap.write(test_jlap_path)

    temp_path = tmp_path / "new_repodata.json"

    # correct hash must appear here and in test_jlap to reach desired condition
    outdated_state = cache.load_state()
    hasher = fetch.hash()
    hasher.update(cache.cache_path_json.read_bytes())
    outdated_state[fetch.NOMINAL_HASH] = hasher.hexdigest()
    outdated_state[fetch.ON_DISK_HASH] = hasher.hexdigest()

    # Simulate a peculiar "request_url_jlap_state uses state object, but later
    # re-fetches state from disk" condition where the initial state and the
    # on-disk state were inconsistent. This is done to avoid unnecessary reads
    # of repodata.json. The failure will happen in the wild when another process
    # writes repodata.json while we are downloading ours.
    on_disk_state = json.loads(cache.cache_path_state.read_text())
    on_disk_state[fetch.NOMINAL_HASH] = "0" * 64
    on_disk_state[fetch.ON_DISK_HASH] = "0" * 64
    cache.cache_path_state.write_text(json.dumps(on_disk_state))

    result = fetch.request_url_jlap_state(
        url,
        outdated_state,
        session=CondaSession(),
        cache=cache,
        temp_path=temp_path,
    )

    assert result is None
