# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Per package cache link and writability policies."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from conda.auxlib.ish import dals
from conda.base.constants import PACKAGE_CACHE_MAGIC_FILE
from conda.base.context import Context, context, reset_context
from conda.common.compat import on_win
from conda.common.configuration import YamlRawParameter
from conda.common.serialize import yaml
from conda.core.package_cache_data import PackageCacheData
from conda.exceptions import NoWritablePkgsDirError
from conda.gateways.disk.delete import rm_rf
from conda.gateways.disk.permissions import make_read_only

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from conda.testing.fixtures import (
        CondaCLIFixture,
        PathFactoryFixture,
        TmpEnvFixture,
    )

pytestmark = [
    pytest.mark.skipif(
        on_win, reason="creating symlinks may require elevated privileges"
    ),
    # torn down after mocker, so context reloads without the test data
    pytest.mark.usefixtures("reset_conda_context", "test_recipes_channel"),
]

# provided by the shared (admin managed) cache
SHARED_PKG = "activate_deactivate_package"
SHARED_FILE = Path("etc", "conda", "activate.d", "activate.sh")

# never present in the shared cache, always a cache miss there
OTHER_PKG = "small-executable"
OTHER_FILE = Path("etc", "conda", "activate.d", "small_executable.sh")


def load_condarc(mocker: MockerFixture, string: str) -> None:
    """Load condarc test data the way ``tests/base/test_context.py`` does.

    Every CLI call reloads context from the search path, so that keeps
    returning the test data too.
    """
    rd = {
        "testdata": YamlRawParameter.make_raw_parameters("testdata", yaml.loads(string))
    }
    mocker.patch.object(Context, "_load_search_path", return_value=rd.items())
    reset_context("")
    context._set_raw_data(rd)
    PackageCacheData.clear()


def snapshot(path: Path) -> dict[Path, int]:
    return {p.relative_to(path): p.lstat().st_mtime_ns for p in path.rglob("*")}


def has_pkg(name: str, pkgs_dir: Path) -> bool:
    return any(p.name.startswith(f"{name}-") for p in pkgs_dir.iterdir())


@pytest.fixture
def shared_cache(
    path_factory: PathFactoryFixture,
    tmp_env: TmpEnvFixture,
    mocker: MockerFixture,
) -> Path:
    """A package cache holding an extracted ``SHARED_PKG``, as an admin would provide."""
    shared = path_factory("shared-pkgs")
    load_condarc(
        mocker,
        dals(
            f"""
            pkgs_dirs:
              - {shared}
            """
        ),
    )
    with tmp_env(SHARED_PKG) as prefix:
        # drop the hard links so the package is unused
        rm_rf(prefix)
    assert (shared / PACKAGE_CACHE_MAGIC_FILE).is_file()
    assert has_pkg(SHARED_PKG, shared)
    return shared


@pytest.fixture
def user_cache(path_factory: PathFactoryFixture) -> Path:
    return path_factory("user-pkgs")


@pytest.mark.parametrize(
    "allow_softlinks,always_softlink,hardlinks_supported,settings,expect_symlink",
    [
        pytest.param("true", "true", True, "", True, id="cache-always"),
        pytest.param("true", "false", False, "", True, id="cache-allow-hardlink-fails"),
        pytest.param("true", "false", True, "", False, id="cache-allow-hardlink-works"),
        pytest.param("false", "false", False, "", False, id="none-copies"),
        # more specific policy (defined on the pkgs_dir) overrides the global default
        pytest.param(
            "false", "false", False, "allow_softlinks: true", False, id="global-allow"
        ),
        pytest.param(
            "false", "false", True, "always_softlink: true", False, id="global-always"
        ),
    ],
)
def test_link_policy_of_cache(
    tmp_env: TmpEnvFixture,
    mocker: MockerFixture,
    user_cache: Path,
    allow_softlinks: str,
    always_softlink: str,
    hardlinks_supported: bool,
    settings: str,
    expect_symlink: bool,
):
    mocker.patch("conda.core.link.hardlink_supported", return_value=hardlinks_supported)
    load_condarc(
        mocker,
        dals(
            f"""
            pkgs_dirs:
              - path: {user_cache}
                allow_softlinks: {allow_softlinks}
                always_softlink: {always_softlink}
            """
        )
        + settings,
    )

    with tmp_env(OTHER_PKG) as prefix:
        target = prefix / OTHER_FILE
        assert target.is_file()
        assert target.is_symlink() == expect_symlink
        if expect_symlink:
            assert target.resolve().is_relative_to(user_cache.resolve())


