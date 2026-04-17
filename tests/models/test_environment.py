# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from __future__ import annotations

from dataclasses import fields
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest

from conda.base.constants import ChannelPriority
from conda.base.context import context, reset_context
from conda.core.prefix_data import PrefixData
from conda.exceptions import CondaValueError
from conda.models.environment import (
    EXTERNAL_PACKAGES_PYPI_KEY,
    Environment,
    EnvironmentConfig,
)
from conda.models.match_spec import MatchSpec
from conda.models.prefix_graph import PrefixGraph
from conda.models.records import PackageRecord
from conda.plugins.types import EnvironmentSpecBase

if TYPE_CHECKING:
    from pathlib import Path

    from pytest import MonkeyPatch
    from pytest_mock import MockerFixture

    from conda.testing.fixtures import PipCLIFixture, TmpEnvFixture


class FixedEnvSpec(EnvironmentSpecBase):
    """Minimal `EnvironmentSpecBase` that returns a pre-built `Environment`."""

    def __init__(self, env: Environment):
        self._env = env

    def can_handle(self) -> bool:
        return True

    @property
    def env(self) -> Environment:
        return self._env

    @property
    def available_platforms(self) -> tuple[str, ...]:
        return (self._env.platform,)

    def env_for(self, platform: str) -> Environment:
        if platform != self._env.platform:
            raise ValueError(
                f"Platform {platform!r} not available. "
                f"Available platforms: {self._env.platform}"
            )
        return self._env


class MultiPlatformEnvSpec(EnvironmentSpecBase):
    """`EnvironmentSpecBase` covering multiple platforms, one `Environment` per call."""

    def __init__(self, platforms: tuple[str, ...]):
        self._platforms = platforms

    def can_handle(self) -> bool:
        return True

    @property
    def env(self) -> Environment:
        return self.env_for(self._platforms[0])

    @property
    def available_platforms(self) -> tuple[str, ...]:
        return self._platforms

    def env_for(self, platform: str) -> Environment:
        if platform not in self._platforms:
            raise ValueError(
                f"Platform {platform!r} not available. "
                f"Available platforms: {', '.join(self._platforms)}"
            )
        return Environment(
            prefix="/path",
            platform=platform,
            requested_packages=[MatchSpec("numpy")],
            explicit_packages=[],
        )


def test_create_environment_missing_required_fields():
    with pytest.raises(CondaValueError):
        Environment(platform=None, prefix="/path/to/env")


def test_create_invalid_platform():
    with pytest.raises(CondaValueError):
        Environment(platform="idontexist", prefix="/path/to/env")


def test_ensure_no_duplicate_named_explicit_packages():
    test_record_one = PackageRecord(
        name="test",
        version="1.0",
        build="1",
        channel="defaults",
        subdir="noarch",
        build_number=1,
    )
    test_record_two = PackageRecord(
        name="test",
        version="2.0",
        build="1",
        channel="defaults",
        subdir="noarch",
        build_number=1,
    )
    with pytest.raises(CondaValueError):
        Environment(
            platform="linux-64",
            prefix="/path/to/env",
            explicit_packages=[test_record_one, test_record_two],
        )


def test_create_missing_explicit_package():
    test_record_one = PackageRecord(
        name="test",
        version="1.0",
        build="1",
        channel="defaults",
        subdir="noarch",
        build_number=1,
    )
    with pytest.raises(CondaValueError):
        Environment(
            platform="linux-64",
            prefix="/path/to/env",
            explicit_packages=[test_record_one],
            requested_packages=[MatchSpec("test"), MatchSpec("pandas")],
        )


