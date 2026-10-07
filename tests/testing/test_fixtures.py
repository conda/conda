# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from conda.base.context import context, reset_context
from conda.cli.main import main_subshell
from conda.common.url import path_to_url
from conda.core.prefix_data import PrefixData
from conda.exceptions import DryRunExit
from conda.models.records import PackageRecord
from conda.reporters import _get_render_func, get_spinner

if TYPE_CHECKING:
    from pathlib import Path

    from pytest import MonkeyPatch, Pytester

    from conda.testing.fixtures import (
        CondaCLIFixture,
        PathFactoryFixture,
        TmpChannelFixture,
        TmpEnvFixture,
        TmpRepodataChannelFixture,
    )

pytest_plugins = ["conda.testing.fixtures", "pytester"]


def test_conda_cli(conda_cli: CondaCLIFixture) -> None:
    stdout, stderr, err = conda_cli("info")
    assert stdout
    assert not stderr
    assert not err


def test_session_conda_cli(session_conda_cli: CondaCLIFixture) -> None:
    stdout, stderr, err = session_conda_cli("info")
    assert not stdout
    assert not stderr
    assert not err


def test_conda_cli_resets_context_after_unexpected_exception(
    conda_cli: CondaCLIFixture, mocker
) -> None:
    def raise_pending_deprecation_warning(*args: str) -> int:
        if args[0] == "install":
            main_subshell("info")
            get_spinner("Installing packages")
            raise PendingDeprecationWarning
        return main_subshell(*args)

    mocker.patch(
        "conda.testing.fixtures.main_subshell",
        side_effect=raise_pending_deprecation_warning,
    )

    with pytest.raises(PendingDeprecationWarning):
        conda_cli("install")

    assert not context.json
    assert not _get_render_func.cache_info().currsize

    stdout, stderr, code = conda_cli("info", "--json")
    assert code == 0, stderr
    assert stdout
    assert json.loads(stdout)
    assert not stderr
    assert context.json is False
    assert not _get_render_func.cache_info().currsize


def test_path_factory(path_factory: PathFactoryFixture) -> None:
    path = path_factory()
    assert not path.exists()
    assert path.parent.is_dir()


def test_path_factory_name_mode(path_factory: PathFactoryFixture) -> None:
    """Test path_factory with explicit name (whole path component)."""
    positional = path_factory("myfile.txt")
    named = path_factory(name="myfile.txt")
    assert positional.name == named.name == "myfile.txt"
    assert not positional.exists()
    assert not named.exists()


@pytest.mark.parametrize(
    "prefix,infix,suffix",
    [
        pytest.param(None, None, None, id="no parts"),
        pytest.param("prefix-", None, None, id="prefix only"),
        pytest.param(None, "!", None, id="infix only"),
        pytest.param(None, None, ".suffix", id="suffix only"),
        pytest.param("prefix-", "infix", ".suffix", id="all parts"),
    ],
)
def test_path_factory_parts_mode(
    path_factory: PathFactoryFixture,
    prefix: str | None,
    infix: str | None,
    suffix: str | None,
) -> None:
    """Test path_factory with prefix/infix/suffix parameters triggers parts mode with UUID defaults."""
    path = path_factory(prefix=prefix, infix=infix, suffix=suffix)
    length = 0
    if prefix is None:
        length += 4  # UUID prefix
    else:
        assert prefix in path.name
        length += len(prefix)
    if infix is None:
        length += 4  # UUID suffix
    else:
        assert infix in path.name
        length += len(infix)
    if suffix is None:
        length += 4  # UUID suffix
    else:
        assert suffix in path.name
        length += len(suffix)
    assert len(path.name) == length


def test_path_factory_mutual_exclusivity(path_factory: PathFactoryFixture) -> None:
    """Test that name and parts params are mutually exclusive."""
    with pytest.raises(ValueError, match="mutually exclusive"):
        path_factory(name="myfile.txt", prefix="pre_")
    with pytest.raises(ValueError, match="mutually exclusive"):
        path_factory(name="myfile.txt", infix="!")
    with pytest.raises(ValueError, match="mutually exclusive"):
        path_factory(name="myfile.txt", suffix="_suf")


