# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from logging import getLogger
from os.path import join
from pathlib import Path
from time import sleep
from typing import TYPE_CHECKING

import pytest

from conda import CondaError
from conda.base.context import context, reset_context
from conda.core.index import Index
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

if TYPE_CHECKING:
    from pytest import MonkeyPatch

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
def test_get_index_no_platform_with_offline_cache(
    monkeypatch: MonkeyPatch, platform=OVERRIDE_PLATFORM
):
    monkeypatch.setenv("CONDA_REPODATA_TIMEOUT_SECS", "0")
    monkeypatch.setenv("CONDA_PLATFORM", platform)
    reset_context()

    channel_urls = ("https://repo.anaconda.com/pkgs/pro",)

    this_platform = context.subdir
    index = Index(channels=channel_urls, prepend=False)
    for dist, record in index.items():
        assert platform_in_record(this_platform, record), (
            this_platform,
            record.url,
        )

    monkeypatch.delenv("CONDA_REPODATA_TIMEOUT_SECS")
    monkeypatch.delenv("CONDA_PLATFORM")
    reset_context()

    # When use_cache=True (which is implicitly engaged when context.offline is
    # True), there may be additional items in the cache that are included in
    # the index. But where those items coincide with entries already in the
    # cache, they must not change the record in any way. TODO: add one or
    # more packages to the cache so these tests affirmatively exercise
    # supplement_index_from_cache on CI?

    for use_cache in (None, False, True):
        monkeypatch.setenv("CONDA_OFFLINE", "yes")
        reset_context()

        index2 = Index(channels=channel_urls, prepend=False, use_cache=use_cache)
        assert all(index2.get(k) == rec for k, rec in index.items())
        assert use_cache is not False or len(index) == len(index2)

    for use_cache in (False, True):
        monkeypatch.setenv("CONDA_REPODATA_TIMEOUT_SECS", "0")
        monkeypatch.setenv("CONDA_PLATFORM", "linux-64")
        reset_context()

        index3 = Index(channels=channel_urls, prepend=False, use_cache=use_cache)
        assert all(index3.get(k) == rec for k, rec in index.items())
        assert use_cache or len(index) == len(index3)

    # only works if CONDA_PLATFORM exists in tests/data/conda_format_repo
    # (test will not pass on newer platforms with default CONDA_PLATFORM =
    # 'osx-arm64' etc.)
    monkeypatch.setenv("CONDA_OFFLINE", "yes")
    monkeypatch.setenv("CONDA_PLATFORM", platform)
    reset_context()
    SubdirData._cache_.clear()

    local_channel = Channel(join(CHANNEL_DIR_V1, platform))
    offline_channels = [local_channel]
    online_channels = context.channels or ["defaults"]
    assert len(SubdirData.query_all("zlib", channels=offline_channels)) > 0
    assert len(SubdirData.query_all("zlib", channels=online_channels)) == 0

    monkeypatch.delenv("CONDA_PLATFORM")
    monkeypatch.delenv("CONDA_OFFLINE")
    reset_context()
    SubdirData._cache_.clear()

    assert len(SubdirData.query_all("zlib", channels=online_channels)) > 1

    # test load from cache
    monkeypatch.setenv("CONDA_USE_INDEX_CACHE", "true")
    reset_context()
    SubdirData._cache_.clear()

    sd = SubdirData(channel=local_channel)
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


def test_subdir_data_prefers_conda_to_tar_bz2(
    monkeypatch: MonkeyPatch, platform=OVERRIDE_PLATFORM
):
    # force these to False, because otherwise tests fail when run with old conda-build
    monkeypatch.setenv("CONDA_USE_ONLY_TAR_BZ2", "false")
    monkeypatch.setenv("CONDA_PLATFORM", platform)
    reset_context()

    channel = Channel(join(CHANNEL_DIR_V1, platform))
    sd = SubdirData(channel)
    precs = tuple(sd.query("zlib"))
    assert precs[0].fn.endswith(".conda")


def test_use_only_tar_bz2(monkeypatch: MonkeyPatch, platform=OVERRIDE_PLATFORM):
    channel = Channel(join(CHANNEL_DIR_V1, platform))
    SubdirData.clear_cached_local_channel_data()

    monkeypatch.setenv("CONDA_USE_ONLY_TAR_BZ2", "true")
    reset_context()

    sd = SubdirData(channel)
    precs = tuple(sd.query("zlib"))
    assert precs[0].fn.endswith(".tar.bz2")
    SubdirData.clear_cached_local_channel_data()

    monkeypatch.setenv("CONDA_USE_ONLY_TAR_BZ2", "false")
    reset_context()

    sd = SubdirData(channel)
    precs = tuple(sd.query("zlib"))
    assert precs[0].fn.endswith(".conda")


def test_subdir_data_coverage(monkeypatch: MonkeyPatch, platform=OVERRIDE_PLATFORM):
    # disable SSL_VERIFY to cover 'turn off warnings' line
    monkeypatch.setattr("conda.models.channel.Channel._cache_", {})
    monkeypatch.setenv("CONDA_PLATFORM", platform)
    monkeypatch.setenv("CONDA_SSL_VERIFY", "false")
    reset_context()

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
    monkeypatch: MonkeyPatch, creds: dict[str, str], platform=OVERRIDE_PLATFORM
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


