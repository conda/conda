# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import copy
import platform
from contextlib import nullcontext
from logging import getLogger
from typing import TYPE_CHECKING

import pytest

import conda
from conda.base.constants import DEFAULTS_CHANNEL_NAME
from conda.base.context import context, non_x86_machines
from conda.common.compat import on_linux, on_mac, on_win
from conda.core import index
from conda.core.index import (
    Index,
    calculate_channel_urls,
    check_allowlist,
    dist_str_in_index,
)
from conda.core.prefix_data import PrefixData
from conda.models.channel import Channel
from conda.models.enums import PackageType
from conda.models.match_spec import MatchSpec
from conda.models.records import PackageCacheRecord, PackageRecord, PrefixRecord

from ..core.test_subdir_data import platform_in_record
from ..data.pkg_cache import load_cache_entries

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

    from pytest import FixtureRequest, MonkeyPatch

    from conda.core.index import ReducedIndex

log = getLogger(__name__)


PLATFORMS = {
    ("Linux", "x86_64"): "linux-64",
    ("Linux", "aarch64"): "linux-aarch64",
    ("Darwin", "x86_64"): "osx-64",
    ("Darwin", "arm64"): "osx-arm64",
    ("Windows", "AMD64"): "win-64",
}

DEFAULTS_SAMPLE_PACKAGES = {
    "linux-64": {
        "channel": "pkgs/main/linux-64",
        "name": "aiohttp",
        "version": "2.3.9",
        "build": "py35_0",
        "build_number": 0,
        "subdir": "linux-64",
        "fn": "aiohttp-2.3.9-py35_0.conda",
    },
    "linux-aarch64": {
        "channel": "pkgs/main/linux-aarch64",
        "name": "aiohttp",
        "version": "3.10.11",
        "build": "py311h998d150_0",
        "build_number": 0,
        "subdir": "linux-aarch64",
    },
    "osx-64": {
        "channel": "pkgs/main/osx-64",
        "name": "aiohttp",
        "version": "2.3.9",
        "build": "py35_0",
        "build_number": 0,
        "subdir": "osx-64",
    },
    "osx-arm64": {
        "channel": "pkgs/main/osx-arm64",
        "name": "aiohttp",
        "version": "3.9.3",
        "build": "py310h80987f9_0",
        "build_number": 0,
        "subdir": "osx-arm64",
    },
    "win-64": {
        "channel": "pkgs/main/win-64",
        "name": "aiohttp",
        "version": "2.3.9",
        "build": "py35_0",
        "build_number": 0,
        "subdir": "win-64",
    },
}

CONDAFORGE_SAMPLE_PACKAGES = {
    "linux-64": {
        "channel": "conda-forge",
        "name": "vim",
        "version": "9.1.0356",
        "build": "py310pl5321hfe26b83_0",
        "build_number": 0,
        "subdir": "linux-64",
    },
    "linux-aarch64": {
        "channel": "conda-forge",
        "name": "vim",
        "version": "9.1.0356",
        "build": "py310pl5321hdc9b7a6_0",
        "build_number": 0,
        "subdir": "linux-aarch64",
    },
    "osx-64": {
        "channel": "conda-forge",
        "name": "vim",
        "version": "9.1.0356",
        "build": "py38pl5321h6d91244_0",
        "build_number": 0,
        "subdir": "osx-64",
    },
    "osx-arm64": {
        "channel": "conda-forge",
        "name": "vim",
        "version": "9.1.0356",
        "build": "py39pl5321h878be05_0",
        "build_number": 0,
        "subdir": "osx-arm64",
    },
    "win-64": {
        "channel": "conda-forge",
        "name": "vim",
        "version": "9.1.0356",
        "build": "py312h275cf98_0",
        "build_number": 0,
        "subdir": "win-64",
    },
}


@pytest.fixture
def pkg_cache_entries(mocker):
    miniconda_pkg_cache = load_cache_entries("miniconda.json")
    return miniconda_pkg_cache


@pytest.fixture(autouse=True)
def patch_pkg_cache(mocker, pkg_cache_entries):
    mocker.patch(
        "conda.core.package_cache_data.PackageCacheData.get_all_extracted_entries",
        lambda: pkg_cache_entries,
    )
    mocker.patch("conda.base.context.context.track_features", ("test_feature",))


def test_supplement_index_with_system() -> None:
    index = Index().system_packages

    has_virtual_pkgs = {
        rec.name for rec in index if rec.package_type == PackageType.VIRTUAL_SYSTEM
    }.issuperset
    if on_win:
        assert has_virtual_pkgs({"__win"})
    elif on_mac:
        assert has_virtual_pkgs({"__osx", "__unix"})
    elif on_linux:
        assert has_virtual_pkgs({"__glibc", "__linux", "__unix"})


@pytest.mark.skipif(
    context.subdir.split("-", 1)[1] not in {"32", "64", *non_x86_machines},
    reason=f"archspec not available for subdir {context.subdir}",
)
def test_supplement_index_with_system_archspec() -> None:
    index = Index().system_packages
    assert any(
        rec.package_type == PackageType.VIRTUAL_SYSTEM and rec.name == "__archspec"
        for rec in index
    )


