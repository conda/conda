# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from logging import getLogger
from os.path import join
from pathlib import Path
from time import sleep

import pytest

from conda import CondaError
from conda.base.context import conda_tests_ctxt_mgmt_def_pol, context
from conda.common.io import env_var, env_vars
from conda.core.index import get_index
from conda.core.subdir_data import SubdirData, cache_fn_url
from conda.exceptions import CondaUpgradeError
from conda.gateways.repodata import (
    CondaRepoInterface,
    RepodataCache,
    RepodataFetch,
    get_repo_interface,
)
from conda.models.channel import Channel
from conda.models.records import PackageRecord
from conda.testing.helpers import CHANNEL_DIR_V1, CHANNEL_DIR_V2
from conda.utils import url_path

log = getLogger(__name__)

# some test dependencies are unavailable on newer platforsm
OVERRIDE_PLATFORM = (
    "linux-64"
    if context.subdir not in ("win-64", "linux-64", "osx-64")
    else context.subdir
)


def platform_in_record(platform, record):
    return (
        record.name.endswith("@")
        or (f"/{platform}/" in record.url)
        or ("/noarch/" in record.url)
    )


@pytest.mark.integration
def test_get_index_no_platform_with_offline_cache(platform=OVERRIDE_PLATFORM):
    with env_vars(
        {"CONDA_REPODATA_TIMEOUT_SECS": "0", "CONDA_PLATFORM": platform},
        stack_callback=conda_tests_ctxt_mgmt_def_pol,
    ):
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
        with env_var(
            "CONDA_OFFLINE", "yes", stack_callback=conda_tests_ctxt_mgmt_def_pol
        ):
            index2 = get_index(
                channel_urls=channel_urls, prepend=False, unknown=unknown
            )
            assert all(index2.get(k) == rec for k, rec in index.items())
            assert unknown is not False or len(index) == len(index2)

    for unknown in (False, True):
        with env_vars(
            {"CONDA_REPODATA_TIMEOUT_SECS": "0", "CONDA_PLATFORM": "linux-64"},
            stack_callback=conda_tests_ctxt_mgmt_def_pol,
        ):
            index3 = get_index(
                channel_urls=channel_urls, prepend=False, unknown=unknown
            )
            assert all(index3.get(k) == rec for k, rec in index.items())
            assert unknown or len(index) == len(index3)

    # only works if CONDA_PLATFORM exists in tests/data/conda_format_repo
    # (test will not pass on newer platforms with default CONDA_PLATFORM =
    # 'osx-arm64' etc.)
    with env_vars(
        {"CONDA_OFFLINE": "yes", "CONDA_PLATFORM": platform},
        stack_callback=conda_tests_ctxt_mgmt_def_pol,
    ):
        local_channel = Channel(join(CHANNEL_DIR_V1, platform))
        sd = SubdirData(channel=local_channel)
        assert len(sd.query_all("zlib", channels=[local_channel])) > 0
        assert len(sd.query_all("zlib", channels=context.channels or ["defaults"])) == 0
    assert len(sd.query_all("zlib", channels=context.channels or ["defaults"])) > 1

    # test load from cache
    with env_vars(
        {"CONDA_USE_INDEX_CACHE": "true"},
        stack_callback=conda_tests_ctxt_mgmt_def_pol,
    ):
        sd.clear_cached_local_channel_data()
        sd._load()


def test_cache_fn_url_repo_continuum_io():
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


def test_cache_fn_url_repo_anaconda_com():
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


def test_subdir_data_prefers_conda_to_tar_bz2(platform=OVERRIDE_PLATFORM):
    # force this to False, because otherwise tests fail when run with old conda-build
    with env_vars(
        {"CONDA_USE_ONLY_TAR_BZ2": False, "CONDA_PLATFORM": platform},
        stack_callback=conda_tests_ctxt_mgmt_def_pol,
    ):
        channel = Channel(join(CHANNEL_DIR_V1, platform))
        sd = SubdirData(channel)
        precs = tuple(sd.query("zlib"))
        assert precs[0].fn.endswith(".conda")


