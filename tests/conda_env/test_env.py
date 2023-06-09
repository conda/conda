# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import os
import random
import unittest
from os.path import join
from unittest.mock import patch
from uuid import uuid4

from conda.base.context import conda_tests_ctxt_mgmt_def_pol
from conda.common.compat import on_win
from conda.common.io import env_vars
from conda.common.serialize import yaml_round_trip_load
from conda.core.prefix_data import PrefixData
from conda.exceptions import CondaHTTPError, EnvironmentFileNotFound
from conda.models.match_spec import MatchSpec
from conda_env.env import from_environment
from tests.test_utils import is_prefix_activated_PATHwise

from . import support_file
from .utils import Commands, make_temp_envs_dir, run_command

PYTHON_BINARY = "python.exe" if on_win else "bin/python"


try:
    from io import StringIO
except ImportError:
    from StringIO import StringIO

import pytest

from conda_env import env


class FakeStream:
    def __init__(self):
        self.output = ""

    def write(self, chunk):
        self.output += chunk.decode("utf-8")


def get_environment(filename):
    return env.from_file(support_file(filename))


def get_simple_environment():
    return get_environment("simple.yml")


def get_valid_keys_environment():
    return get_environment("valid_keys.yml")


def get_invalid_keys_environment():
    return get_environment("invalid_keys.yml")


class from_file_TestCase(unittest.TestCase):
    def test_returns_Environment(self):
        e = get_simple_environment()
        self.assertIsInstance(e, env.Environment)

    def test_retains_full_filename(self):
        e = get_simple_environment()
        self.assertEqual(support_file("simple.yml"), e.filename)

    def test_with_pip(self):
        e = env.from_file(support_file("with-pip.yml"))
        assert "pip" in e.dependencies
        assert "foo" in e.dependencies["pip"]
        assert "baz" in e.dependencies["pip"]

    @pytest.mark.timeout(20)
    def test_add_pip(self):
        e = env.from_file(support_file("add-pip.yml"))
        expected = {
            "conda": ["pip", "car"],
            "pip": ["foo", "baz"],
        }
        self.assertEqual(e.dependencies, expected)

    @pytest.mark.integration
    def test_http(self):
        e = get_simple_environment()
        f = env.from_file(
            "https://raw.githubusercontent.com/conda/conda/main/tests/conda_env/support/simple.yml"
        )
        self.assertEqual(e.dependencies, f.dependencies)
        assert e.dependencies == f.dependencies

    @pytest.mark.integration
    def test_http_raises(self):
        with self.assertRaises(CondaHTTPError):
            env.from_file(
                "https://raw.githubusercontent.com/conda/conda/main/tests/conda_env/support/does-not-exist.yml"
            )

    def test_envvars(self):
        current_conda_token = os.environ.get("CONDA_TOKEN")
        os.environ["CONDA_TOKEN"] = "aaa-12345"
        os.environ["OTHER_KEY"] = "12345-aaa"
        e = get_environment("channels_with_envvars.yml")
        self.assertEqual(
            set(e.channels),
            {
                "https://localhost/t/aaa-12345/stable",
                "https://localhost/t/12345-aaa/stable",
                "conda-forge",
                "defaults",
            },
        )
        if current_conda_token:
            os.environ["CONDA_TOKEN"] = current_conda_token
        else:
            del os.environ["CONDA_TOKEN"]
        del os.environ["OTHER_KEY"]