def test_link_policy_follows_supplying_cache(
    tmp_env: TmpEnvFixture,
    mocker: MockerFixture,
    shared_cache: Path,
    user_cache: Path,
):
    load_condarc(
        mocker,
        dals(
            f"""
            pkgs_dirs:
              - path: {shared_cache}
                always_softlink: true
                read_only: true
              - {user_cache}
            """
        ),
    )

    with tmp_env(SHARED_PKG, OTHER_PKG) as prefix:
        # supplied by the shared cache: soft linked into it
        assert (prefix / SHARED_FILE).is_symlink()
        assert (prefix / SHARED_FILE).resolve().is_relative_to(shared_cache.resolve())

        # cache miss in the shared cache: fetched into, and linked from, the user cache
        assert not (prefix / OTHER_FILE).is_symlink()
        assert has_pkg(OTHER_PKG, user_cache)
        assert not has_pkg(OTHER_PKG, shared_cache)


@pytest.mark.parametrize(
    "policy,hardlinks_supported,settings,expect_shared_symlink,expect_other_symlink",
    [
        pytest.param(
            "always_softlink: true",
            True,
            "always_softlink: false",
            True,
            False,
            id="always-over-global-not-always",
        ),
        pytest.param(
            "always_softlink: false",
            True,
            "always_softlink: true",
            False,
            True,
            id="not-always-over-global-always",
        ),
        pytest.param(
            "allow_softlinks: true",
            False,
            "allow_softlinks: false",
            True,
            False,
            id="allow-over-global-disallow",
        ),
        pytest.param(
            "allow_softlinks: false",
            False,
            "allow_softlinks: true",
            False,
            True,
            id="disallow-over-global-allow",
        ),
    ],
)
def test_link_policy_overrides_global_for_its_cache_only(
    tmp_env: TmpEnvFixture,
    mocker: MockerFixture,
    shared_cache: Path,
    user_cache: Path,
    policy: str,
    hardlinks_supported: bool,
    settings: str,
    expect_shared_symlink: bool,
    expect_other_symlink: bool,
):
    mocker.patch("conda.core.link.hardlink_supported", return_value=hardlinks_supported)
    # the user cache comes first, so OTHER_PKG is downloaded there
    load_condarc(
        mocker,
        dals(
            f"""
            pkgs_dirs:
              - {user_cache}
              - path: {shared_cache}
                {policy}
            """
        )
        + settings,
    )

    with tmp_env(SHARED_PKG, OTHER_PKG) as prefix:
        # linked from the shared cache: its own policy applies
        assert (prefix / SHARED_FILE).is_file()
        assert (prefix / SHARED_FILE).is_symlink() == expect_shared_symlink
        if expect_shared_symlink:
            assert (
                (prefix / SHARED_FILE).resolve().is_relative_to(shared_cache.resolve())
            )

        # linked from the user cache: the global setting applies
        assert (prefix / OTHER_FILE).is_file()
        assert (prefix / OTHER_FILE).is_symlink() == expect_other_symlink
        assert has_pkg(OTHER_PKG, user_cache)
        assert not has_pkg(OTHER_PKG, shared_cache)


def test_read_only_cache_supplies_extracted_package(
    tmp_env: TmpEnvFixture,
    mocker: MockerFixture,
    shared_cache: Path,
    user_cache: Path,
):
    load_condarc(
        mocker,
        dals(
            f"""
            pkgs_dirs:
              - path: {shared_cache}
                read_only: true
              - {user_cache}
            """
        ),
    )
    before = snapshot(shared_cache)

    with tmp_env(SHARED_PKG) as prefix:
        assert (prefix / SHARED_FILE).is_file()

    assert snapshot(shared_cache) == before
    # nothing downloaded or extracted again
    assert not user_cache.exists() or not has_pkg(SHARED_PKG, user_cache)


