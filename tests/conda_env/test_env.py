# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import os
import random
from io import StringIO
from os.path import join
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import pytest

from conda.base.context import conda_tests_ctxt_mgmt_def_pol
from conda.common.io import env_vars
from conda.common.serialize import yaml_round_trip_load
from conda.core.prefix_data import PrefixData
from conda.exceptions import CondaHTTPError, EnvironmentFileNotFound
from conda.models.match_spec import MatchSpec
from conda.testing import CondaCLIFixture
from conda_env.env import (
    VALID_KEYS,
    Environment,
    from_environment,
    from_file,
    load_from_directory,
)
from tests.test_utils import is_prefix_activated_PATHwise

from . import support_file
from .utils import make_temp_envs_dir


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
    assert isinstance(e, Environment)


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
        "https://raw.githubusercontent.com/conda/conda/main/tests/conda_env/support/simple.yml"
    )
    assert e.dependencies == f.dependencies
    assert e.dependencies == f.dependencies


@pytest.mark.integration
def test_http_raises():
    with pytest.raises(CondaHTTPError):
        from_file(
            "https://raw.githubusercontent.com/conda/conda/main/tests/conda_env/support/does-not-exist.yml"
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
    e = Environment()
    assert e.filename is None


def test_has_filename_if_provided():
    r = random.randint(100, 200)
    random_filename = f"/path/to/random/environment-{r}.yml"
    e = Environment(filename=random_filename)
    assert e.filename == random_filename


def test_has_empty_name_by_default():
    e = Environment()
    assert e.name is None


def test_has_name_if_provided():
    random_name = f"random-{random.randint(100, 200)}"
    e = Environment(name=random_name)
    assert e.name == random_name


def test_dependencies_are_empty_by_default():
    e = Environment()
    assert not e.dependencies


def test_parses_dependencies_from_raw_file():
    e = get_simple_environment()
    expected = {"conda": ["nltk"]}
    assert e.dependencies == expected


def test_builds_spec_from_line_raw_dependency():
    # TODO Refactor this inside conda to not be a raw string
    e = Environment(dependencies=["nltk=3.0.0=np18py27_0"])
    expected = {"conda": ["nltk==3.0.0=np18py27_0"]}
    assert e.dependencies == expected


def test_args_are_wildcarded():
    e = Environment(dependencies=["python=2.7"])
    expected = {"conda": ["python=2.7"]}
    assert e.dependencies == expected


def test_other_tips_of_dependencies_are_supported():
    e = Environment(dependencies=["nltk", {"pip": ["foo", "bar"]}])
    expected = {
        "conda": ["nltk", "pip"],
        "pip": ["foo", "bar"],
    }
    assert e.dependencies == expected


def test_channels_default_to_empty_list():
    e = Environment()
    assert isinstance(e.channels, list)
    assert not e.channels


def test_add_channels():
    e = Environment()
    e.add_channels(["dup", "dup", "unique"])
    assert e.channels == ["dup", "unique"]


def test_remove_channels():
    e = Environment(channels=["channel"])
    e.remove_channels()
    assert not e.channels


def test_channels_are_provided_by_kwarg():
    random_channels = (random.randint(100, 200), random)
    e = Environment(channels=random_channels)
    assert e.channels == random_channels


def test_to_dict_returns_dictionary_of_data():
    random_name = f"random{random.randint(100, 200)}"
    e = Environment(name=random_name, channels=["javascript"], dependencies=["nodejs"])

    expected = {
        "name": random_name,
        "channels": ["javascript"],
        "dependencies": ["nodejs"],
    }
    assert e.to_dict() == expected


def test_to_dict_returns_just_name_if_only_thing_present():
    e = Environment(name="simple")
    expected = {"name": "simple"}
    assert e.to_dict() == expected


def test_to_yaml_returns_yaml_parseable_string():
    random_name = f"random{random.randint(100, 200)}"
    e = Environment(name=random_name, channels=["javascript"], dependencies=["nodejs"])

    expected = {
        "name": random_name,
        "channels": ["javascript"],
        "dependencies": ["nodejs"],
    }

    actual = yaml_round_trip_load(StringIO(e.to_yaml()))
    assert expected == actual


def test_to_yaml_returns_proper_yaml():
    random_name = f"random{random.randint(100, 200)}"
    e = Environment(name=random_name, channels=["javascript"], dependencies=["nodejs"])

    expected = "\n".join(
        [
            "name: %s" % random_name,
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
    e = Environment(name=random_name, channels=["javascript"], dependencies=["nodejs"])

    s = FakeStream()
    e.to_yaml(stream=s)

    expected = "\n".join(
        [
            "name: %s" % random_name,
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


@pytest.mark.parametrize(
    "directory",
    ["example", "example-yaml", "foo/bar", "foo/bar/baz", "foo/bar/baz/"],
)
def test_load_from_directory(directory: str):
    env = load_from_directory(support_file(directory))

    assert isinstance(env, Environment)
    assert "test" == env.name
    assert len(env.dependencies["conda"]) == 1
    assert "numpy" in env.dependencies["conda"]


def test_raises_when_unable_to_find():
    with pytest.raises(EnvironmentFileNotFound):
        load_from_directory("/path/to/unknown/env-spec")


def test_raised_exception_has_environment_yml_as_file():
    with pytest.raises(EnvironmentFileNotFound) as err:
        load_from_directory("/path/to/unknown/env-spec")
    assert err.value.filename == "environment.yml"


def test_load_from_directory_and_save(tmp_path: Path):
    original = Path(support_file("saved-env/environment.yml")).read_text()

    tmp = tmp_path / "environment.yml"
    tmp.write_text(original)

    env = load_from_directory(tmp)

    assert len(env.dependencies["conda"]) == 1
    assert "numpy" not in env.dependencies["conda"]

    env.dependencies.add("numpy")
    env.save()

    new_env = load_from_directory(tmp)
    assert len(new_env.dependencies["conda"]) == 2
    assert "numpy" in new_env.dependencies["conda"]


def test_creates_file_on_save(tmp_path: Path):
    tmp = tmp_path / "environment.yml"

    assert not tmp.exists()

    env = Environment(filename=tmp, name="simple")
    env.save()

    assert tmp.exists()
    assert env.to_yaml() == tmp.read_text()


@pytest.mark.skipif(
    not is_prefix_activated_PATHwise(),
    reason=(
        "You are running `pytest` outside of proper activation. "
        "The entries necessary for conda to operate correctly "
        "are not on PATH.  Please use `conda activate`"
    ),
)
@pytest.mark.integration
def test_create_advanced_pip(conda_cli: CondaCLIFixture):
    with make_temp_envs_dir() as envs_dir:
        with env_vars(
            {
                "CONDA_ENVS_DIRS": envs_dir,
                "CONDA_DLL_SEARCH_MODIFICATION_ENABLE": "true",
            },
            stack_callback=conda_tests_ctxt_mgmt_def_pol,
        ):
            env_name = str(uuid4())[:8]
            conda_cli("env", "create", "--name", env_name, support_file("pip_argh.yml"))
            out_file = join(envs_dir, "test_env.yaml")

        # make sure that the export reconsiders the presence of pip interop being enabled
        PrefixData._cache_.clear()

        with env_vars(
            {
                "CONDA_ENVS_DIRS": envs_dir,
            },
            stack_callback=conda_tests_ctxt_mgmt_def_pol,
        ):
            # note: out of scope of pip interop var.  Should be enabling conda pip interop itself.
            conda_cli("export", "--name", env_name, out_file)
            with open(out_file) as f:
                d = yaml_round_trip_load(f)
            assert {"pip": ["argh==0.26.2"]} in d["dependencies"]


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
