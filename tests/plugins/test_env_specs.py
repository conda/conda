# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import pytest

from conda import plugins
from conda.exceptions import (
    CondaValueError,
    EnvironmentSpecPluginNotDetected,
    PluginError,
)
from conda.models.environment import Environment
from conda.plugins import environment_specifiers
from conda.plugins.types import CondaEnvironmentSpecifier, EnvironmentSpecBase


class NaughtySpec(EnvironmentSpecBase):
    def __init__(self, source: str):
        self.source = source

    def can_handle(self):
        raise TypeError("This is a naughty spec")

    def env(self):
        raise TypeError("This is a naughty spec")


class NaughtySpecPlugin:
    @plugins.hookimpl
    def conda_environment_specifiers(self):
        yield CondaEnvironmentSpecifier(
            name="naughty",
            environment_spec=NaughtySpec,
        )


class RandomSpec(EnvironmentSpecBase):
    extensions = {".random"}

    def __init__(self, filename: str):
        self.filename = filename

    def can_handle(self):
        for ext in RandomSpec.extensions:
            if self.filename.endswith(ext):
                return True
        return False

    def env(self):
        return Environment(prefix="/somewhere", platform=["linux-64"])


class RandomSpecNoAutoDetect(RandomSpec):
    detection_supported = False


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