def test_environments_merge():
    env1 = Environment(
        prefix="/path/to/env1",
        platform="linux-64",
        config=EnvironmentConfig(
            aggressive_update_packages=("abc",),
            channels=("defaults",),
            channel_settings=({"channel": "one", "a": 1},),
        ),
        external_packages={
            EXTERNAL_PACKAGES_PYPI_KEY: ["one", "two", {"special": "type"}],
            "other": ["three"],
        },
        explicit_packages=[],
        requested_packages=[MatchSpec("numpy"), MatchSpec("pandas")],
        variables={"PATH": "/usr/bin"},
        virtual_packages=[PackageRecord.virtual_package("vp", "1.2.3", "44")],
    )
    env2 = Environment(
        prefix="/path/to/env1",
        platform="linux-64",
        config=EnvironmentConfig(
            aggressive_update_packages=("two",),
            channels=("conda-forge",),
            channel_settings=({"channel": "two", "b": 2},),
            repodata_fns=("repodata2.json",),
        ),
        external_packages={
            EXTERNAL_PACKAGES_PYPI_KEY: ["two", "flask"],
            "a": ["nother"],
        },
        explicit_packages=[],
        requested_packages=[MatchSpec("numpy"), MatchSpec("flask")],
        variables={"VAR": "IABLE"},
        virtual_packages=[PackageRecord.virtual_package("vp2", "3.2.1", "1")],
    )
    merged = Environment.merge(env1, env2)
    assert merged.prefix == "/path/to/env1"
    assert merged.platform == "linux-64"
    assert merged.config == EnvironmentConfig(
        aggressive_update_packages=(
            "abc",
            "two",
        ),
        channels=(
            "conda-forge",
            "defaults",
        ),
        channel_settings=(
            {"channel": "one", "a": 1},
            {"channel": "two", "b": 2},
        ),
        repodata_fns=("repodata2.json",),
    )
    assert merged.external_packages == {
        EXTERNAL_PACKAGES_PYPI_KEY: ["one", "two", {"special": "type"}, "flask"],
        "other": ["three"],
        "a": ["nother"],
    }
    assert set(merged.requested_packages) == set(
        [MatchSpec("pandas"), MatchSpec("flask"), MatchSpec("numpy")]
    )
    assert merged.variables == {"PATH": "/usr/bin", "VAR": "IABLE"}
    assert merged.virtual_packages == [
        PackageRecord.virtual_package("vp", "1.2.3", "44"),
        PackageRecord.virtual_package("vp2", "3.2.1", "1"),
    ]


def test_environments_merge_explicit_packages():
    somepackage = PackageRecord(
        name="somepackage",
        version="1.0",
        build="1",
        channel="defaults",
        subdir="noarch",
        build_number=1,
    )
    somepackageother = PackageRecord(
        name="somepackageother",
        version="1.0",
        build="1",
        channel="defaults",
        subdir="noarch",
        build_number=1,
    )
    env1 = Environment(
        prefix="/path/to/env1",
        platform="linux-64",
        explicit_packages=[somepackage],
    )
    env2 = Environment(
        prefix="/path/to/env1",
        platform="linux-64",
        explicit_packages=[somepackage, somepackageother],
    )
    merged = Environment.merge(env1, env2)
    assert merged.prefix == "/path/to/env1"
    assert merged.platform == "linux-64"
    assert merged.explicit_packages == [somepackage, somepackageother]


def test_environments_merge_colliding_platform():
    env1 = Environment(prefix="/path/to/env1", platform="linux-64")
    env2 = Environment(prefix="/path/to/env2", platform="osx-64")

    with pytest.raises(CondaValueError):
        Environment.merge(env1, env2)


def test_environments_merge_colliding_name():
    env1 = Environment(
        prefix="/path/to/env1",
        platform="linux-64",
        name="one",
    )
    env2 = Environment(
        prefix="/path/to/env1",
        platform="linux-64",
        name="two",
    )
    merged = Environment.merge(env1, env2)
    assert merged.prefix == "/path/to/env1"
    assert merged.platform == "linux-64"
    assert merged.name == "two"


def test_environments_merge_colliding_prefix():
    env1 = Environment(
        prefix="/path/to/env1",
        platform="linux-64",
    )
    env2 = Environment(
        prefix="/path/to/env2",
        platform="linux-64",
    )
    merged = Environment.merge(env1, env2)
    assert merged.prefix == "/path/to/env2"
    assert merged.platform == "linux-64"


def test_merge_configs_primitive_values_order_one():
    config1 = EnvironmentConfig(
        use_only_tar_bz2=True,
    )
    config2 = EnvironmentConfig(
        use_only_tar_bz2=False,
    )

    result = EnvironmentConfig.merge(config1, config2)
    assert result.use_only_tar_bz2 is False