def test_path_factory_uniqueness(path_factory: PathFactoryFixture) -> None:
    """Test that multiple calls generate unique paths."""
    paths = [path_factory(infix="!") for _ in range(10)]
    assert len(set(paths)) == 10  # All unique


def test_tmp_env(tmp_env: TmpEnvFixture) -> None:
    with tmp_env() as prefix:
        assert PrefixData(prefix).is_environment()


@pytest.mark.parametrize(
    "name,path_prefix,path_infix,path_suffix",
    [
        pytest.param(None, None, None, None, id="no parts"),
        pytest.param("name", None, None, None, id="name only"),
        pytest.param(None, "prefix-", None, None, id="prefix only"),
        pytest.param(None, None, "env", None, id="infix only"),
        pytest.param(None, None, None, "-suffix", id="suffix only"),
        pytest.param(None, "prefix-", "env", "suffix", id="all parts"),
    ],
)
def test_tmp_env_path_parts(
    tmp_env: TmpEnvFixture,
    name: str | None,
    path_prefix: str | None,
    path_infix: str | None,
    path_suffix: str | None,
) -> None:
    """Test tmp_env with path_infix for special character testing."""
    with tmp_env(
        name=name,
        path_prefix=path_prefix,
        path_infix=path_infix,
        path_suffix=path_suffix,
        shallow=True,
    ) as prefix:
        if name is not None:
            assert prefix.name == name
        if path_prefix is not None:
            assert path_prefix in prefix.name
        if path_infix is not None:
            assert path_infix in prefix.name
        if path_suffix is not None:
            assert path_suffix in prefix.name
        assert PrefixData(prefix).is_environment()


def test_tmp_env_mutual_exclusivity(tmp_env: TmpEnvFixture) -> None:
    """Test that prefix, name, and path_* params are mutually exclusive."""
    with pytest.raises(ValueError, match="mutually exclusive"):
        with tmp_env(prefix="prefix", name="name"):
            pass
    with pytest.raises(ValueError, match="mutually exclusive"):
        with tmp_env(prefix="prefix", path_prefix="prefix"):
            pass
    with pytest.raises(ValueError, match="mutually exclusive"):
        with tmp_env(prefix="prefix", path_infix="infix"):
            pass
    with pytest.raises(ValueError, match="mutually exclusive"):
        with tmp_env(prefix="prefix", path_suffix="suffix"):
            pass


def test_empty_env(empty_env: Path) -> None:
    assert PrefixData(empty_env).is_environment()


def test_session_tmp_env(session_tmp_env: TmpEnvFixture) -> None:
    with session_tmp_env() as prefix:
        assert PrefixData(prefix).is_environment()


def test_env(pytester: Pytester) -> None:
    """Assert all tests get the same conda environment."""
    pytester.makepyfile(
        """
        import pytest

        pytest_plugins = "conda.testing.fixtures"

        @pytest.fixture
        def env1(tmp_env):
            with tmp_env() as prefix:
                yield prefix

        @pytest.fixture(scope="session")
        def env2(session_tmp_env):
            with session_tmp_env() as prefix:
                yield prefix

        @pytest.fixture(scope="session")
        def env3(session_tmp_env):
            with session_tmp_env() as prefix:
                yield prefix

        NAME = None

        def test_env1(env1):
            global NAME
            NAME = env1.name
            assert env1.name != "tmp_env-0"

        def test_env2(env1):
            assert env1.name != "tmp_env-0"
            assert env1.name != NAME

        def test_env3(env2):
            assert env2.name == "tmp_env-0"

        def test_env4(env2):
            assert env2.name == "tmp_env-0"

        def test_env5(env3):
            assert env3.name == "tmp_env-1"

        def test_env6(env3):
            assert env3.name == "tmp_env-1"
        """
    )
    result = pytester.runpytest()
    result.assert_outcomes(passed=6)


def _read_repodata(channel: Path, subdir: str) -> dict:
    return json.loads((channel / subdir / "repodata.json").read_text())