def test_use_only_tar_bz2(platform=OVERRIDE_PLATFORM):
    channel = Channel(join(CHANNEL_DIR_V1, platform))
    SubdirData.clear_cached_local_channel_data()
    with env_var(
        "CONDA_USE_ONLY_TAR_BZ2", True, stack_callback=conda_tests_ctxt_mgmt_def_pol
    ):
        sd = SubdirData(channel)
        precs = tuple(sd.query("zlib"))
        assert precs[0].fn.endswith(".tar.bz2")
    SubdirData.clear_cached_local_channel_data()
    with env_var(
        "CONDA_USE_ONLY_TAR_BZ2", False, stack_callback=conda_tests_ctxt_mgmt_def_pol
    ):
        sd = SubdirData(channel)
        precs = tuple(sd.query("zlib"))
        assert precs[0].fn.endswith(".conda")


def test_subdir_data_coverage(platform=OVERRIDE_PLATFORM):
    class ChannelCacheClear:
        def __enter__(self):
            return

        def __exit__(self, *exc):
            Channel._cache_.clear()

    # disable SSL_VERIFY to cover 'turn off warnings' line
    with (
        ChannelCacheClear(),
        env_vars(
            {"CONDA_PLATFORM": platform, "CONDA_SSL_VERIFY": "false"},
            stack_callback=conda_tests_ctxt_mgmt_def_pol,
        ),
    ):
        channel = Channel(url_path(join(CHANNEL_DIR_V1, platform)))

        sd = SubdirData(channel)
        sd.load()
        assert all(isinstance(p, PackageRecord) for p in sd._package_records[1:])

        assert all(r.name == "zlib" for r in sd._iter_records_by_name("zlib"))  # type: ignore

        sd.reload()
        assert all(r.name == "zlib" for r in sd._iter_records_by_name("zlib"))  # type: ignore


def test_repodata_version_error(platform=OVERRIDE_PLATFORM):
    channel = Channel(url_path(join(CHANNEL_DIR_V1, platform)))

    # clear, to see our testing class
    SubdirData.clear_cached_local_channel_data(exclude_file=False)

    class SubdirDataRepodataTooNew(SubdirData):
        def _load(self):
            return {"repodata_version": 1024}

    with pytest.raises(CondaUpgradeError):
        SubdirDataRepodataTooNew(channel).load()

    SubdirData.clear_cached_local_channel_data(exclude_file=False)


@pytest.mark.parametrize(
    "creds",
    (
        pytest.param({"auth": None, "token": None}, id="no-credentials"),
        pytest.param({"auth": "user:password", "token": None}, id="with-auth"),
        pytest.param({"auth": None, "token": "123456abcdef"}, id="with-token"),
    ),
)
def test_repodata_version_2_base_url(
    monkeypatch: pytest.MonkeyPatch, creds: dict[str, str], platform=OVERRIDE_PLATFORM
):
    channel = Channel(url_path(join(CHANNEL_DIR_V2, platform)))
    channel_parts = channel.dump()
    base_url = f"https://repo.anaconda.com/pkgs/main/{platform}"
    if creds["auth"]:
        channel_parts["auth"] = creds["auth"]
        channel = Channel(**channel_parts)
        base_url_w_creds = (
            f"https://{creds['auth']}@repo.anaconda.com/pkgs/main/{platform}"
        )
    elif creds["token"]:
        channel_parts["token"] = creds["token"]
        channel = Channel(**channel_parts)
        base_url_w_creds = (
            f"https://repo.anaconda.com/t/{creds['token']}/pkgs/main/{platform}"
        )
    else:
        base_url_w_creds = base_url

    if creds["auth"] or creds["token"]:
        # Patch fetcher so it doesn't try to use the fake auth
        def _no_auth_repo(self):
            return self.repo_interface_cls(
                self.url_w_subdir,  # this is the patch
                repodata_fn=self.repodata_fn,
                cache=self.repo_cache,
            )

        monkeypatch.setattr(RepodataFetch, "_repo", property(_no_auth_repo))

    # clear, to see our testing class
    SubdirData.clear_cached_local_channel_data(exclude_file=False)

    subdir_data = SubdirData(channel).load()
    assert subdir_data._base_url == base_url
    for pkg in subdir_data.iter_records():
        assert pkg.url.startswith(base_url_w_creds)

    SubdirData.clear_cached_local_channel_data(exclude_file=False)