def test_merge_configs_primitive_values_order_two():
    config1 = EnvironmentConfig(
        use_only_tar_bz2=True,
    )
    config2 = EnvironmentConfig(
        use_only_tar_bz2=False,
    )
    result = EnvironmentConfig.merge(config2, config1)
    assert result.use_only_tar_bz2 is True


def test_merge_configs_primitive_none_values_order():
    config1 = EnvironmentConfig(
        use_only_tar_bz2=True,
    )
    config2 = EnvironmentConfig()

    result = EnvironmentConfig.merge(config1, config2)
    assert result.use_only_tar_bz2 is True

    result = EnvironmentConfig.merge(config2, config1)
    assert result.use_only_tar_bz2 is True


def test_merge_configs_channel_order_last_wins():
    """Later config's channels take precedence (e.g. conda create -f env.yaml -c conda-forge)."""
    file_config = EnvironmentConfig(channels=("defaults",))
    cli_config = EnvironmentConfig(channels=("conda-forge", "defaults"))
    result = EnvironmentConfig.merge(file_config, cli_config)
    assert result.channels == ("conda-forge", "defaults")


def test_config_from_cli_channels_empty():
    args = SimpleNamespace()
    config = EnvironmentConfig.from_cli_channels(args)
    assert config.channels == ()
    assert config == EnvironmentConfig()


def test_config_from_cli_channels_behaviors():
    config = EnvironmentConfig.from_cli_channels(
        SimpleNamespace(channel=["conda-forge", "r"])
    )
    assert config.channels == ("conda-forge", "r")

    config = EnvironmentConfig.from_cli_channels(SimpleNamespace(use_local=True))
    assert config.channels == ("local",)

    config = EnvironmentConfig.from_cli_channels(
        SimpleNamespace(use_local=True, channel=["conda-forge"])
    )
    assert config.channels == ("local", "conda-forge")


def test_from_cli_override_channels_excludes_file_channels(mocker: MockerFixture):
    """conda create -f env.yaml -c conda-forge --override-channels uses only -c channels.

    File channels are excluded when override_channels is set.
    """
    file_env = Environment(
        prefix="/path",
        platform=context.subdir,
        requested_packages=[MatchSpec("numpy")],
        explicit_packages=[],
        config=EnvironmentConfig(channels=("defaults", "my-channel")),
    )

    mocker.patch(
        "conda.models.environment.context.plugin_manager.get_environment_specifier",
        return_value=SimpleNamespace(
            environment_spec=lambda fpath: FixedEnvSpec(file_env)
        ),
    )

    env = Environment.from_cli(
        SimpleNamespace(
            name="testenv",
            packages=[],
            file=["/some/env.yaml"],
            channel=["conda-forge"],
            override_channels=True,
        )
    )
    assert env.config.channels == ("conda-forge",)


def test_from_cli_channel_order_base_file_cli(mocker: MockerFixture):
    """conda create -f env.yaml -c cli-chan merges base, file, CLI channels: CLI > file > configs."""
    # The context contains both the .condarc settings and the CLI settings
    context_config = EnvironmentConfig(channels=("base-channel", "cli-channel"))
    file_env = Environment(
        prefix="/path",
        platform=context.subdir,
        requested_packages=[MatchSpec("numpy")],
        explicit_packages=[],
        config=EnvironmentConfig(channels=("file-channel",)),
    )
    mocker.patch(
        "conda.models.environment.context.plugin_manager.get_environment_specifier",
        return_value=SimpleNamespace(
            environment_spec=lambda fpath: FixedEnvSpec(file_env)
        ),
    )
    mocker.patch(
        "conda.models.environment.EnvironmentConfig.from_context",
        return_value=context_config,
    )

    env = Environment.from_cli(
        SimpleNamespace(
            name="testenv",
            packages=[],
            file=["/some/env.yaml"],
            channel=["cli-channel"],
        ),
        add_default_packages=False,
    )
    assert env.config.channels == ("cli-channel", "file-channel", "base-channel")