def test_tmp_repodata_channel_defaults(
    tmp_repodata_channel: TmpRepodataChannelFixture,
) -> None:
    channel, url = tmp_repodata_channel([{"name": "pkg"}])

    assert url == path_to_url(str(channel))
    assert {path.name for path in channel.iterdir()} == {"noarch", context.subdir}
    assert _read_repodata(channel, "noarch") == {
        "info": {"subdir": "noarch"},
        "packages": {
            "pkg-1.0-0.tar.bz2": {
                "name": "pkg",
                "version": "1.0",
                "build": "0",
                "build_number": 0,
                "depends": [],
                "subdir": "noarch",
                "noarch": "generic",
            }
        },
        "packages.conda": {},
        "repodata_version": 1,
    }
    if context.subdir != "noarch":
        assert _read_repodata(channel, context.subdir) == {
            "info": {"subdir": context.subdir},
            "packages": {},
            "packages.conda": {},
            "repodata_version": 1,
        }
    assert all(path.name == "repodata.json" for path in channel.rglob("*.*"))


def test_tmp_repodata_channel_overrides(
    tmp_repodata_channel: TmpRepodataChannelFixture,
) -> None:
    records = [
        {"name": "a"},
        {"name": "b", "version": "3.0", "depends": ["a"], "constrains": ["c <2"]},
    ]
    channel, _ = tmp_repodata_channel(
        records, version="2.0", build="custom_1", build_number=1, depends=["c"]
    )

    packages = _read_repodata(channel, "noarch")["packages"]
    assert packages["a-2.0-custom_1.tar.bz2"] == {
        "name": "a",
        "version": "2.0",
        "build": "custom_1",
        "build_number": 1,
        "depends": ["c"],
        "subdir": "noarch",
        "noarch": "generic",
    }
    assert packages["b-3.0-custom_1.tar.bz2"] == {
        "name": "b",
        "version": "3.0",
        "build": "custom_1",
        "build_number": 1,
        "depends": ["a"],
        "constrains": ["c <2"],
        "subdir": "noarch",
        "noarch": "generic",
    }
    assert records == [
        {"name": "a"},
        {"name": "b", "version": "3.0", "depends": ["a"], "constrains": ["c <2"]},
    ]


def test_tmp_repodata_channel_package_formats(
    tmp_repodata_channel: TmpRepodataChannelFixture,
) -> None:
    channel, _ = tmp_repodata_channel(
        [{"name": "a", "fn": "a-1.0-0.conda"}, {"name": "b"}]
    )

    repodata = _read_repodata(channel, "noarch")
    assert set(repodata["packages.conda"]) == {"a-1.0-0.conda"}
    assert set(repodata["packages"]) == {"b-1.0-0.tar.bz2"}
    assert "fn" not in repodata["packages.conda"]["a-1.0-0.conda"]
    assert "fn" not in repodata["packages"]["b-1.0-0.tar.bz2"]


@pytest.mark.parametrize("noarch", ["generic", "python"])
def test_tmp_repodata_channel_noarch_override(
    tmp_repodata_channel: TmpRepodataChannelFixture, noarch: str
) -> None:
    channel, _ = tmp_repodata_channel([{"name": "pkg", "noarch": noarch}])

    record = _read_repodata(channel, "noarch")["packages"]["pkg-1.0-0.tar.bz2"]
    assert record["noarch"] == noarch


@pytest.mark.parametrize(
    "subdirs",
    [None, [], ["osx-64"], ["linux-64", "linux-64"]],
)
def test_tmp_repodata_channel_subdirs(
    tmp_repodata_channel: TmpRepodataChannelFixture,
    subdirs: list[str] | None,
) -> None:
    channel, _ = tmp_repodata_channel(
        ({"name": name} for name in ("a", "b")), subdirs=subdirs, subdir="linux-64"
    )

    expected_subdirs = set(
        subdirs if subdirs is not None else ("noarch", context.subdir)
    )
    assert {path.name for path in channel.iterdir()} == expected_subdirs | {"linux-64"}
    repodata = _read_repodata(channel, "linux-64")
    assert repodata["info"] == {"subdir": "linux-64"}
    assert set(repodata["packages"]) == {"a-1.0-0.tar.bz2", "b-1.0-0.tar.bz2"}
    assert all("noarch" not in record for record in repodata["packages"].values())
    for subdir in expected_subdirs - {"linux-64"}:
        assert _read_repodata(channel, subdir) == {
            "info": {"subdir": subdir},
            "packages": {},
            "packages.conda": {},
            "repodata_version": 1,
        }


