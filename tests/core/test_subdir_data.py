# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause


import json
from logging import getLogger
from os.path import dirname, join
from pathlib import Path
from time import sleep
from unittest import TestCase
from unittest.mock import patch

import pytest

from conda.base.context import conda_tests_ctxt_mgmt_def_pol, context
from conda.common.disk import temporary_content_in_file
from conda.common.io import env_var, env_vars
from conda.core.index import get_index
from conda.core.subdir_data import (
    RepodataState,
    CondaRepoInterface,
    Response304ContentUnchanged,
    SubdirData,
    cache_fn_url,
    fetch_repodata_remote_request,
    read_mod_and_etag,
)
from conda.exceptions import CondaSSLError, CondaUpgradeError, UnavailableInvalidChannel
from conda.gateways.connection import SSLError
from conda.gateways.connection.session import CondaSession
from conda.models.channel import Channel
from conda.models.records import PackageRecord
from conda.testing.integration import make_temp_env

log = getLogger(__name__)

# some test dependencies are unavailable on newer platforsm
OVERRIDE_PLATFORM = (
    "linux-64" if context.subdir not in ("win-64", "linux-64", "osx-64") else context.subdir
)


def platform_in_record(platform, record):
    return (
        record.name.endswith("@")
        or ("/%s/" % platform in record.url)
        or ("/noarch/" in record.url)
    )


@pytest.mark.integration
class GetRepodataIntegrationTests(TestCase):
    def test_get_index_no_platform_with_offline_cache(self, platform=OVERRIDE_PLATFORM):
        import conda.core.subdir_data

        with env_vars(
            {"CONDA_REPODATA_TIMEOUT_SECS": "0", "CONDA_PLATFORM": platform},
            stack_callback=conda_tests_ctxt_mgmt_def_pol,
        ):
            with patch.object(conda.core.subdir_data, "read_mod_and_etag") as read_mod_and_etag:
                read_mod_and_etag.return_value = {}
                channel_urls = ("https://repo.anaconda.com/pkgs/pro",)

                this_platform = context.subdir
                index = get_index(channel_urls=channel_urls, prepend=False)
                for dist, record in index.items():
                    assert platform_in_record(this_platform, record), (
                        this_platform,
                        record.url,
                    )

        # When unknown=True (which is implicitly engaged when context.offline is
        # True), there may be additional items in the cache that are included in
        # the index. But where those items coincide with entries already in the
        # cache, they must not change the record in any way. TODO: add one or
        # more packages to the cache so these tests affirmatively exercise
        # supplement_index_from_cache on CI?

        for unknown in (None, False, True):
            with env_var("CONDA_OFFLINE", "yes", stack_callback=conda_tests_ctxt_mgmt_def_pol):
                # note `fetch_repodata_remote_request` will no longer be called
                # by conda code, and is only there for backwards compatibility.
                with patch.object(
                    conda.core.subdir_data, "fetch_repodata_remote_request"
                ) as remote_request:
                    index2 = get_index(channel_urls=channel_urls, prepend=False, unknown=unknown)
                    assert all(index2.get(k) == rec for k, rec in index.items())
                    assert unknown is not False or len(index) == len(index2)
                    assert remote_request.call_count == 0

        for unknown in (False, True):
            with env_vars(
                {"CONDA_REPODATA_TIMEOUT_SECS": "0", "CONDA_PLATFORM": "linux-64"},
                stack_callback=conda_tests_ctxt_mgmt_def_pol,
            ):
                with patch.object(
                    conda.core.subdir_data, "fetch_repodata_remote_request"
                ) as remote_request:
                    remote_request.side_effect = Response304ContentUnchanged()
                    index3 = get_index(channel_urls=channel_urls, prepend=False, unknown=unknown)
                    assert all(index3.get(k) == rec for k, rec in index.items())
                    assert unknown or len(index) == len(index3)

        # only works if CONDA_PLATFORM exists in tests/data/conda_format_repo
        # (test will not pass on newer platforms with default CONDA_PLATFORM =
        # 'osx-arm64' etc.)
        with env_vars(
            {"CONDA_OFFLINE": "yes", "CONDA_PLATFORM": platform},
            stack_callback=conda_tests_ctxt_mgmt_def_pol,
        ):
            local_channel = Channel(
                join(dirname(__file__), "..", "data", "conda_format_repo", platform)
            )
            sd = SubdirData(channel=local_channel)
            assert len(sd.query_all("zlib", channels=[local_channel])) > 0
            assert len(sd.query_all("zlib")) == 0
        assert len(sd.query_all("zlib")) > 1

        # test slow "check against all packages" query
        assert len(tuple(sd.query("*[version=1.2.11]"))) >= 1

        # test search by PackageRecord
        assert any(sd.query(next(sd.query("zlib"))))  # type: ignore

        # test load from cache
        with env_vars(
            {"CONDA_USE_INDEX_CACHE": "true"}, stack_callback=conda_tests_ctxt_mgmt_def_pol
        ):
            sd._load()