def test_merge_configs_deduplicate_values():
    config1 = EnvironmentConfig(
        channels=(
            "defaults",
            "conda-forge",
        ),
        disallowed_packages=("a",),
        pinned_packages=("b",),
        repodata_fns=("repodata.json",),
        track_features=("track",),
    )
    config2 = EnvironmentConfig(
        channels=(
            "defaults",
            "my-channel",
        ),
        disallowed_packages=("a",),
        pinned_packages=("b",),
        repodata_fns=("repodata.json",),
        track_features=("track",),
    )
    config3 = EnvironmentConfig(
        channels=(
            "conda-forge",
            "b-channel",
        ),
    )

    result = EnvironmentConfig.merge(config1, config2, config3)
    assert result.channels == (
        "conda-forge",
        "b-channel",
        "defaults",
        "my-channel",
    )
    assert result.disallowed_packages == ("a",)
    assert result.pinned_packages == ("b",)
    assert result.repodata_fns == ("repodata.json",)
    assert result.track_features == ("track",)


def test_environment_config_from_context(context_testdata):
    config = EnvironmentConfig.from_context()

    # Check that some of the config values have been populated from the context
    assert config.channel_priority == ChannelPriority.DISABLED

    # Check that the types are matching up with the default type
    for field in fields(EnvironmentConfig):
        if field.default:
            assert isinstance(getattr(config, field.name), field.default_factory), (
                f"{field.name} expected to be a {field.default_factory} but is a {type(getattr(config, field.name))}"
            )


def test_merge_channel_settings():
    config1 = EnvironmentConfig(
        channel_settings=(
            {"channel": "one", "param_one": "val_one", "param_two": "val_two"},
            {"channel": "two", "param_three": "val_three"},
        ),
    )
    config2 = EnvironmentConfig(
        channel_settings=(
            {
                "channel": "one",
                "other_val": "yes",
            },
            {"channel": "three", "param_three": "val_three"},
        )
    )
    config3 = EnvironmentConfig(channel_settings=({"some": "stuff"},))
    result = EnvironmentConfig.merge(config1, config2, config3)
    expected = EnvironmentConfig(
        channel_settings=(
            {
                "channel": "one",
                "param_one": "val_one",
                "param_two": "val_two",
                "other_val": "yes",
            },
            {"channel": "two", "param_three": "val_three"},
            {"channel": "three", "param_three": "val_three"},
            {"some": "stuff"},
        ),
    )
    assert result == expected


@pytest.mark.integration
def test_from_prefix_package_population_semantics(tmp_env: TmpEnvFixture):
    """Test that explicit_packages and requested_packages are populated with correct semantics."""
    with tmp_env("zlib") as prefix:
        env_history = Environment.from_prefix(
            str(prefix), "test", "linux-64", from_history=True
        )
        env_normal = Environment.from_prefix(
            str(prefix), "test", "linux-64", from_history=False
        )

        # explicit_packages: always PackageRecords from prefix (regardless of from_history)
        for env in [env_history, env_normal]:
            assert len(env.explicit_packages) > 0
            assert all(isinstance(pkg, PackageRecord) for pkg in env.explicit_packages)
            assert "zlib" in {pkg.name for pkg in env.explicit_packages}

        # requested_packages: always MatchSpecs, both populated
        for env in [env_history, env_normal]:
            assert len(env.requested_packages) > 0
            assert all(isinstance(spec, MatchSpec) for spec in env.requested_packages)


@pytest.mark.integration
def test_from_prefix_options_affect_correct_packages(tmp_env: TmpEnvFixture):
    """Test that command-line options affect requested_packages but not explicit_packages."""
    with tmp_env("zlib") as prefix:
        env_default = Environment.from_prefix(str(prefix), "test", "linux-64")
        env_no_builds = Environment.from_prefix(
            str(prefix), "test", "linux-64", no_builds=True
        )
        env_no_channels = Environment.from_prefix(
            str(prefix), "test", "linux-64", ignore_channels=True
        )

        # explicit_packages identical across all options (always PackageRecords)
        pkg_count = len(env_default.explicit_packages)
        assert len(env_no_builds.explicit_packages) == pkg_count
        assert len(env_no_channels.explicit_packages) == pkg_count

        # Options affect requested_packages format
        default_spec = str(env_default.requested_packages[0])
        no_builds_spec = str(env_no_builds.requested_packages[0])
        no_channels_specs = [str(s) for s in env_no_channels.requested_packages]

        # no_builds: fewer "=" signs (no build string)
        assert default_spec.count("=") > no_builds_spec.count("=")

        # ignore_channels: no "::" in specs
        assert not any("::" in spec for spec in no_channels_specs)