def test_tmp_repodata_channel_multiple_record_subdirs(
    tmp_repodata_channel: TmpRepodataChannelFixture,
) -> None:
    channel, _ = tmp_repodata_channel(
        [{"name": "a", "subdir": "linux-64"}, {"name": "b", "subdir": "noarch"}]
    )

    assert set(_read_repodata(channel, "linux-64")["packages"]) == {"a-1.0-0.tar.bz2"}
    assert set(_read_repodata(channel, "noarch")["packages"]) == {"b-1.0-0.tar.bz2"}


def test_tmp_repodata_channel_unique_paths(
    tmp_repodata_channel: TmpRepodataChannelFixture,
) -> None:
    first, first_url = tmp_repodata_channel([{"name": "pkg"}], version="2.0")
    second, second_url = tmp_repodata_channel([{"name": "pkg"}])

    assert first != second
    assert first_url != second_url
    assert set(_read_repodata(first, "noarch")["packages"]) == {"pkg-2.0-0.tar.bz2"}
    assert set(_read_repodata(second, "noarch")["packages"]) == {"pkg-1.0-0.tar.bz2"}


def test_tmp_repodata_channel_empty(
    tmp_repodata_channel: TmpRepodataChannelFixture,
) -> None:
    channel, _ = tmp_repodata_channel()

    for subdir in {"noarch", context.subdir}:
        assert _read_repodata(channel, subdir) == {
            "info": {"subdir": subdir},
            "packages": {},
            "packages.conda": {},
            "repodata_version": 1,
        }


def test_tmp_repodata_channel_package_record(
    tmp_repodata_channel: TmpRepodataChannelFixture,
) -> None:
    record = PackageRecord(
        name="a",
        version="1.0",
        build="0",
        build_number=0,
        subdir="noarch",
        channel="https://example.test/channel",
        fn="a-1.0-0.tar.bz2",
        url="https://example.test/channel/noarch/a-1.0-0.tar.bz2",
        depends=["b >=1"],
    )
    original = record.dump()
    channel, _ = tmp_repodata_channel([record], version="2.0")

    written = _read_repodata(channel, "noarch")["packages"]["a-1.0-0.tar.bz2"]
    assert written["name"] == "a"
    assert written["version"] == "1.0"
    assert written["depends"] == ["b >=1"]
    assert not {"url", "channel", "schannel", "channel_name"} & written.keys()
    assert record.dump() == original


@pytest.mark.usefixtures("parametrized_solver_fixture")
def test_tmp_repodata_channel_dry_run(
    tmp_repodata_channel: TmpRepodataChannelFixture,
    conda_cli: CondaCLIFixture,
    path_factory: PathFactoryFixture,
    tmp_pkgs_dir: Path,
) -> None:
    channel, url = tmp_repodata_channel(
        [
            {"name": "app", "depends": ["lib >=2"]},
            {"name": "lib"},
            {"name": "lib", "version": "2.0"},
        ]
    )
    prefix = path_factory()
    stdout, _, _ = conda_cli(
        "create",
        f"--prefix={prefix}",
        "--dry-run",
        "--json",
        "--override-channels",
        f"--channel={url}",
        "--repodata-fn=repodata.json",
        "--no-default-packages",
        "app",
        "--yes",
        raises=DryRunExit,
    )

    result = json.loads(stdout)
    assert result["success"]
    assert {
        (record["name"], record["version"]) for record in result["actions"]["LINK"]
    } == {
        ("app", "1.0"),
        ("lib", "2.0"),
    }
    assert not prefix.exists()
    assert all(path.name == "repodata.json" for path in channel.rglob("*.*"))


def test_tmp_channel(tmp_channel: TmpChannelFixture) -> None:
    with tmp_channel() as (channel, url):
        assert channel.is_dir()


def test_monkeypatch(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("CONDA_CLOBBER", "true")
    reset_context()
    assert context.clobber


def test_tmp_pkgs_dir(tmp_pkgs_dir: Path) -> None:
    assert tmp_pkgs_dir.is_dir()


def test_tmp_envs_dir(tmp_envs_dir: Path) -> None:
    assert tmp_envs_dir.is_dir()