class StaticFunctionTests(TestCase):
    def test_read_mod_and_etag_mod_only(self):
        mod_only_str = """
        {
        "_mod": "Wed, 14 Dec 2016 18:49:16 GMT",
        "_url": "https://conda.anaconda.org/conda-canary/noarch",
        "info": {
            "arch": null,
            "default_numpy_version": "1.7",
            "default_python_version": "2.7",
            "platform": null,
            "subdir": "noarch"
        },
        "packages": {}
        }
        """.strip()
        with temporary_content_in_file(mod_only_str) as path:
            mod_etag_dict = read_mod_and_etag(path)
            assert "_etag" not in mod_etag_dict
            assert mod_etag_dict["_mod"] == "Wed, 14 Dec 2016 18:49:16 GMT"

    def test_read_mod_and_etag_etag_only(self):
        etag_only_str = """
        {
        "_url": "https://repo.anaconda.com/pkgs/r/noarch",
        "info": {},
        "_etag": "\"569c0ecb-48\"",
        "packages": {}
        }
        """.strip()
        with temporary_content_in_file(etag_only_str) as path:
            mod_etag_dict = read_mod_and_etag(path)
            assert "_mod" not in mod_etag_dict
            assert mod_etag_dict["_etag"] == '"569c0ecb-48"'

    def test_read_mod_and_etag_etag_mod(self):
        etag_mod_str = """
        {
        "_etag": "\"569c0ecb-48\"",
        "_mod": "Sun, 17 Jan 2016 21:59:39 GMT",
        "_url": "https://repo.anaconda.com/pkgs/r/noarch",
        "info": {},
        "packages": {}
        }
        """.strip()
        with temporary_content_in_file(etag_mod_str) as path:
            mod_etag_dict = read_mod_and_etag(path)
            assert mod_etag_dict["_mod"] == "Sun, 17 Jan 2016 21:59:39 GMT"
            assert mod_etag_dict["_etag"] == '"569c0ecb-48"'

    def test_read_mod_and_etag_mod_etag(self):
        mod_etag_str = """
        {
        "_mod": "Sun, 17 Jan 2016 21:59:39 GMT",
        "_url": "https://repo.anaconda.com/pkgs/r/noarch",
        "info": {},
        "_etag": "\"569c0ecb-48\"",
        "packages": {}
        }
        """.strip()
        with temporary_content_in_file(mod_etag_str) as path:
            mod_etag_dict = read_mod_and_etag(path)
            assert mod_etag_dict["_mod"] == "Sun, 17 Jan 2016 21:59:39 GMT"
            assert mod_etag_dict["_etag"] == '"569c0ecb-48"'

    def test_cache_fn_url_repo_continuum_io(self):
        hash1 = cache_fn_url("http://repo.continuum.io/pkgs/free/osx-64/")
        hash2 = cache_fn_url("http://repo.continuum.io/pkgs/free/osx-64")
        assert "aa99d924.json" == hash1 == hash2

        hash3 = cache_fn_url("https://repo.continuum.io/pkgs/free/osx-64/")
        hash4 = cache_fn_url("https://repo.continuum.io/pkgs/free/osx-64")
        assert "d85a531e.json" == hash3 == hash4 != hash1

        hash5 = cache_fn_url("https://repo.continuum.io/pkgs/free/linux-64/")
        assert hash4 != hash5

        hash6 = cache_fn_url("https://repo.continuum.io/pkgs/r/osx-64")
        assert hash4 != hash6

    def test_cache_fn_url_repo_anaconda_com(self):
        hash1 = cache_fn_url("http://repo.anaconda.com/pkgs/free/osx-64/")
        hash2 = cache_fn_url("http://repo.anaconda.com/pkgs/free/osx-64")
        assert "1e817819.json" == hash1 == hash2

        hash3 = cache_fn_url("https://repo.anaconda.com/pkgs/free/osx-64/")
        hash4 = cache_fn_url("https://repo.anaconda.com/pkgs/free/osx-64")
        assert "3ce78580.json" == hash3 == hash4 != hash1

        hash5 = cache_fn_url("https://repo.anaconda.com/pkgs/free/linux-64/")
        assert hash4 != hash5

        hash6 = cache_fn_url("https://repo.anaconda.com/pkgs/r/osx-64")
        assert hash4 != hash6