def test_metadata_cache_works(
    mocker, monkeypatch: MonkeyPatch, platform=OVERRIDE_PLATFORM
):
    channel = Channel(join(CHANNEL_DIR_V1, platform))
    SubdirData.clear_cached_local_channel_data()

    # Sadly, on Windows, st_mtime resolution is limited to 2 seconds. (See note in Python docs
    # on os.stat_result.)  To ensure that the timestamp on the existing JSON file is safely
    # in the past before this test starts, we need to wait for more than 2 seconds...

    sleep(3)

    RepoInterface = get_repo_interface()

    monkeypatch.setenv("CONDA_PLATFORM", platform)
    reset_context()

    fetcher = mocker.patch.object(RepoInterface, "repodata", return_value="{}")
    if hasattr(RepoInterface, "repodata_parsed"):
        fetcher = mocker.patch.object(RepoInterface, "repodata_parsed", return_value={})

    SubdirData(channel).cache_path_json.touch()

    sd_a = SubdirData(channel)
    tuple(sd_a.query("zlib"))
    assert fetcher.call_count == 1

    sd_b = SubdirData(channel)
    assert sd_b is sd_a
    tuple(sd_b.query("zlib"))
    assert fetcher.call_count == 1


def test_metadata_cache_clearing(
    mocker, monkeypatch: MonkeyPatch, platform=OVERRIDE_PLATFORM
):
    channel = Channel(join(CHANNEL_DIR_V1, platform))
    SubdirData.clear_cached_local_channel_data()

    RepoInterface = get_repo_interface()

    monkeypatch.setenv("CONDA_PLATFORM", platform)
    reset_context()

    fetcher = mocker.patch.object(RepoInterface, "repodata", return_value="{}")
    if hasattr(RepoInterface, "repodata_parsed"):
        fetcher = mocker.patch.object(RepoInterface, "repodata_parsed", return_value={})
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


def test_key_equals_fn_for_traditional_packages(platform=OVERRIDE_PLATFORM):
    """For traditional conda packages, key equals fn."""
    local_channel = Channel(join(CHANNEL_DIR_V1, platform))
    sd = SubdirData(channel=local_channel)
    sd.load()

    for prec in sd.iter_records():
        # key should be set and equal to fn for traditional packages
        assert prec.key is not None
        assert prec.key == prec.fn
        # stem should strip the extension
        assert prec.stem == prec.fn.rsplit(".", 1)[0].replace(".tar", "")


@pytest.mark.parametrize(
    "key,fn,expected_stem",
    [
        pytest.param(
            "numpy-1.26.4-py312h8753938_0.conda",
            "numpy-1.26.4-py312h8753938_0.conda",
            "numpy-1.26.4-py312h8753938_0",
            id="conda-extension",
        ),
        pytest.param(
            "requests-2.32.3-py313h06a4308_0.tar.bz2",
            "requests-2.32.3-py313h06a4308_0.tar.bz2",
            "requests-2.32.3-py313h06a4308_0",
            id="tar-bz2-extension",
        ),
        pytest.param(
            "idna-3.10-py3_none_any_0",  # no extension (wheel key)
            "idna-3.10-py3-none-any.whl",  # actual filename
            "idna-3.10-py3_none_any_0",  # stem uses key unchanged
            id="wheel-key-no-extension",
        ),
    ],
)
def test_stem_with_various_extensions(key, fn, expected_stem):
    """stem property correctly handles different package extensions."""
    prec = PackageRecord(
        name="test",
        version="1.0",
        build="0",
        build_number=0,
        channel="defaults",
        subdir="linux-64",
        key=key,
        fn=fn,
    )
    assert prec.stem == expected_stem


def test_stem_falls_back_to_fn_when_no_key():
    """stem property falls back to fn when key is not set."""
    prec = PackageRecord(
        name="numpy",
        version="1.26.4",
        build="py312h8753938_0",
        build_number=0,
        channel="defaults",
        subdir="linux-64",
        fn="numpy-1.26.4-py312h8753938_0.conda",
    )
    # key is not set, so stem should use fn
    assert prec.key is None
    assert prec.stem == "numpy-1.26.4-py312h8753938_0"


def test_fn_preserved_when_in_repodata_entry():
    """When repodata entry has explicit fn, it should be preserved."""
    # Simulate what subdir_data does when processing repodata
    info = {
        "name": "idna",
        "version": "3.10",
        "build": "py3_none_any_0",
        "build_number": 0,
        "depends": [],
        "fn": "idna-3.10-py3-none-any.whl",  # explicit fn in entry
    }
    repodata_key = "idna-3.10-py3_none_any_0"  # dict key (no extension)

    # Simulate _process_raw_repodata logic
    info["key"] = repodata_key
    if "fn" not in info:
        info["fn"] = repodata_key
    if "url" not in info:
        info["url"] = f"https://example.com/{info['fn']}"

    # fn should be preserved, not overwritten with key
    assert info["fn"] == "idna-3.10-py3-none-any.whl"
    assert info["key"] == "idna-3.10-py3_none_any_0"
    assert info["url"] == "https://example.com/idna-3.10-py3-none-any.whl"


def test_fn_falls_back_to_key_when_not_in_entry():
    """When repodata entry has no fn, it should fall back to key."""
    # Simulate what subdir_data does when processing repodata
    info = {
        "name": "numpy",
        "version": "1.26.4",
        "build": "py312h8753938_0",
        "build_number": 0,
        "depends": [],
        # no "fn" in entry - typical for traditional conda packages
    }
    repodata_key = "numpy-1.26.4-py312h8753938_0.conda"

    # Simulate _process_raw_repodata logic
    info["key"] = repodata_key
    if "fn" not in info:
        info["fn"] = repodata_key
    if "url" not in info:
        info["url"] = f"https://example.com/{info['fn']}"

    # fn should fall back to key
    assert info["fn"] == "numpy-1.26.4-py312h8753938_0.conda"
    assert info["key"] == "numpy-1.26.4-py312h8753938_0.conda"
    assert info["url"] == "https://example.com/numpy-1.26.4-py312h8753938_0.conda"