def test_from_prefix_behavior_with_pip_interoperability(
    tmp_env: TmpEnvFixture, pip_cli: PipCLIFixture, wheelhouse: Path
):
    """Test that extrapolating an env from a prefix behaves correctly with conda and pip packages."""
    # Create environment with conda packages and pip
    packages = ["python=3.13", "pip"]
    with tmp_env(*packages) as prefix:
        # Install small-python-package wheel for testing pip interoperability
        wheel_path = wheelhouse / "small_python_package-1.0.0-py3-none-any.whl"
        pip_stdout, pip_stderr, pip_code = pip_cli(
            "install", str(wheel_path), prefix=prefix
        )
        assert pip_code == 0, f"pip install failed: {pip_stderr}"

        # Clear prefix data cache to ensure fresh data
        PrefixData._cache_.clear()

        env = Environment.from_prefix(
            str(prefix), "test", context.subdir, from_history=False
        )

        # Check that expected conda packages are present. Note, purposefully leaving out some packages
        # that are not common for all platforms.
        expected_conda_explicit_names = [
            "python",
            "python_abi",
            "pip",
            "tk",
            "bzip2",
            "openssl",
            "ca-certificates",
        ]
        actual_explicit_package_names = [pkg.name for pkg in env.explicit_packages]
        for pkg in expected_conda_explicit_names:
            assert pkg in actual_explicit_package_names

        # Check that the pip install package is present in the set of externally
        # managed packages, but not in the explicit packages
        assert len(env.external_packages[EXTERNAL_PACKAGES_PYPI_KEY]) == 1
        assert (
            "small-python-package==1.0.0"
            == env.external_packages[EXTERNAL_PACKAGES_PYPI_KEY][0]
        )
        assert "small-python-package" not in [pkg.name for pkg in env.explicit_packages]


def test_environment_config_channels_basic():
    """Test that environment config channels work as expected."""
    env_config = EnvironmentConfig(channels=["conda-forge", "defaults"])

    assert "conda-forge" in env_config.channels
    assert "defaults" in env_config.channels
    assert len(env_config.channels) == 2


def test_from_cli_empty():
    env = Environment.from_cli(
        SimpleNamespace(name=None, packages=[], file=[]),
    )
    assert env.config == EnvironmentConfig.from_context()


def test_from_cli_empty_with_default_packages(
    monkeypatch: MonkeyPatch,
):
    # Setup the default packages. Expect this to inject python==3.13
    monkeypatch.setenv("CONDA_CREATE_DEFAULT_PACKAGES", "python==3.13")
    reset_context()

    env = Environment.from_cli(
        SimpleNamespace(name=None, packages=[], file=[]),
        add_default_packages=True,
    )
    assert env.config == EnvironmentConfig.from_context()
    assert env.requested_packages == [MatchSpec("python==3.13")]


def test_from_cli_with_specs():
    env = Environment.from_cli(
        SimpleNamespace(
            name="testenv",
            packages=["numpy", "scipy=1.*"],
            file=[],
        ),
    )
    assert env.config == EnvironmentConfig.from_context()
    assert env.name == "testenv"
    assert env.requested_packages == [MatchSpec("numpy"), MatchSpec("scipy=1.*")]
    assert env.explicit_packages == []


@pytest.mark.parametrize(
    "files_platforms,expected_in_error",
    [
        pytest.param(
            [("/tmp/a.yml", ("linux-64", "win-64"))],
            ["/tmp/a.yml"],
            id="single-incompatible",
        ),
        pytest.param(
            [
                ("/tmp/a.yml", ("linux-64", "win-64")),
                ("/tmp/b.lock", ("linux-64", "win-64")),
            ],
            ["/tmp/a.yml", "/tmp/b.lock"],
            id="multiple-incompatible",
        ),
    ],
)
def test_from_cli_pre_flight_rejects_incompatible_files(
    mocker: MockerFixture,
    files_platforms: list[tuple[str, tuple[str, ...]]],
    expected_in_error: list[str],
):
    """Pre-flight pass reports every file that does not cover `context.subdir`."""
    specs_by_path = {fp: MultiPlatformEnvSpec(plats) for fp, plats in files_platforms}
    mocker.patch(
        "conda.models.environment.context.plugin_manager.get_environment_specifier",
        return_value=SimpleNamespace(
            environment_spec=lambda fpath: specs_by_path[fpath]
        ),
    )
    with pytest.raises(CondaValueError) as exc_info:
        Environment.from_cli(
            SimpleNamespace(
                name="testenv",
                packages=[],
                file=list(specs_by_path),
            )
        )
    msg = str(exc_info.value)
    assert f"do not include packages for {context.subdir}" in msg
    assert "--platform=<subdir>" in msg
    for fp in expected_in_error:
        assert fp in msg