class FetchLocalRepodataTests(TestCase):
    def test_fetch_repodata_remote_request_invalid_arch(self):
        # see https://github.com/conda/conda/issues/8150
        url = "file:///fake/fake/fake/linux-64"
        etag = None
        mod_stamp = "Mon, 28 Jan 2019 01:01:01 GMT"
        result = fetch_repodata_remote_request(url, etag, mod_stamp)
        assert result is None

    def test_fetch_repodata_remote_request_invalid_noarch(self):
        url = "file:///fake/fake/fake/noarch"
        etag = None
        mod_stamp = "Mon, 28 Jan 2019 01:01:01 GMT"
        with pytest.raises(UnavailableInvalidChannel):
            fetch_repodata_remote_request(url, etag, mod_stamp)


def test_no_ssl(mocker):
    def CondaSession_get(*args, **kwargs):
        raise SSLError("Got an SSL error")

    mocker.patch.object(CondaSession, "get", CondaSession_get)

    url = "https://www.fake.fake/fake/fake/noarch"
    etag = None
    mod_stamp = "Mon, 28 Jan 2019 01:01:01 GMT"
    with pytest.raises(CondaSSLError):
        fetch_repodata_remote_request(url, etag, mod_stamp)


def test_subdir_data_prefers_conda_to_tar_bz2(platform=OVERRIDE_PLATFORM):
    # force this to False, because otherwise tests fail when run with old conda-build
    with env_vars(
        {"CONDA_USE_ONLY_TAR_BZ2": False, "CONDA_PLATFORM": platform},
        stack_callback=conda_tests_ctxt_mgmt_def_pol,
    ):
        channel = Channel(join(dirname(__file__), "..", "data", "conda_format_repo", platform))
        sd = SubdirData(channel)
        precs = tuple(sd.query("zlib"))
        assert precs[0].fn.endswith(".conda")


def test_use_only_tar_bz2(platform=OVERRIDE_PLATFORM):
    channel = Channel(join(dirname(__file__), "..", "data", "conda_format_repo", platform))
    SubdirData.clear_cached_local_channel_data()
    with env_var("CONDA_USE_ONLY_TAR_BZ2", True, stack_callback=conda_tests_ctxt_mgmt_def_pol):
        sd = SubdirData(channel)
        precs = tuple(sd.query("zlib"))
        assert precs[0].fn.endswith(".tar.bz2")
    SubdirData.clear_cached_local_channel_data()
    with env_var("CONDA_USE_ONLY_TAR_BZ2", False, stack_callback=conda_tests_ctxt_mgmt_def_pol):
        sd = SubdirData(channel)
        precs = tuple(sd.query("zlib"))
        assert precs[0].fn.endswith(".conda")