def test_supplement_index_with_system_cuda(
    clear_cuda_version: None, monkeypatch: MonkeyPatch
) -> None:
    monkeypatch.setenv("CONDA_OVERRIDE_CUDA", "3.2")
    index = Index().system_packages

    cuda_pkg = next(iter(_ for _ in index if _.name == "__cuda"))
    assert cuda_pkg.version == "3.2"
    assert cuda_pkg.package_type == PackageType.VIRTUAL_SYSTEM


@pytest.mark.skipif(not on_mac, reason="osx-only test")
def test_supplement_index_with_system_osx(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("CONDA_OVERRIDE_OSX", "0.15")
    index = Index().system_packages

    osx_pkg = next(iter(_ for _ in index if _.name == "__osx"))
    assert osx_pkg.version == "0.15"
    assert osx_pkg.package_type == PackageType.VIRTUAL_SYSTEM


@pytest.mark.skipif(not on_linux, reason="linux-only test")
@pytest.mark.parametrize(
    "release_str,version",
    [
        ("1.2.3.4", "1.2.3.4"),  # old numbering system
        ("4.2", "4.2"),
        ("4.2.1", "4.2.1"),
        ("4.2.0-42-generic", "4.2.0"),
        ("5.4.89+", "5.4.89"),
        ("5.5-rc1", "5.5"),
        ("9.1.a", "9.1"),  # should probably be "0"
        ("9.1.a.2", "9.1"),  # should probably be "0"
        ("9.a.1", "0"),
    ],
)
def test_supplement_index_with_system_linux(
    release_str: str, version: str, monkeypatch: MonkeyPatch
) -> None:
    monkeypatch.setenv("CONDA_OVERRIDE_LINUX", release_str)
    index = Index().system_packages

    linux_pkg = next(iter(_ for _ in index if _.name == "__linux"))
    assert linux_pkg.version == version
    assert linux_pkg.package_type == PackageType.VIRTUAL_SYSTEM


@pytest.mark.skipif(on_win or on_mac, reason="linux-only test")
def test_supplement_index_with_system_glibc(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("CONDA_OVERRIDE_GLIBC", "2.10")
    index = Index().system_packages

    glibc_pkg = next(iter(_ for _ in index if _.name == "__glibc"))
    assert glibc_pkg.version == "2.10"
    assert glibc_pkg.package_type == PackageType.VIRTUAL_SYSTEM


@pytest.mark.integration
@pytest.mark.parametrize("platform", ["linux-64", "osx-64", "win-64"])
def test_get_index_platform(platform: str) -> None:
    index = Index(platform=platform)
    for dist, record in index.items():
        assert platform_in_record(platform, record), (platform, record.url)


def test_dist_str_in_index(test_recipes_channel: Path) -> None:
    idx = Index((Channel(str(test_recipes_channel)),), prepend=False)
    assert not dist_str_in_index(idx.data, "test-1.4.0-0")
    assert dist_str_in_index(idx.data, "other_dependent-1.0-0")


def test_calculate_channel_urls():
    urls = calculate_channel_urls(
        channel_urls=[DEFAULTS_CHANNEL_NAME], use_local=False, prepend=True
    )
    assert "https://repo.anaconda.com/pkgs/main/noarch" in urls
    assert len(urls) == 6 if on_win else 4


@pytest.mark.parametrize(
    "subdir",
    ["linux-64", "linux-aarch64", "osx-64", "osx-arm64", "win-64"]
)
@pytest.mark.memray
@pytest.mark.integration
def test_get_index_lazy(subdir):
    index = Index(channels=["defaults", "conda-forge"], platform=subdir)
    main_prec = PackageRecord(**DEFAULTS_SAMPLE_PACKAGES[subdir])
    conda_forge_prec = PackageRecord(**CONDAFORGE_SAMPLE_PACKAGES[subdir])

    assert main_prec == index[main_prec]
    assert conda_forge_prec == index[conda_forge_prec]


class TestIndex:
    @pytest.fixture(params=[False, True])
    def index(
        self,
        request: FixtureRequest,
        test_recipes_channel: Path,
        tmp_env: Path,
    ) -> Iterable[Index]:
        with tmp_env("dependent=2.0") as prefix:
            _index = Index(prefix=prefix, use_cache=True, use_system=True)
            if request.param:
                _index.data
            yield _index

    @pytest.fixture
    def reduced_index(self, index: Index) -> ReducedIndex:
        return index.get_reduced_index((MatchSpec("dependent=2.0"),))

    @pytest.fixture
    def valid_channel_entry(self, test_recipes_channel: Path) -> PackageRecord:
        return PackageRecord(
            channel=Channel(str(test_recipes_channel)),
            name="dependent",
            subdir="noarch",
            version="1.0",
            build_number=0,
            build="0",
            fn="dependent-1.0-0.tar.bz2",
        )

    @pytest.fixture
    def invalid_channel_entry(self, test_recipes_channel: Path) -> PackageRecord:
        return PackageRecord(
            channel=Channel(str(test_recipes_channel)),
            name="dependent-non-existent",
            subdir="noarch",
            version="1.0",
            build_number=0,
            build="0",
            fn="dependent-1.0-0.tar.bz2",
        )

    @pytest.fixture
    def valid_prefix_entry(self, test_recipes_channel: Path) -> PackageRecord:
        return PackageRecord(
            channel=Channel(str(test_recipes_channel)),
            name="dependent",
            subdir="noarch",
            version="2.0",
            build_number=0,
            build="0",
            fn="dependent-2.0-0.tar.bz2",
        )

    @pytest.fixture
    def valid_cache_entry(self):
        return PackageRecord(
            name="python",
            subdir="linux-64",
            version="3.12.4",
            channel="defaults",
            build_number=1,
            build="h5148396_1",
            fn="python-3.12.4-h5148396_1.conda",
        )

    @pytest.fixture
    def valid_feature(self):
        return PackageRecord.feature("test_feature")

    @pytest.fixture
    def invalid_feature(self):
        return PackageRecord.feature("test_feature_non_existent")

    @pytest.fixture
    def valid_system_package(self):
        return PackageRecord.virtual_package("__conda", conda.__version__)

    @pytest.fixture
    def invalid_system_package(self):
        return PackageRecord.virtual_package("__conda_invalid", conda.__version__)

    def test_init_use_local(self):
        index = Index(use_local=True, prepend=False)
        assert len(index.channels) == 1
        assert "local" in index.channels.keys()

    def test_init_conflicting_subdirs(self, mocker):
        log = mocker.patch("conda.core.index.log")
        platform = "linux-64"
        subdirs = ("linux-64",)
        _ = Index(platform=platform, subdirs=subdirs)
        assert len(log.method_calls) == 1
        log_call = log.method_calls[0]
        assert log_call.args == (
            "subdirs is %s, ignoring platform %s",
            subdirs,
            platform,
        )

    def test_init_prefix_path(self, tmp_path: Path):
        index = Index(prefix=tmp_path)
        assert index.prefix_data
        assert index.prefix_data.prefix_path == tmp_path

    def test_init_prefix_data(self, tmp_path: Path):
        index = Index(prefix=PrefixData(tmp_path))
        assert index.prefix_data
        assert index.prefix_data.prefix_path == tmp_path

    def test_cache_entries(self, index, pkg_cache_entries):
        cache_entries = index.cache_entries
        assert cache_entries == pkg_cache_entries

    def test_getitem_channel(self, index, valid_channel_entry):
        package_record = index[valid_channel_entry]
        assert type(package_record) is PackageRecord
        assert package_record == valid_channel_entry

    def test_getitem_channel_invalid(self, index, invalid_channel_entry):
        with pytest.raises(KeyError):
            _ = index[invalid_channel_entry]

    def test_getitem_prefix(self, index, valid_prefix_entry):
        prefix_record = index[valid_prefix_entry]
        assert type(prefix_record) is PrefixRecord
        assert prefix_record == valid_prefix_entry

    def test_getitem_cache(self, index, valid_cache_entry):
        cache_record = index[valid_cache_entry]
        assert type(cache_record) is PackageCacheRecord
        assert cache_record == valid_cache_entry

    def test_getitem_feature(self, index, valid_feature):
        feature_record = index[valid_feature]
        assert type(feature_record) is PackageRecord
        assert feature_record == valid_feature

    def test_getitem_feature_non_existent(self, index, invalid_feature):
        with pytest.raises(KeyError):
            _ = index[invalid_feature]

    def test_getitem_system_package_valid(self, index, valid_system_package):
        system_record = index[valid_system_package]
        assert system_record == valid_system_package
        assert type(system_record) is PackageRecord
        assert system_record.package_type == PackageType.VIRTUAL_SYSTEM

    def test_getitem_system_package_invalid(self, index, invalid_system_package):
        with pytest.raises(KeyError):
            _ = index[invalid_system_package]

    def test_contains_valid(self, index, valid_cache_entry):
        assert valid_cache_entry in index

    def test_contains_invalid(self, index, invalid_feature):
        assert invalid_feature not in index

    def test_copy(self, index):
        index_copy = copy.copy(index)
        assert index_copy == index

    def test_reduced_index(self, reduced_index):
        assert len(reduced_index) == (
            # tests/data/pkg_cache/miniconda.json has 75 packages, see patch_pkg_cache
            75
            # we have 1 feature, see patch_pkg_cache
            + 1
            # only 4 packages are loaded from tests/data/test-recipes/noarch/repodata.json
            + 4
            # each OS has different virtual packages
            + len(context.plugin_manager.get_virtual_package_records())
        )


def test_check_allowlist_deprecation_warning():
    """
    Ensure a deprecation warning is raised for ``check_allowlist``.

    Also used to ensure coverage on this code path
    """
    with pytest.deprecated_call():
        check_allowlist(("defaults",))


@pytest.mark.parametrize(
    "function,raises",
    [
        ("calculate_channel_urls", None),
    ],
)
def test_deprecations(function: str, raises: type[Exception] | None) -> None:
    raises_context = pytest.raises(raises) if raises else nullcontext()
    with pytest.deprecated_call(), raises_context:
        getattr(index, function)()