class EnvironmentTestCase(unittest.TestCase):
    def test_has_empty_filename_by_default(self):
        e = env.Environment()
        self.assertEqual(e.filename, None)

    def test_has_filename_if_provided(self):
        r = random.randint(100, 200)
        random_filename = f"/path/to/random/environment-{r}.yml"
        e = env.Environment(filename=random_filename)
        self.assertEqual(e.filename, random_filename)

    def test_has_empty_name_by_default(self):
        e = env.Environment()
        self.assertEqual(e.name, None)

    def test_has_name_if_provided(self):
        random_name = f"random-{random.randint(100, 200)}"
        e = env.Environment(name=random_name)
        self.assertEqual(e.name, random_name)

    def test_dependencies_are_empty_by_default(self):
        e = env.Environment()
        self.assertEqual(0, len(e.dependencies))

    def test_parses_dependencies_from_raw_file(self):
        e = get_simple_environment()
        expected = {"conda": ["nltk"]}
        self.assertEqual(e.dependencies, expected)

    def test_builds_spec_from_line_raw_dependency(self):
        # TODO Refactor this inside conda to not be a raw string
        e = env.Environment(dependencies=["nltk=3.0.0=np18py27_0"])
        expected = {"conda": ["nltk==3.0.0=np18py27_0"]}
        self.assertEqual(e.dependencies, expected)

    def test_args_are_wildcarded(self):
        e = env.Environment(dependencies=["python=2.7"])
        expected = {"conda": ["python=2.7"]}
        self.assertEqual(e.dependencies, expected)

    def test_other_tips_of_dependencies_are_supported(self):
        e = env.Environment(dependencies=["nltk", {"pip": ["foo", "bar"]}])
        expected = {
            "conda": ["nltk", "pip"],
            "pip": ["foo", "bar"],
        }
        self.assertEqual(e.dependencies, expected)

    def test_channels_default_to_empty_list(self):
        e = env.Environment()
        self.assertIsInstance(e.channels, list)
        self.assertEqual(e.channels, [])

    def test_add_channels(self):
        e = env.Environment()
        e.add_channels(["dup", "dup", "unique"])
        self.assertEqual(e.channels, ["dup", "unique"])

    def test_remove_channels(self):
        e = env.Environment(channels=["channel"])
        e.remove_channels()
        self.assertEqual(e.channels, [])

    def test_channels_are_provided_by_kwarg(self):
        random_channels = (random.randint(100, 200), random)
        e = env.Environment(channels=random_channels)
        self.assertEqual(e.channels, random_channels)

    def test_to_dict_returns_dictionary_of_data(self):
        random_name = f"random{random.randint(100, 200)}"
        e = env.Environment(
            name=random_name, channels=["javascript"], dependencies=["nodejs"]
        )

        expected = {
            "name": random_name,
            "channels": ["javascript"],
            "dependencies": ["nodejs"],
        }
        self.assertEqual(e.to_dict(), expected)

    def test_to_dict_returns_just_name_if_only_thing_present(self):
        e = env.Environment(name="simple")
        expected = {"name": "simple"}
        self.assertEqual(e.to_dict(), expected)

    def test_to_yaml_returns_yaml_parseable_string(self):
        random_name = f"random{random.randint(100, 200)}"
        e = env.Environment(
            name=random_name, channels=["javascript"], dependencies=["nodejs"]
        )

        expected = {
            "name": random_name,
            "channels": ["javascript"],
            "dependencies": ["nodejs"],
        }

        actual = yaml_round_trip_load(StringIO(e.to_yaml()))
        self.assertEqual(expected, actual)

    def test_to_yaml_returns_proper_yaml(self):
        random_name = f"random{random.randint(100, 200)}"
        e = env.Environment(
            name=random_name, channels=["javascript"], dependencies=["nodejs"]
        )

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
        self.assertEqual(expected, actual)

    def test_to_yaml_takes_stream(self):
        random_name = f"random{random.randint(100, 200)}"
        e = env.Environment(
            name=random_name, channels=["javascript"], dependencies=["nodejs"]
        )

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

    def test_can_add_dependencies_to_environment(self):
        e = get_simple_environment()
        e.dependencies.add("bar")

        s = FakeStream()
        e.to_yaml(stream=s)

        expected = "\n".join(["name: nlp", "dependencies:", "  - nltk", "  - bar", ""])
        assert expected == s.output

    def test_dependencies_update_after_adding(self):
        e = get_simple_environment()
        assert "bar" not in e.dependencies["conda"]
        e.dependencies.add("bar")
        assert "bar" in e.dependencies["conda"]

    def test_valid_keys(self):
        e = get_valid_keys_environment()
        e_dict = e.to_dict()
        for key in env.VALID_KEYS:
            assert key in e_dict

    def test_invalid_keys(self):
        e = get_invalid_keys_environment()
        e_dict = e.to_dict()
        assert "name" in e_dict
        assert len(e_dict) == 1


