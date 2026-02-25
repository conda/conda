# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
Test that SubdirData is able to use zstd repodata downloads.
"""

import json
from pathlib import Path
from socket import socket

import pytest
import requests
import zstandard
from pytest import MonkeyPatch

import conda.gateways.repodata
from conda.base.context import reset_context
from conda.core.subdir_data import SubdirData
from conda.exceptions import CondaHTTPError
from conda.gateways.connection.session import CondaSession
from conda.gateways.repodata import (
    CACHE_CONTROL_KEY,
    ETAG_KEY,
    LAST_MODIFIED_KEY,
    URL_KEY,
    CondaRepoInterface,
    RepodataCache,
    RepodataOnDisk,
    RepodataState,
    get_repo_interface,
)
from conda.gateways.repodata.zstd import (
    ZstdRepoInterface,
    download_repodata,
)
from conda.models.channel import Channel


def test_server_available(package_server: socket):
    port = package_server.getsockname()[1]
    response = requests.get(f"http://127.0.0.1:{port}/notfound")
    assert response.status_code == 404


def test_download_repodata(
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
        download_repodata(url, destination, session, state)
    except requests.HTTPError as e:
        assert e.response.status_code == 404
        assert not destination.exists()
    else:
        assert False, "must raise"

    destination = tmp_path / "repodata.json"
    url2 = base + "/osx-64/repodata.json"
    response = download_repodata(
        url2,
        destination,
        session,
        state,
        dest_path=destination,
    )
    t = destination.read_text()
    assert len(t)

    # assert we don't clobber if 304 not modified
    response2 = download_repodata(
        url2,
        destination,
        session,
        RepodataState(dict={"_etag": response.headers["etag"]}),
    )
    assert response2.status_code == 304
    assert destination.read_text() == t

    (package_repository_base / "osx-64" / "repodata.json.zst").write_bytes(
        zstandard.ZstdCompressor().compress(
            (package_repository_base / "osx-64" / "repodata.json").read_bytes()
        )
    )

    url3 = base + "/osx-64/repodata.json.zst"
    dest_zst = tmp_path / "repodata.json.from-zst"  # should be decompressed
    assert not dest_zst.exists()
    response3 = download_repodata(url3, dest_zst, session, RepodataState(), is_zst=True)
    assert response3.status_code == 200
    assert int(response3.headers["content-length"]) < dest_zst.stat().st_size

    assert destination.read_text() == dest_zst.read_text()


def test_repodata_state(
    package_server: socket,
    monkeypatch: MonkeyPatch,
):
    """Test that cache metadata file works correctly.  This test is valid for both .zst and .json repodata formats."""
    host, port = package_server.getsockname()
    base = f"http://{host}:{port}/test"
    channel_url = f"{base}/osx-64"

    monkeypatch.setenv("CONDA_PLATFORM", "osx-64")
    reset_context()

    SubdirData.clear_cached_local_channel_data(
        exclude_file=False
    )  # definitely clears them, including normally-excluded file:// urls

    # possibly file cache is left over from test run

    test_channel = Channel(channel_url)
    sd = SubdirData(channel=test_channel)

    # change SubdirData base path, or set something in context

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


def test_repodata_info_jsondecodeerror(
    package_server: socket,
    monkeypatch,
):
    """Test that corrupted cache state file (double JSON) is handled gracefully with a warning."""
    host, port = package_server.getsockname()
    base = f"http://{host}:{port}/test"
    channel_url = f"{base}/osx-64"

    monkeypatch.setenv("CONDA_PLATFORM", "osx-64")
    reset_context()

    SubdirData.clear_cached_local_channel_data(
        exclude_file=False
    )  # definitely clears them, including normally-excluded file:// urls

    test_channel = Channel(channel_url)
    sd = SubdirData(channel=test_channel)

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


@pytest.mark.parametrize("repodata_use_zst", [True, False])
def test_repodata_use_zst(repodata_use_zst, monkeypatch: pytest.MonkeyPatch):
    expected = CondaRepoInterface if not repodata_use_zst else ZstdRepoInterface
    monkeypatch.setenv("CONDA_REPODATA_USE_ZST", str(repodata_use_zst))
    reset_context()
    assert get_repo_interface() is expected


def test_zstd_not_404(mocker, package_server, tmp_path):
    """
    Test that exception is raised if `repodata.json.zst` produces something
    other than a 404. For code coverage.
    """
    host, port = package_server.getsockname()
    base = f"http://{host}:{port}/test"

    url = f"{base}/osx-64"
    cache = RepodataCache(base=tmp_path / "cache", repodata_fn="repodata.json")
    repo = ZstdRepoInterface(
        url,
        repodata_fn="repodata.json",
        cache=cache,
    )

    def error(*args, **kwargs):
        class Response:
            status_code = 405

        raise requests.HTTPError(response=Response())

    mocker.patch("conda.gateways.repodata.zstd.download_repodata", side_effect=error)

    with pytest.raises(CondaHTTPError, match="HTTP 405"):
        repo.repodata({})


def test_zstd_fallback_on_invalid_zstd(
    package_server, package_repository_base: Path, tmp_path
):
    """
    Test that fallback is taken if repodata.json.zst is not decompressible.
    """
    host, port = package_server.getsockname()
    base = f"http://{host}:{port}/test"

    url = f"{base}/osx-64"
    cache = RepodataCache(base=tmp_path / "cache", repodata_fn="repodata.json")
    repo = ZstdRepoInterface(
        url,
        repodata_fn="repodata.json",
        cache=cache,
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
