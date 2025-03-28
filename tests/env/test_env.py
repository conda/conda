# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import os
import random
from io import StringIO
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from conda.auxlib.ish import dals
from conda.common.serialize import yaml_round_trip_load
from conda.core.prefix_data import PrefixData
from conda.env.env import (
    VALID_KEYS,
    EnvironmentV1,
    EnvironmentV2,
    from_environment,
    from_file,
)
from conda.exceptions import CondaHTTPError
from conda.models.match_spec import MatchSpec
from conda.testing.integration import package_is_installed

from . import support_file

if TYPE_CHECKING:
    from pathlib import Path

    from pytest import MonkeyPatch

    from conda.testing.fixtures import CondaCLIFixture, PathFactoryFixture


class FakeStream:
    def __init__(self):
        self.output = ""

    def write(self, chunk):
        self.output += chunk.decode("utf-8")


def get_environment(filename):
    return from_file(support_file(filename))


def get_simple_environment():
    return get_environment("simple.yml")


def get_valid_keys_environment():
    return get_environment("valid_keys.yml")


def get_invalid_keys_environment():
    return get_environment("invalid_keys.yml")


def test_returns_Environment():
    e = get_simple_environment()
    assert isinstance(e, EnvironmentV1)


def test_retains_full_filename():
    e = get_simple_environment()
    assert support_file("simple.yml") == e.filename


def test_with_pip():
    e = from_file(support_file("with-pip.yml"))
    assert "pip" in e.dependencies
    assert "foo" in e.dependencies["pip"]
    assert "baz" in e.dependencies["pip"]


@pytest.mark.timeout(20)
def test_add_pip():
    e = from_file(support_file("add-pip.yml"))
    expected = {
        "conda": ["pip", "car"],
        "pip": ["foo", "baz"],
    }
    assert e.dependencies == expected


@pytest.mark.integration
def test_http():
    e = get_simple_environment()
    f = from_file(
        "https://raw.githubusercontent.com/conda/conda/main/tests/env/support/simple.yml"
    )
    assert e.dependencies == f.dependencies
    assert e.dependencies == f.dependencies


@pytest.mark.integration
def test_http_raises():
    with pytest.raises(CondaHTTPError):
        from_file(
            "https://raw.githubusercontent.com/conda/conda/main/tests/env/support/does-not-exist.yml"
        )


def test_envvars():
    current_conda_token = os.environ.get("CONDA_TOKEN")
    os.environ["CONDA_TOKEN"] = "aaa-12345"
    os.environ["OTHER_KEY"] = "12345-aaa"
    e = get_environment("channels_with_envvars.yml")
    assert set(e.channels) == {
        "https://localhost/t/aaa-12345/stable",
        "https://localhost/t/12345-aaa/stable",
        "conda-forge",
        "defaults",
    }
    if current_conda_token:
        os.environ["CONDA_TOKEN"] = current_conda_token
    else:
        del os.environ["CONDA_TOKEN"]
    del os.environ["OTHER_KEY"]


def test_has_empty_filename_by_default():
    e = EnvironmentV1()
    assert e.filename is None


def test_has_filename_if_provided():
    r = random.randint(100, 200)
    random_filename = f"/path/to/random/environment-{r}.yml"
    e = EnvironmentV1(filename=random_filename)
    assert e.filename == random_filename


def test_has_empty_name_by_default():
    e = EnvironmentV1()
    assert e.name is None


def test_has_name_if_provided():
    random_name = f"random-{random.randint(100, 200)}"
    e = EnvironmentV1(name=random_name)
    assert e.name == random_name


def test_dependencies_are_empty_by_default():
    e = EnvironmentV1()
    assert not e.dependencies


def test_parses_dependencies_from_raw_file():
    e = get_simple_environment()
    expected = {"conda": ["nltk"]}
    assert e.dependencies == expected


def test_builds_spec_from_line_raw_dependency():
    # TODO Refactor this inside conda to not be a raw string
    e = EnvironmentV1(dependencies=["nltk=3.0.0=np18py27_0"])
    expected = {"conda": ["nltk==3.0.0=np18py27_0"]}
    assert e.dependencies == expected


def test_args_are_wildcarded():
    e = EnvironmentV1(dependencies=["python=2.7"])
    expected = {"conda": ["python=2.7"]}
    assert e.dependencies == expected


def test_other_tips_of_dependencies_are_supported():
    e = EnvironmentV1(dependencies=["nltk", {"pip": ["foo", "bar"]}])
    expected = {
        "conda": ["nltk", "pip"],
        "pip": ["foo", "bar"],
    }
    assert e.dependencies == expected


def test_channels_default_to_empty_list():
    e = EnvironmentV1()
    assert isinstance(e.channels, list)
    assert not e.channels


def test_add_channels():
    e = EnvironmentV1()
    e.add_channels(["dup", "dup", "unique"])
    assert e.channels == ["dup", "unique"]


def test_remove_channels():
    e = EnvironmentV1(channels=["channel"])
    e.remove_channels()
    assert not e.channels


def test_channels_are_provided_by_kwarg():
    random_channels = (random.randint(100, 200), random)
    e = EnvironmentV1(channels=random_channels)
    assert e.channels == random_channels


def test_to_dict_returns_dictionary_of_data():
    random_name = f"random{random.randint(100, 200)}"
    e = EnvironmentV1(
        name=random_name, channels=["javascript"], dependencies=["nodejs"]
    )

    expected = {
        "name": random_name,
        "channels": ["javascript"],
        "dependencies": ["nodejs"],
    }
    assert e.to_dict() == expected


