# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from conda import plugins
from conda.exceptions import (
    CondaValueError,
    EnvironmentSpecPluginNotDetected,
    PluginError,
)
from conda.models.environment import Environment
from conda.plugins.types import CondaEnvironmentSpecifier

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from conda.common.path import PathType


def random_validate(filename: PathType, data: str) -> bool:
    extensions = {".random"}
    for ext in extensions:
        if filename.endswith(ext):
            return True
    return False


def random_env(data: str) -> Environment:
    return Environment(prefix="/somewhere", platform=["linux-64"])


class RandomSpecPlugin:
    @plugins.hookimpl
    def conda_environment_specifiers(self):
        yield CondaEnvironmentSpecifier(
            name="rand-spec",
            validate=random_validate,
            env=random_env,
        )


class RandomSpecPlugin2:
    @plugins.hookimpl
    def conda_environment_specifiers(self):
        yield CondaEnvironmentSpecifier(
            name="rand-spec-2",
            validate=random_validate,
            env=random_env,
        )


class RandomSpecPluginNoAutodetect:
    @plugins.hookimpl
    def conda_environment_specifiers(self):
        yield CondaEnvironmentSpecifier(
            name="rand-spec-no-autodetect",
            validate=random_validate,
            env=random_env,
            detection_supported=False,
        )


class NaughtySpecPlugin:
    @plugins.hookimpl
    def conda_environment_specifiers(self):
        def naughty(**kwargs):
            raise TypeError("This is a naughty spec")

        yield CondaEnvironmentSpecifier(
            name="naughty",
            validate=naughty,
            env=naughty,
        )


@pytest.fixture()
def random_spec_plugin(plugin_manager):
    plg = RandomSpecPlugin()
    plugin_manager.register(plg)
    return plugin_manager


@pytest.fixture()
def random_spec_plugin_2(plugin_manager):
    plg = RandomSpecPlugin2()
    plugin_manager.register(plg)
    return plugin_manager


@pytest.fixture()
def random_spec_plugin_no_autodetect(plugin_manager):
    plg = RandomSpecPluginNoAutodetect()
    plugin_manager.register(plg)
    return plugin_manager


@pytest.fixture()
def naughty_spec_plugin(plugin_manager):
    plg = NaughtySpecPlugin()
    plugin_manager.register(plg)
    return plugin_manager


@pytest.fixture()
def mock_load_file(mocker: MockerFixture):
    mocker.patch(
        "conda.plugins.manager.load_file",
        return_value="",
    )


def test_dummy_random_spec_is_registered(random_spec_plugin, mock_load_file):
    """
    Ensures that our dummy random spec has been registered and can recognize .random files
    """
    filename = "test.random"
    env_spec_backend = random_spec_plugin.get_environment_specifier(filename)
    assert env_spec_backend.name == "rand-spec"
    assert env_spec_backend.env is not None

    env_spec_backend = random_spec_plugin.get_environment_specifier_by_name(
        source=filename, name="rand-spec"
    )
    assert env_spec_backend.name == "rand-spec"
    assert env_spec_backend.env is not None

    env_spec_backend = random_spec_plugin.detect_environment_specifier(source=filename)
    assert env_spec_backend.name == "rand-spec"
    assert env_spec_backend.env is not None


def test_raises_an_error_if_file_is_unhandleable(random_spec_plugin, mock_load_file):
    """
    Ensures that our dummy random spec does not recognize non-".random" files
    """
    with pytest.raises(EnvironmentSpecPluginNotDetected):
        random_spec_plugin.detect_environment_specifier("test.random-not")


def test_raises_an_error_if_plugin_name_does_not_exist(
    random_spec_plugin, mock_load_file
):
    """
    Ensures that an error is raised if the user requests a plugin that doesn't exist
    """
    with pytest.raises(CondaValueError):
        random_spec_plugin.get_environment_specifier_by_name(
            name="uhoh", source="test.random"
        )


def test_raises_an_error_if_named_plugin_can_not_be_handled(
    random_spec_plugin,
    mock_load_file,
):
    """
    Ensures that an error is raised if the user requests a plugin exists, but can't be handled
    """
    with pytest.raises(
        PluginError,
        match=r"Requested plugin 'rand-spec' is unable to handle environment spec",
    ):
        random_spec_plugin.get_environment_specifier_by_name(
            name="rand-spec", source="test.random-not-so-much"
        )


def test_raise_error_for_multiple_registered_installers(
    random_spec_plugin,
    random_spec_plugin_2,
    mock_load_file,
):
    """
    Ensures that we raise an error when more than one env installer is found
    for the same section.
    """
    filename = "test.random"
    with pytest.raises(PluginError):
        random_spec_plugin.get_environment_specifier(filename)


def test_raises_an_error_if_no_plugins_found(
    random_spec_plugin_no_autodetect, mock_load_file
):
    """
    Ensures that our a plugin with autodetect disabled does not get detected
    """
    with pytest.raises(EnvironmentSpecPluginNotDetected):
        random_spec_plugin_no_autodetect.get_environment_specifier("test.random")


def test_explicitly_select_a_non_autodetect_plugin(
    random_spec_plugin, random_spec_plugin_no_autodetect, mock_load_file
):
    """
    Ensures that our a plugin with autodetect disabled can be explicitly selected
    """
    env_spec = random_spec_plugin.get_environment_specifier(
        "test.random", name="rand-spec-no-autodetect"
    )
    assert env_spec.name == "rand-spec-no-autodetect"
    assert env_spec.env is not None
    assert env_spec.detection_supported is False


def test_naught_plugin_does_not_cause_unhandled_errors(
    plugin_manager,
    random_spec_plugin,
    random_spec_plugin_no_autodetect,
    naughty_spec_plugin,
    mock_load_file,
):
    """
    Ensures that explicitly selecting a plugin that has errors is handled appropriately
    """
    filename = "test.random"
    with pytest.raises(
        PluginError,
        match=rf"An error occured when handling '{filename}' with plugin 'naughty'.",
    ):
        plugin_manager.get_environment_specifier_by_name(filename, "naughty")


def test_naught_plugin_does_not_cause_unhandled_errors_during_detection(
    plugin_manager,
    random_spec_plugin,
    naughty_spec_plugin,
    mock_load_file,
):
    """
    Ensure that plugins that cause errors does not break plugin detection
    """
    filename = "test.random"
    env_spec_backend = plugin_manager.detect_environment_specifier(filename)
    assert env_spec_backend.name == "rand-spec"
    assert env_spec_backend.env is not None