def test_subdir_data_coverage(platform=OVERRIDE_PLATFORM):
    # make_temp_env() suggests integration test
    with make_temp_env(), env_vars(
        {"CONDA_PLATFORM": platform},
        stack_callback=conda_tests_ctxt_mgmt_def_pol,
    ):
        channel = Channel(join(dirname(__file__), "..", "data", "conda_format_repo", platform))
        sd = SubdirData(channel)
        sd.load()
        assert all(isinstance(p, PackageRecord) for p in sd._package_records[1:])

        assert all(r.name == "zlib" for r in sd._iter_records_by_name("zlib"))  # type: ignore

        sd.reload()
        assert all(r.name == "zlib" for r in sd._iter_records_by_name("zlib"))  # type: ignore

        # newly deprecated, run them anyway
        sd._save_state(sd._load_state())

        # clear, to see our testing class
        SubdirData._cache_.clear()

        class SubdirDataRepodataTooNew(SubdirData):
            def _load(self):
                return {"repodata_version": 1024}

        with pytest.raises(CondaUpgradeError):
            SubdirDataRepodataTooNew(channel).load()


def test_metadata_cache_works(platform=OVERRIDE_PLATFORM):
    channel = Channel(join(dirname(__file__), "..", "data", "conda_format_repo", platform))
    SubdirData.clear_cached_local_channel_data()

    # Sadly, on Windows, st_mtime resolution is limited to 2 seconds. (See note in Python docs
    # on os.stat_result.)  To ensure that the timestamp on the existing JSON file is safely
    # in the past before this test starts, we need to wait for more than 2 seconds...

    sleep(3)

    with env_vars(
        {"CONDA_PLATFORM": platform}, stack_callback=conda_tests_ctxt_mgmt_def_pol
    ), patch.object(CondaRepoInterface, "repodata", return_value="{}") as fetcher:
        sd_a = SubdirData(channel)
        tuple(sd_a.query("zlib"))
        assert fetcher.call_count == 1

        sd_b = SubdirData(channel)
        assert sd_b is sd_a
        tuple(sd_b.query("zlib"))
        assert fetcher.call_count == 1


def test_metadata_cache_clearing(platform=OVERRIDE_PLATFORM):
    channel = Channel(join(dirname(__file__), "..", "data", "conda_format_repo", platform))
    SubdirData.clear_cached_local_channel_data()

    with env_vars(
        {"CONDA_PLATFORM": platform}, stack_callback=conda_tests_ctxt_mgmt_def_pol
    ), patch.object(CondaRepoInterface, "repodata", return_value="{}") as fetcher:
        sd_a = SubdirData(channel)
        precs_a = tuple(sd_a.query("zlib"))
        assert fetcher.call_count == 1

        SubdirData.clear_cached_local_channel_data()

        sd_b = SubdirData(channel)
        assert sd_b is not sd_a
        precs_b = tuple(sd_b.query("zlib"))
        assert fetcher.call_count == 2
        assert precs_b == precs_a


def test_cache_json(tmp_path: Path):
    """
    Load and save standardized field names, from internal matches-legacy
    underscore-prefixed field names. Assert state is only loaded if it matches
    cached json.
    """
    cache_json = tmp_path / "cached.json"
    cache_state = tmp_path / "cached.state.json"

    cache_json.write_text("{}")

    RepodataState(cache_json, cache_state, "repodata.json").save()

    state = RepodataState(cache_json, cache_state, "repodata.json").load()

    mod = "last modified time"

    state = RepodataState(cache_json, cache_state, "repodata.json")
    state.mod = mod  # this is the last-modified header not mtime_ns
    state.cache_control = "cache control"
    state.etag = "etag"
    state.save()

    on_disk_format = json.loads(cache_state.read_text())
    print("disk format", on_disk_format)
    assert on_disk_format["mod"] == mod
    assert on_disk_format["cache_control"]
    assert on_disk_format["etag"]
    assert isinstance(on_disk_format["size"], int)
    assert isinstance(on_disk_format["mtime_ns"], int)

    state2 = RepodataState(cache_json, cache_state, "repodata.json").load()
    assert state2.mod == mod
    assert state2.cache_control
    assert state2.etag

    assert state2["mod"] == state2.mod
    assert state2["etag"] == state2.etag
    assert state2["cache_control"] == state2.cache_control

    cache_json.write_text("{ }")  # now invalid due to size

    state_invalid = RepodataState(cache_json, cache_state, "repodata.json").load()
    assert state_invalid.get("mod") == ""