def test_from_cli_accepts_multi_platform_file_covering_current(mocker: MockerFixture):
    """Multi-platform specs that cover `context.subdir` return only that platform's `Environment`."""
    spec = MultiPlatformEnvSpec(("linux-64", "osx-arm64", "win-64", context.subdir))
    mocker.patch(
        "conda.models.environment.context.plugin_manager.get_environment_specifier",
        return_value=SimpleNamespace(environment_spec=lambda fpath: spec),
    )
    env = Environment.from_cli(
        SimpleNamespace(
            name="testenv",
            packages=[],
            file=["/tmp/multi.lock"],
        )
    )
    assert env.platform == context.subdir


def test_from_cli_with_explicit_specs(mocker: MockerFixture):
    # Mock the function that retrieves explicit package records to return
    # a fake value. We'll use this to compare to the expected output.
    fake_explicit_records = ["/path/to/package/numpy.conda"]
    mocker.patch(
        "conda.models.environment.get_package_records_from_explicit",
        return_value=fake_explicit_records,
    )

    env = Environment.from_cli(
        SimpleNamespace(
            name="testenv",
            packages=["/path/to/package/numpy.conda"],
            file=[],
        ),
    )
    assert env.config == EnvironmentConfig.from_context()
    assert env.name == "testenv"
    assert env.requested_packages == []
    assert env.explicit_packages == fake_explicit_records


def test_from_cli_mix_explicit_and_specs():
    with pytest.raises(CondaValueError) as exc_info:
        Environment.from_cli(
            SimpleNamespace(
                name="testenv",
                packages=["numpy", "scipy=1.*", "/path/to/package/numpy.conda"],
                file=[],
            ),
        )
    assert "Cannot combine package names with explicit package lists" in str(exc_info)


def test_from_cli_with_files(mocker: MockerFixture):
    # Mock out extracting specs from a file by providing a list of specs.
    # This is similar output to extracting specs from a requirements.txt file.
    fake_specs = ["numpy", "python >=3.9"]
    fake_env = Environment(
        prefix="/path",
        platform=context.subdir,
        requested_packages=[MatchSpec(s) for s in fake_specs],
        explicit_packages=[],
        config=EnvironmentConfig.from_context(),
    )
    mock_spec = SimpleNamespace(
        environment_spec=lambda fpath: FixedEnvSpec(fake_env)
    )
    mocker.patch(
        "conda.models.environment.context.plugin_manager.get_environment_specifier",
        return_value=mock_spec,
    )

    env = Environment.from_cli(
        SimpleNamespace(
            name="testenv",
            packages=["scipy"],
            file=["/my/files/that/does/not/exist"],
        ),
        add_default_packages=True,
    )
    assert env.config == EnvironmentConfig.from_context()
    assert env.name == "testenv"
    assert env.requested_packages == [
        MatchSpec("numpy"),
        MatchSpec("python >=3.9"),
        MatchSpec("scipy"),
    ]
    assert env.explicit_packages == []