class DirectoryTestCase(unittest.TestCase):
    directory = support_file("example")

    def setUp(self):
        self.original_working_dir = os.getcwd()
        self.env = env.load_from_directory(self.directory)

    def tearDown(self):
        os.chdir(self.original_working_dir)

    def test_returns_env_object(self):
        self.assertIsInstance(self.env, env.Environment)

    def test_has_expected_name(self):
        self.assertEqual("test", self.env.name)

    def test_has_dependencies(self):
        self.assertEqual(1, len(self.env.dependencies["conda"]))
        assert "numpy" in self.env.dependencies["conda"]


class load_from_directory_example_TestCase(DirectoryTestCase):
    directory = support_file("example")


class load_from_directory_example_yaml_TestCase(DirectoryTestCase):
    directory = support_file("example-yaml")


class load_from_directory_recursive_TestCase(DirectoryTestCase):
    directory = support_file("foo/bar")


class load_from_directory_recursive_two_TestCase(DirectoryTestCase):
    directory = support_file("foo/bar/baz")


class load_from_directory_trailing_slash_TestCase(DirectoryTestCase):
    directory = support_file("foo/bar/baz/")


class load_from_directory_TestCase(unittest.TestCase):
    def test_raises_when_unable_to_find(self):
        with self.assertRaises(EnvironmentFileNotFound):
            env.load_from_directory("/path/to/unknown/env-spec")

    def test_raised_exception_has_environment_yml_as_file(self):
        with self.assertRaises(EnvironmentFileNotFound) as e:
            env.load_from_directory("/path/to/unknown/env-spec")
        self.assertEqual(e.exception.filename, "environment.yml")


class LoadEnvFromFileAndSaveTestCase(unittest.TestCase):
    env_path = support_file(os.path.join("saved-env", "environment.yml"))

    def setUp(self):
        with open(self.env_path, "rb") as fp:
            self.original_file_contents = fp.read()
        self.env = env.load_from_directory(self.env_path)

    def tearDown(self):
        with open(self.env_path, "wb") as fp:
            fp.write(self.original_file_contents)

    def test_expected_default_conditions(self):
        self.assertEqual(1, len(self.env.dependencies["conda"]))

    def test(self):
        self.env.dependencies.add("numpy")
        self.env.save()

        e = env.load_from_directory(self.env_path)
        self.assertEqual(2, len(e.dependencies["conda"]))
        assert "numpy" in e.dependencies["conda"]


class EnvironmentSaveTestCase(unittest.TestCase):
    env_file = support_file("saved.yml")

    def tearDown(self):
        if os.path.exists(self.env_file):
            os.unlink(self.env_file)

    def test_creates_file_on_save(self):
        self.assertFalse(os.path.exists(self.env_file), msg="sanity check")

        e = env.Environment(filename=self.env_file, name="simple")
        e.save()

        self.assertTrue(os.path.exists(self.env_file))

    def _test_saves_yaml_representation_of_file(self):
        e = env.Environment(filename=self.env_file, name="simple")
        e.save()

        with open(self.env_file, "rb") as fp:
            actual = fp.read()

        self.assertTrue(len(actual) > 0, msg="sanity check")
        self.assertEqual(e.to_yaml(), actual)


class SaveExistingEnvTestCase(unittest.TestCase):
    @unittest.skipIf(
        not is_prefix_activated_PATHwise(),
        "You are running `pytest` outside of proper activation. "
        "The entries necessary for conda to operate correctly "
        "are not on PATH.  Please use `conda activate`",
    )
    @pytest.mark.integration
    def test_create_advanced_pip(self):
        with make_temp_envs_dir() as envs_dir:
            with env_vars(
                {
                    "CONDA_ENVS_DIRS": envs_dir,
                    "CONDA_DLL_SEARCH_MODIFICATION_ENABLE": "true",
                },
                stack_callback=conda_tests_ctxt_mgmt_def_pol,
            ):
                env_name = str(uuid4())[:8]
                run_command(Commands.CREATE, env_name, support_file("pip_argh.yml"))
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
                run_command(Commands.EXPORT, env_name, out_file)
                with open(out_file) as f:
                    d = yaml_round_trip_load(f)
                assert {"pip": ["argh==0.26.2"]} in d["dependencies"]


class TestFromEnvironment(unittest.TestCase):
    def test_from_history(self):
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