def test_metadata_cache_works(mocker, platform=OVERRIDE_PLATFORM):
    channel = Channel(join(CHANNEL_DIR_V1, platform))
    SubdirData.clear_cached_local_channel_data()

    # Sadly, on Windows, st_mtime resolution is limited to 2 seconds. (See note in Python docs
    # on os.stat_result.)  To ensure that the timestamp on the existing JSON file is safely
    # in the past before this test starts, we need to wait for more than 2 seconds...

    sleep(3)

    RepoInterface = get_repo_interface()

    with env_vars(
        {"CONDA_PLATFORM": platform}, stack_callback=conda_tests_ctxt_mgmt_def_pol
    ):
        fetcher = mocker.patch.object(RepoInterface, "repodata", return_value="{}")
        if hasattr(RepoInterface, "repodata_parsed"):
            fetcher = mocker.patch.object(
                RepoInterface, "repodata_parsed", return_value={}
            )

        SubdirData(channel).cache_path_json.touch()

        sd_a = SubdirData(channel)
        tuple(sd_a.query("zlib"))
        assert fetcher.call_count == 1

        sd_b = SubdirData(channel)
        assert sd_b is sd_a
        tuple(sd_b.query("zlib"))
        assert fetcher.call_count == 1


def test_metadata_cache_clearing(mocker, platform=OVERRIDE_PLATFORM):
    channel = Channel(join(CHANNEL_DIR_V1, platform))
    SubdirData.clear_cached_local_channel_data()

    RepoInterface = get_repo_interface()

    with env_vars(
        {"CONDA_PLATFORM": platform}, stack_callback=conda_tests_ctxt_mgmt_def_pol
    ):
        fetcher = mocker.patch.object(RepoInterface, "repodata", return_value="{}")
        if hasattr(RepoInterface, "repodata_parsed"):
            fetcher = mocker.patch.object(
                RepoInterface, "repodata_parsed", return_value={}
            )
        SubdirData(channel).cache_path_json.touch()

        sd_a = SubdirData(channel)
        precs_a = tuple(sd_a.query("zlib"))
        assert fetcher.call_count == 1

        SubdirData.clear_cached_local_channel_data()

        sd_b = SubdirData(channel)
        assert sd_b is not sd_a
        precs_b = tuple(sd_b.query("zlib"))
        assert fetcher.call_count == 2
        assert precs_b == precs_a


def test_search_by_packagerecord(platform=OVERRIDE_PLATFORM):
    local_channel = Channel(join(CHANNEL_DIR_V1, platform))
    sd = SubdirData(channel=local_channel)

    # test slow "check against all packages" query
    assert len(tuple(sd.query("*[version=1.2.11]"))) >= 1

    # test search by PackageRecord
    assert any(sd.query(next(sd.query("zlib"))))  # type: ignore


def test_state_is_not_json(tmp_path, platform=OVERRIDE_PLATFORM):
    """
    SubdirData has a ValueError exception handler, that is hard to invoke
    currently.
    """
    local_channel = Channel(join(CHANNEL_DIR_V1, platform))

    bad_cache = tmp_path / "not_json.json"
    bad_cache.write_text("{}")

    class BadRepodataCache(RepodataCache):
        cache_path_state = bad_cache

    class BadRepodataFetch(RepodataFetch):
        @property
        def repo_cache(self) -> RepodataCache:
            return BadRepodataCache(self.cache_path_base, self.repodata_fn)

    class BadCacheSubdirData(SubdirData):
        @property
        def repo_fetch(self):
            return BadRepodataFetch(
                Path(self.cache_path_base),
                self.channel,
                self.repodata_fn,
                repo_interface_cls=CondaRepoInterface,
            )

    SubdirData.clear_cached_local_channel_data(exclude_file=False)
    sd: SubdirData = BadCacheSubdirData(channel=local_channel)

    with pytest.raises(CondaError):
        state = sd.repo_cache.load_state()
        # tortured way to get to old ValueError handler
        bad_cache.write_text("NOT JSON")
        sd._read_local_repodata(state)


def test_subdir_data_dict_state(platform=OVERRIDE_PLATFORM):
    """SubdirData can accept a dict instead of a RepodataState, for compatibility."""
    local_channel = Channel(join(CHANNEL_DIR_V1, platform))
    sd = SubdirData(channel=local_channel)
    sd._read_pickled({})  # type: ignore