def test_from_cli_inject_default_packages_override(
    monkeypatch: MonkeyPatch,
):
    # Setup the default packages. Expect this to inject favicon and scipy=1.16.0
    monkeypatch.setenv("CONDA_CREATE_DEFAULT_PACKAGES", "favicon,scipy=1.16.0")
    reset_context()

    env = Environment.from_cli(
        SimpleNamespace(
            name="testenv",
            packages=["numpy"],
            file=[],
        ),
        add_default_packages=True,
    )
    assert env.config == EnvironmentConfig.from_context()
    assert env.name == "testenv"
    assert env.requested_packages == [
        MatchSpec("numpy"),
        MatchSpec("favicon"),
        MatchSpec("scipy=1.16.0"),
    ]
    assert env.explicit_packages == []

    env = Environment.from_cli(
        SimpleNamespace(
            name="testenv",
            packages=["numpy", "scipy=1.*"],
            file=[],
        ),
        add_default_packages=False,
    )
    assert env.config == EnvironmentConfig.from_context()
    assert env.name == "testenv"
    assert env.requested_packages == [MatchSpec("numpy"), MatchSpec("scipy=1.*")]
    assert env.explicit_packages == []

    env = Environment.from_cli(
        SimpleNamespace(
            name="testenv",
            packages=["numpy", "scipy=1.*"],
            file=[],
        ),
        add_default_packages=True,
    )
    assert env.config == EnvironmentConfig.from_context()
    assert env.name == "testenv"
    assert env.requested_packages == [
        MatchSpec("numpy"),
        MatchSpec("scipy=1.*"),
        MatchSpec("favicon"),
    ]
    assert env.explicit_packages == []


def test_from_cli_environment_inject_default_packages_override_file(
    monkeypatch: MonkeyPatch, mocker: MockerFixture
):
    # Setup the default packages. Expect this to inject favicon and numpy==2.0.0
    monkeypatch.setenv("CONDA_CREATE_DEFAULT_PACKAGES", "favicon,numpy==2.0.0")
    reset_context()

    # Mock env spec plugin returning env with numpy==2.3.1
    fake_env = Environment(
        platform=context.subdir,
        requested_packages=[MatchSpec("numpy==2.3.1")],
    )
    mock_spec = FixedEnvSpec(fake_env)
    mock_hook = type("Hook", (), {"environment_spec": lambda self, path: mock_spec})()
    mocker.patch(
        "conda.models.environment.context.plugin_manager.get_environment_specifier",
        return_value=mock_hook,
    )

    env = Environment.from_cli(
        SimpleNamespace(
            name="testenv",
            packages=[],
            file=["/i/dont/exist"],
        ),
        add_default_packages=True,
    )
    assert env.config == EnvironmentConfig.from_context()
    assert env.name == "testenv"
    assert MatchSpec("numpy==2.0.0") not in env.requested_packages
    assert MatchSpec("numpy==2.3.1") in env.requested_packages
    assert env.explicit_packages == []


def test_extrapolate(tmp_env: TmpEnvFixture):
    package_name = "zlib"
    package_version = "1.2.12"
    platforms = {"linux-64", "osx-arm64", "win-64"}
    with tmp_env(f"{package_name}=={package_version}") as prefix:
        assert PrefixData(prefix).get(package_name).version == package_version
        env = Environment.from_prefix(prefix, None, context.subdir)
        for platform in platforms:
            extrapolated = env.extrapolate(platform)

            if platform == env.platform:
                assert env is extrapolated
                continue

            # assert the package with no dependents is the requested package
            package = list(PrefixGraph(extrapolated.explicit_packages).records)[-1]
            assert package.name == package_name
            assert package.version == package_version

            # assert the extrapolated environment is as expected
            assert extrapolated.prefix == prefix
            assert extrapolated.platform == platform
            assert extrapolated.config == env.config
            assert extrapolated.external_packages == env.external_packages
            # cannot compare explicit_packages because they are unique to each platform
            # assert extrapolated.explicit_packages == env.explicit_packages
            assert extrapolated.name is None
            assert len(extrapolated.requested_packages) == 1
            assert extrapolated.variables == env.variables
            assert extrapolated.virtual_packages == env.virtual_packages

            # assert the explicit package version matches the requested package version
            assert (
                next(
                    package
                    for package in extrapolated.explicit_packages
                    if package.name == package_name
                ).version
                == package_version
            )


def test_explicit_packages(tmp_path: Path):
    explicit = tmp_path / "explicit.txt"
    explicit.write_text(
        "@EXPLICIT\n"
        "http://repo.anaconda.com/pkgs/main/noarch/pip-25.2-pyhc872135_0.conda#b829d36091ab08d18cafe8994ac6e02b"
    )
    env = Environment.from_cli(
        args=SimpleNamespace(name="test", packages=[], file=[str(explicit)]),
    )
    assert len(env.explicit_packages) == 1
    assert not env.requested_packages
