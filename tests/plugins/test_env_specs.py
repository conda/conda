# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import pytest

from conda import plugins
from conda.env.env import Environment
from conda.exceptions import EnvironmentSpecPluginNotDetected, PluginError
from conda.plugins.types import CondaEnvironmentSpecifier, EnvironmentSpecBase


class RandomSpec(EnvironmentSpecBase):
    extensions = {".random"}

    def __init__(self, filename: str):
        self.filename = filename

    def validate_source_name(self):
        for ext in RandomSpec.extensions:
            if self.filename.endswith(ext):
                return True
        return False
    
    def validate_schema(self):
        return True

    def environment(self):
        return Environment(name="random-environment", dependencies=["python", "numpy"])


class RandomSpecPlugin:
    @plugins.hookimpl
    def conda_environment_specifiers(self):
        yield CondaEnvironmentSpecifier(
            name="rand-spec",
            environment_spec=RandomSpec,
        )


class RandomSpecPlugin2:
    @plugins.hookimpl
    def conda_environment_specifiers(self):
        yield CondaEnvironmentSpecifier(
            name="rand-spec-2",
            environment_spec=RandomSpec,
        )


@pytest.fixture()
def dummy_random_spec_plugin(plugin_manager):
    random_spec_plugin = RandomSpecPlugin()
    plugin_manager.register(random_spec_plugin)

    return plugin_manager


@pytest.fixture()
def dummy_random_spec_plugin2(plugin_manager):
    random_spec_plugin = RandomSpecPlugin2()
    plugin_manager.register(random_spec_plugin)

    return plugin_manager


def test_dummy_random_spec_is_registered(dummy_random_spec_plugin):
    """
    Ensures that our dummy random spec has been registered and can recognize .random files
    """
    filename = "test.random"
    env_spec_backend = dummy_random_spec_plugin.get_environment_specifiers(filename)
    assert env_spec_backend.name == "rand-spec"
    assert env_spec_backend.environment_spec(filename).environment is not None


def test_raises_an_error_if_file_is_unhandleable(dummy_random_spec_plugin):
    """
    Ensures that our dummy random spec does not recognize non-".random" files
    """
    with pytest.raises(EnvironmentSpecPluginNotDetected):
        dummy_random_spec_plugin.get_environment_specifiers("test.random-not")


def test_raise_error_for_multiple_registered_installers(
    dummy_random_spec_plugin,
    dummy_random_spec_plugin2,
):
    """
    Ensures that we raise an error when more than one env installer is found
    for the same section.
    """
    filename = "test.random"
    with pytest.raises(PluginError):
        dummy_random_spec_plugin.get_environment_specifiers(filename)
