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
from conda.models.environment import Environment, EnvironmentConfig
from conda.models.match_spec import MatchSpec
from conda.models.prefix_graph import PrefixGraph
from conda.models.records import PackageRecord

if TYPE_CHECKING:
    from pathlib import Path

    from pytest import MonkeyPatch
    from pytest_mock import MockerFixture

    from conda.testing.fixtures import TmpEnvFixture


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
            "pip": ["one", "two", {"special": "type"}],
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
        external_packages={"pip": ["two", "flask"], "a": ["nother"]},
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
            "defaults",
            "conda-forge",
        ),
        channel_settings=(
            {"channel": "one", "a": 1},
            {"channel": "two", "b": 2},
        ),
        repodata_fns=("repodata2.json",),
    )
    assert merged.external_packages == {
        "pip": ["one", "two", {"special": "type"}, "flask"],
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
    assert merged.name == "one"


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
    assert merged.prefix == "/path/to/env1"
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
        "defaults",
        "conda-forge",
        "my-channel",
        "b-channel",
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
    assert "Cannot mix specifications with conda package filenames" in str(exc_info)


def test_from_cli_with_files(mocker: MockerFixture):
    # Mock out extracting specs from a file by providing a list of specs.
    # This is similar output to extracting specs from a requirements.txt file.
    fake_specs_from_url = ["numpy", "python >=3.9"]
    mocker.patch(
        "conda.models.environment.specs_from_url",
        return_value=fake_specs_from_url,
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
        MatchSpec("scipy"),
        MatchSpec("numpy"),
        MatchSpec("python >=3.9"),
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

    # Mock the contents of a requirements.txt file that contains the spec numpy==2.3.1
    fake_specs_from_url = ["numpy==2.3.1"]
    mocker.patch(
        "conda.models.environment.specs_from_url",
        return_value=fake_specs_from_url,
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