def test_read_only_cache_miss_uses_next_writable_cache(
    tmp_env: TmpEnvFixture,
    mocker: MockerFixture,
    shared_cache: Path,
    user_cache: Path,
):
    load_condarc(
        mocker,
        dals(
            f"""
            pkgs_dirs:
              - path: {shared_cache}
                read_only: true
              - {user_cache}
            """
        ),
    )
    before = snapshot(shared_cache)

    with tmp_env(OTHER_PKG) as prefix:
        assert (prefix / OTHER_FILE).is_file()

    assert snapshot(shared_cache) == before
    assert has_pkg(OTHER_PKG, user_cache)


def test_read_only_cache_is_not_repaired(
    tmp_env: TmpEnvFixture,
    mocker: MockerFixture,
    shared_cache: Path,
    user_cache: Path,
):
    # tarball present but not extracted: normally conda would extract it in place
    (extracted,) = (
        p
        for p in shared_cache.iterdir()
        if p.is_dir() and p.name.startswith(SHARED_PKG)
    )
    rm_rf(extracted)

    load_condarc(
        mocker,
        dals(
            f"""
            pkgs_dirs:
              - path: {shared_cache}
                read_only: true
              - {user_cache}
            """
        ),
    )
    before = snapshot(shared_cache)

    with tmp_env(SHARED_PKG) as prefix:
        assert (prefix / SHARED_FILE).is_file()

    assert snapshot(shared_cache) == before
    assert has_pkg(SHARED_PKG, user_cache)


@pytest.mark.parametrize(
    "args",
    [
        ("--all",),
        ("--packages",),
        ("--tarballs",),
        ("--force-pkgs-dirs",),
    ],
    ids=lambda args: " ".join(args),
)
def test_read_only_cache_is_not_cleaned(
    conda_cli: CondaCLIFixture,
    mocker: MockerFixture,
    shared_cache: Path,
    user_cache: Path,
    args: tuple[str, ...],
):
    mocker.patch("conda.core.envs_manager.list_all_known_prefixes", return_value=[])
    load_condarc(
        mocker,
        dals(
            f"""
            pkgs_dirs:
              - path: {shared_cache}
                read_only: true
              - {user_cache}
            """
        ),
    )
    before = snapshot(shared_cache)

    conda_cli("clean", *args, "--yes")

    assert snapshot(shared_cache) == before


def test_configuration_cannot_grant_write_access(
    tmp_env: TmpEnvFixture,
    mocker: MockerFixture,
    shared_cache: Path,
    user_cache: Path,
):
    make_read_only(shared_cache / PACKAGE_CACHE_MAGIC_FILE)
    load_condarc(
        mocker,
        dals(
            f"""
            pkgs_dirs:
              - path: {shared_cache}
                read_only: false
              - {user_cache}
            """
        ),
    )
    before = snapshot(shared_cache)

    assert not PackageCacheData(str(shared_cache)).is_writable
    assert PackageCacheData.first_writable().pkgs_dir == str(user_cache)

    with tmp_env(OTHER_PKG):
        pass

    assert snapshot(shared_cache) == before
    assert has_pkg(OTHER_PKG, user_cache)


def test_all_caches_read_only(
    tmp_env: TmpEnvFixture,
    mocker: MockerFixture,
    path_factory: PathFactoryFixture,
    shared_cache: Path,
):
    # an empty admin cache ahead of the one holding the package
    empty_cache = path_factory("empty-pkgs")
    empty_cache.mkdir()
    (empty_cache / PACKAGE_CACHE_MAGIC_FILE).touch()

    load_condarc(
        mocker,
        dals(
            f"""
            pkgs_dirs:
              - path: {empty_cache}
                read_only: true
              - path: {shared_cache}
                read_only: true
            """
        ),
    )
    before = {cache: snapshot(cache) for cache in (empty_cache, shared_cache)}

    assert not PackageCacheData.writable_caches()

    with pytest.raises(NoWritablePkgsDirError):
        with tmp_env(OTHER_PKG):
            pass

    assert {cache: snapshot(cache) for cache in before} == before
