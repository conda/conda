# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import pytest
from pytest import MonkeyPatch
from pytest_mock import MockerFixture

from conda.base.context import reset_context
from conda.cli.install import assemble_environment
from conda.exceptions import CondaValueError
from conda.models.environment import EnvironmentConfig
from conda.models.match_spec import MatchSpec


def test_assemble_environment_empty():
    env = assemble_environment()
    assert env.config == EnvironmentConfig.from_context()


def test_assemble_environment_with_specs():
    env = assemble_environment(
        name="testenv", prefix="/path/to/testenv", specs=["numpy", "scipy=1.*"]
    )
    assert env.config == EnvironmentConfig.from_context()
    assert env.name == "testenv"
    assert env.prefix == "/path/to/testenv"
    assert env.requested_packages == [MatchSpec("numpy"), MatchSpec("scipy=1.*")]
    assert env.explicit_packages == []


def test_assemble_environment_with_explicit_specs(mocker: MockerFixture):
    fake_explicit_records = ["/path/to/package/numpy.conda"]
    mocker.patch(
        "conda.cli.install.get_package_records_from_explicit",
        return_value=fake_explicit_records,
    )

    env = assemble_environment(
        name="testenv",
        prefix="/path/to/testenv",
        specs=["/path/to/package/numpy.conda"],
    )
    assert env.config == EnvironmentConfig.from_context()
    assert env.name == "testenv"
    assert env.prefix == "/path/to/testenv"
    assert env.requested_packages == []
    assert env.explicit_packages == fake_explicit_records


def test_assemble_environment_mix_explicit_and_specs():
    with pytest.raises(CondaValueError) as exc_info:
        assemble_environment(
            name="testenv",
            prefix="/path/to/testenv",
            specs=["numpy", "scipy=1.*", "/path/to/package/numpy.conda"],
        )
    assert "cannot mix specifications with conda package filenames" in str(exc_info)


def test_assemble_environment_with_files(mocker: MockerFixture):
    fake_specs_from_url = ["numpy", "python >=3.9"]
    mocker.patch(
        "conda.cli.install.common.specs_from_url",
        return_value=fake_specs_from_url,
    )

    env = assemble_environment(
        name="testenv",
        prefix="/path/to/testenv",
        specs=["scipy"],
        files=["/my/files/that/does/not/exist"],
    )
    assert env.config == EnvironmentConfig.from_context()
    assert env.name == "testenv"
    assert env.prefix == "/path/to/testenv"
    assert env.requested_packages == [
        MatchSpec("scipy"),
        MatchSpec("numpy"),
        MatchSpec("python >=3.9"),
    ]
    assert env.explicit_packages == []


def test_assemble_environment_inject_default_packages_override(
    monkeypatch: MonkeyPatch,
):
    monkeypatch.setenv("CONDA_CREATE_DEFAULT_PACKAGES", "favicon,scipy=1.16.0")
    reset_context()

    env = assemble_environment(
        name="testenv",
        prefix="/path/to/testenv",
        specs=["numpy"],
        inject_default_packages=True,
    )
    assert env.config == EnvironmentConfig.from_context()
    assert env.name == "testenv"
    assert env.prefix == "/path/to/testenv"
    assert env.requested_packages == [
        MatchSpec("numpy"),
        MatchSpec("favicon"),
        MatchSpec("scipy=1.16.0"),
    ]
    assert env.explicit_packages == []

    env = assemble_environment(
        name="testenv",
        prefix="/path/to/testenv",
        specs=["numpy", "scipy=1.*"],
        inject_default_packages=False,
    )
    assert env.config == EnvironmentConfig.from_context()
    assert env.name == "testenv"
    assert env.prefix == "/path/to/testenv"
    assert env.requested_packages == [MatchSpec("numpy"), MatchSpec("scipy=1.*")]
    assert env.explicit_packages == []

    env = assemble_environment(
        name="testenv",
        prefix="/path/to/testenv",
        specs=["numpy", "scipy=1.*"],
        inject_default_packages=True,
    )
    assert env.config == EnvironmentConfig.from_context()
    assert env.name == "testenv"
    assert env.prefix == "/path/to/testenv"
    assert env.requested_packages == [
        MatchSpec("numpy"),
        MatchSpec("scipy=1.*"),
        MatchSpec("favicon"),
    ]
    assert env.explicit_packages == []