def test_to_dict_returns_just_name_if_only_thing_present():
    e = EnvironmentV1(name="simple")
    expected = {"name": "simple"}
    assert e.to_dict() == expected


def test_to_yaml_returns_yaml_parseable_string():
    random_name = f"random{random.randint(100, 200)}"
    e = EnvironmentV1(
        name=random_name, channels=["javascript"], dependencies=["nodejs"]
    )

    expected = {
        "name": random_name,
        "channels": ["javascript"],
        "dependencies": ["nodejs"],
    }

    actual = yaml_round_trip_load(StringIO(e.to_yaml()))
    assert expected == actual


def test_to_yaml_returns_proper_yaml():
    random_name = f"random{random.randint(100, 200)}"
    e = EnvironmentV1(
        name=random_name, channels=["javascript"], dependencies=["nodejs"]
    )

    expected = "\n".join(
        [
            f"name: {random_name}",
            "channels:",
            "  - javascript",
            "dependencies:",
            "  - nodejs",
            "",
        ]
    )

    actual = e.to_yaml()
    assert expected == actual


def test_to_yaml_takes_stream():
    random_name = f"random{random.randint(100, 200)}"
    e = EnvironmentV1(
        name=random_name, channels=["javascript"], dependencies=["nodejs"]
    )

    s = FakeStream()
    e.to_yaml(stream=s)

    expected = "\n".join(
        [
            f"name: {random_name}",
            "channels:",
            "  - javascript",
            "dependencies:",
            "  - nodejs",
            "",
        ]
    )
    assert expected == s.output


def test_can_add_dependencies_to_environment():
    e = get_simple_environment()
    e.dependencies.add("bar")

    s = FakeStream()
    e.to_yaml(stream=s)

    expected = "\n".join(["name: nlp", "dependencies:", "  - nltk", "  - bar", ""])
    assert expected == s.output


def test_dependencies_update_after_adding():
    e = get_simple_environment()
    assert "bar" not in e.dependencies["conda"]
    e.dependencies.add("bar")
    assert "bar" in e.dependencies["conda"]


def test_valid_keys():
    e = get_valid_keys_environment()
    e_dict = e.to_dict()
    for key in VALID_KEYS:
        assert key in e_dict


def test_invalid_keys():
    e = get_invalid_keys_environment()
    e_dict = e.to_dict()
    assert "name" in e_dict
    assert len(e_dict) == 1


def test_creates_file_on_save(tmp_path: Path):
    tmp = tmp_path / "environment.yml"

    assert not tmp.exists()

    env = EnvironmentV1(filename=tmp, name="simple")
    env.save()

    assert tmp.exists()
    assert env.to_yaml() == tmp.read_text()


@pytest.mark.integration
def test_create_advanced_pip(
    monkeypatch: MonkeyPatch,
    conda_cli: CondaCLIFixture,
    path_factory: PathFactoryFixture,
    tmp_envs_dir: Path,
):
    monkeypatch.setenv("CONDA_DLL_SEARCH_MODIFICATION_ENABLE", "true")

    prefix = path_factory()
    assert not prefix.exists()
    conda_cli(
        *("env", "create"),
        *("--prefix", prefix),
        *("--file", support_file("pip_argh.yml")),
    )
    assert prefix.exists()
    PrefixData._cache_.clear()
    assert package_is_installed(prefix, "argh==0.26.2")


def test_from_history():
    # We're not testing that get_requested_specs_map() actually works
    # assume it gives us back a dict of MatchSpecs
    with patch("conda.history.History.get_requested_specs_map") as m:
        m.return_value = {
            "python": MatchSpec("python=3"),
            "pytest": MatchSpec("pytest!=3.7.3"),
            "mock": MatchSpec("mock"),
            "yaml": MatchSpec("yaml>=0.1"),
        }
        out = from_environment("mock_env", "mock_prefix", from_history=True)
        assert "yaml[version='>=0.1']" in out.to_dict()["dependencies"]
        assert "pytest!=3.7.3" in out.to_dict()["dependencies"]
        assert len(out.to_dict()["dependencies"]) == 4

        m.assert_called()


def test_parse_environment_v2():
    yml_str = dals("""
        # From https://gist.github.com/jaimergp/4209c4c90d51b1bb07fe7293095f7c70
        #
        # What we want
        # - Everything the original environment.yml had
        # - All necessary inputs for the solver (channels, priority, repodata fn, platforms)
        # - Conditional dependencies based on virtual packages
        # - Requirement groups that can be joined
        # What we do NOT want
        # - This to become a lockfile
        name: data-science-something
        version: 2
        description: This environment provides data science packages
        variables:
            ENVVAR: value
            ENVVAR2: value
        channels:
            - conda-forge
        channel-priority: strict
        repodata-fn: repodata.json
        platforms:
            - linux-64
            - osx-64
            - win-64
        requirements:
            - python
            - numpy
            - if: __win
              then: pywin32
        pypi-requirements:
            - my-lab-dependency
            - if: __cuda
              then: my-lab-dependency-gpu
        groups:
            - group: py38
              requirements:
                - python=3.8
            - group: test
              requirements:
                - pytest
                - pytest-cov
                - if: __win
                  then: pytest-windows
              pypi-requirements:
                - some-test-dependency-only-on-pypi
        """)
    EnvironmentV2.from_yaml(yml_str)
