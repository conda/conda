# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import pytest

from conda import plugins
from conda.env.env import Environment
from conda.exceptions import EnvSpecPluginNotDetected
from conda.plugins.types import CondaEnvironmentSpecifier, EnvironmentSpecBase


class RandomSpec(EnvironmentSpecBase):
    extensions = {".random"}

    def __init__(self, filename: str):
        self.filename = filename

    def can_handle(self):
        for ext in RandomSpec.extensions:
            if self.filename.endswith(ext):
                return True
        return False

    def environment(self):
        return Environment(name="random-environment", dependencies=["python", "numpy"])


class RandomSpecPlugin:
    @plugins.hookimpl
    def conda_environment_specifiers(self):
        yield CondaEnvironmentSpecifier(
            name="rand-spec",
            handler_class=RandomSpec,
        )


@pytest.fixture()
def dummy_random_spec_plugin(plugin_manager):
    random_spec_plugin = RandomSpecPlugin()
    plugin_manager.register(random_spec_plugin)

    return plugin_manager


def test_dummy_random_spec_is_registered(dummy_random_spec_plugin):
    """
    Ensures that our dummy random spec has been registered and can recognize .random files
    """
    filename = "test.random"
    env_spec_backend = dummy_random_spec_plugin.get_environment_specifier_handler(
        filename
    )
    assert env_spec_backend.name == "rand-spec"
    assert env_spec_backend.handler_class(filename).environment is not None


def test_raises_an_error_if_file_is_unhandleable(dummy_random_spec_plugin):
    """
    Ensures that our dummy random spec does not recognize non-".random" files
    """
    with pytest.raises(EnvSpecPluginNotDetected):
        dummy_random_spec_plugin.get_environment_specifier_handler("test.random-not")