class RandomSpecPluginNoAutodetect:
    @plugins.hookimpl
    def conda_environment_specifiers(self):
        yield CondaEnvironmentSpecifier(
            name="rand-spec-no-autodetect",
            environment_spec=RandomSpecNoAutoDetect,
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


@pytest.fixture()
def dummy_random_spec_plugin_no_autodetect(plugin_manager):
    random_spec_plugin = RandomSpecPluginNoAutodetect()
    plugin_manager.register(random_spec_plugin)

    return plugin_manager


@pytest.fixture()
def naughty_spec_plugin(plugin_manager):
    plg = NaughtySpecPlugin()
    plugin_manager.register(plg)

    return plugin_manager


@pytest.fixture()
def plugin_manager_with_specifiers(plugin_manager):
    """Plugin manager with built-in environment specifier plugins loaded."""
    plugin_manager.load_plugins(*environment_specifiers.plugins)
    return plugin_manager


def test_dummy_random_spec_is_registered(dummy_random_spec_plugin):
    """
    Ensures that our dummy random spec has been registered and can recognize .random files
    """
    filename = "test.random"
    env_spec_backend = dummy_random_spec_plugin.get_environment_specifier(filename)
    assert env_spec_backend.name == "rand-spec"
    assert env_spec_backend.environment_spec(filename).env is not None

    env_spec_backend = dummy_random_spec_plugin.get_environment_specifier_by_name(
        source=filename, name="rand-spec"
    )
    assert env_spec_backend.name == "rand-spec"
    assert env_spec_backend.environment_spec(filename).env is not None

    env_spec_backend = dummy_random_spec_plugin.detect_environment_specifier(
        source=filename
    )
    assert env_spec_backend.name == "rand-spec"
    assert env_spec_backend.environment_spec(filename).env is not None


def test_raises_an_error_if_file_is_unhandleable(dummy_random_spec_plugin):
    """
    Ensures that our dummy random spec does not recognize non-".random" files
    """
    with pytest.raises(EnvironmentSpecPluginNotDetected):
        dummy_random_spec_plugin.detect_environment_specifier("test.random-not")


def test_raises_an_error_if_plugin_name_does_not_exist(dummy_random_spec_plugin):
    """
    Ensures that an error is raised if the user requests a plugin that doesn't exist
    """
    with pytest.raises(CondaValueError):
        dummy_random_spec_plugin.get_environment_specifier_by_name(
            name="uhoh", source="test.random"
        )


def test_raises_an_error_if_named_plugin_can_not_be_handled(
    dummy_random_spec_plugin,
):
    """
    Ensures that an error is raised if the user requests a plugin exists, but can't be handled
    """
    with pytest.raises(
        PluginError,
        match=r"Requested plugin 'rand-spec' is unable to handle environment spec",
    ):
        dummy_random_spec_plugin.get_environment_specifier_by_name(
            name="rand-spec", source="test.random-not-so-much"
        )


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
        dummy_random_spec_plugin.get_environment_specifier(filename)


def test_raises_an_error_if_no_plugins_found(dummy_random_spec_plugin_no_autodetect):
    """
    Ensures that our a plugin with autodetect disabled does not get detected
    """
    with pytest.raises(EnvironmentSpecPluginNotDetected):
        dummy_random_spec_plugin_no_autodetect.get_environment_specifier("test.random")


def test_explicitly_select_a_non_autodetect_plugin(
    dummy_random_spec_plugin, dummy_random_spec_plugin_no_autodetect
):
    """
    Ensures that our a plugin with autodetect disabled can be explicitly selected
    """
    env_spec = dummy_random_spec_plugin.get_environment_specifier(
        "test.random", name="rand-spec-no-autodetect"
    )
    assert env_spec.name == "rand-spec-no-autodetect"
    assert env_spec.environment_spec.detection_supported is False


def test_naught_plugin_does_not_cause_unhandled_errors(
    plugin_manager,
    dummy_random_spec_plugin,
    dummy_random_spec_plugin_no_autodetect,
    naughty_spec_plugin,
):
    """
    Ensures that explicitly selecting a plugin that has errors is handled appropriately
    """
    filename = "test.random"
    with pytest.raises(
        PluginError,
        match=rf"An error occurred when handling '{filename}' with plugin 'naughty'.",
    ):
        plugin_manager.get_environment_specifier_by_name(filename, "naughty")


def test_naught_plugin_does_not_cause_unhandled_errors_during_detection(
    plugin_manager,
    dummy_random_spec_plugin,
    dummy_random_spec_plugin_no_autodetect,
    naughty_spec_plugin,
):
    """
    Ensure that plugins that cause errors does not break plugin detection
    """
    filename = "test.random"
    env_spec_backend = plugin_manager.detect_environment_specifier(filename)
    assert env_spec_backend.name == "rand-spec"
    assert env_spec_backend.environment_spec(filename).env is not None


@pytest.mark.parametrize(
    "filename,expected_plugin",
    [
        ("requirements.txt", "requirements.txt"),
        ("spec.txt", "requirements.txt"),
        ("environment.yml", "cep-24"),  # cep-24 is registered with tryfirst=True
        ("environment.yaml", "cep-24"),
        ("explicit.txt", "explicit"),
    ],
)
def test_detect_environment_specifier_by_filename(
    plugin_manager_with_specifiers,
    tmp_path,
    filename,
    expected_plugin,
):
    """Test filename-based filtering in two-phase detection."""
    # Create a test file with appropriate content
    test_file = tmp_path / filename
    if "requirements" in filename or "spec" in filename:
        test_file.write_text("numpy==1.20.0\npandas>=1.0")
    elif "environment" in filename:
        test_file.write_text("name: test\ndependencies:\n  - python=3.8")
    elif "explicit" in filename:
        test_file.write_text(
            "@EXPLICIT\nhttps://repo.anaconda.com/pkgs/main/linux-64/python-3.8.0-0.tar.bz2"
        )

    specifier = plugin_manager_with_specifiers.detect_environment_specifier(
        str(test_file)
    )
    assert specifier.name == expected_plugin


def test_detect_environment_specifier_phase2_fallback(
    plugin_manager_with_specifiers,
    tmp_path,
):
    """Test that Phase 2 fallback works when filename doesn't match."""
    # Create a file with non-standard name but valid requirements.txt content
    test_file = tmp_path / "my-custom-deps.txt"
    test_file.write_text("numpy==1.20.0\npandas>=1.0")

    # Should fall back to content-based detection
    specifier = plugin_manager_with_specifiers.detect_environment_specifier(
        str(test_file)
    )
    assert specifier.name == "requirements.txt"  # Detected by content


def test_detect_environment_specifier_pattern_matching_with_wildcard(
    plugin_manager,
    tmp_path,
):
    """Test that fnmatch patterns work for plugins with wildcards."""

    # Create a plugin with wildcard pattern support
    class WildcardSpec(EnvironmentSpecBase):
        def __init__(self, source: str):
            self.source = source

        def can_handle(self):
            # Simple check - just verify file exists
            from pathlib import Path

            return Path(self.source).exists()

        def env(self):
            return Environment(prefix="/somewhere", platform=["linux-64"])

    class WildcardSpecPlugin:
        @plugins.hookimpl
        def conda_environment_specifiers(self):
            yield CondaEnvironmentSpecifier(
                name="wildcard-spec",
                environment_spec=WildcardSpec,
                default_filenames=("*.lock.yml",),  # Pattern with wildcard
            )

    # Register the plugin
    wildcard_plugin = WildcardSpecPlugin()
    plugin_manager.register(wildcard_plugin)

    # Create a file matching the pattern
    test_file = tmp_path / "my-project.lock.yml"
    test_file.write_text("name: test\ndependencies:\n  - python=3.8")

    # Should match the wildcard pattern
    specifier = plugin_manager.detect_environment_specifier(str(test_file))
    assert specifier.name == "wildcard-spec"

    # Unregister the plugin to avoid affecting other tests
    plugin_manager.unregister(wildcard_plugin)


def test_detect_environment_specifier_no_match_raises_error(
    plugin_manager_with_specifiers,
    tmp_path,
):
    """Test that unrecognized files raise appropriate error."""
    # Create a file that doesn't match any plugin
    test_file = tmp_path / "unknown.xyz"
    test_file.write_text("some random content")

    # Should raise error when no plugin can handle it
    with pytest.raises(EnvironmentSpecPluginNotDetected):
        plugin_manager_with_specifiers.detect_environment_specifier(str(test_file))
