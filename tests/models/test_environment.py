# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

import pytest

from conda.exceptions import CondaValueError
from conda.models.environment import Environment, EnvironmentConfig
from conda.models.match_spec import MatchSpec
from conda.models.records import PackageRecord


def test_create_environment_missing_required_fields():
    with pytest.raises(CondaValueError):
        Environment(platform="linux-64", prefix=None)

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
            aggressive_update_packages=True,
            channels=["defaults"],
            channel_settings={"a": 1},
        ),
        external_packages={
            "pip": ["one", "two", {"special": "type"}],
            "other": ["three"],
        },
        explicit_packages=[],
        requested_packages=[MatchSpec("numpy"), MatchSpec("pandas")],
        variables={"PATH": "/usr/bin"},
    )
    env2 = Environment(
        prefix="/path/to/env1",
        platform="linux-64",
        config=EnvironmentConfig(
            aggressive_update_packages=False,
            channels=["conda-forge"],
            channel_settings={"b": 2},
            repodata_fns=["repodata2.json"],
        ),
        external_packages={"pip": ["two", "flask"], "a": ["nother"]},
        explicit_packages=[],
        requested_packages=[MatchSpec("numpy"), MatchSpec("flask")],
        variables={"VAR": "IABLE"},
    )
    merged = Environment.merge(env1, env2)
    assert merged.prefix == "/path/to/env1"
    assert merged.platform == "linux-64"
    assert merged.config == EnvironmentConfig(
        aggressive_update_packages=False,
        channels=["defaults", "conda-forge"],
        channel_settings={"a": 1, "b": 2},
        repodata_fns=["repodata2.json"],
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


def test_merge_configs_primitive_values_order():
    config1 = EnvironmentConfig(
        aggressive_update_packages=True,
    )
    config2 = EnvironmentConfig(
        aggressive_update_packages=False,
    )

    result = EnvironmentConfig.merge(config1, config2)
    assert result.aggressive_update_packages is False

    result = EnvironmentConfig.merge(config2, config1)
    assert result.aggressive_update_packages is True


def test_merge_configs_primitive_none_values_order():
    config1 = EnvironmentConfig(
        aggressive_update_packages=True,
    )
    config2 = EnvironmentConfig()

    result = EnvironmentConfig.merge(config1, config2)
    assert result.aggressive_update_packages is True

    result = EnvironmentConfig.merge(config2, config1)
    assert result.aggressive_update_packages is True


def test_merge_configs_deduplicate_values():
    config1 = EnvironmentConfig(
        channels=["defaults", "conda-forge"],
        disallowed_packages=["a"],
        pinned_packages=["b"],
        repodata_fns=["repodata.json"],
        track_features=["track"],
    )
    config2 = EnvironmentConfig(
        channels=["defaults", "my-channel"],
        disallowed_packages=["a"],
        pinned_packages=["b"],
        repodata_fns=["repodata.json"],
        track_features=["track"],
    )
    config3 = EnvironmentConfig(
        channels=["conda-forge", "b-channel"],
    )

    result = EnvironmentConfig.merge(config1, config2, config3)
    assert result.channels == ["defaults", "conda-forge", "my-channel", "b-channel"]
    assert result.disallowed_packages == ["a"]
    assert result.pinned_packages == ["b"]
    assert result.repodata_fns == ["repodata.json"]
    assert result.track_features == ["track"]
