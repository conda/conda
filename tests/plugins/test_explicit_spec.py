# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
# No need for os and tempfile anymore as we use support files

import pytest

from conda import plugins
from conda.env.specs.requirements import ExplicitRequirementsSpec
from conda.exceptions import EnvironmentSpecPluginNotDetected
from conda.plugins.types import CondaEnvironmentSpecifier
from tests.env import support_file


@pytest.fixture(scope="module")
def support_explicit_file():
    """Path to the explicit environment file in the test support directory"""
    return support_file("explicit.txt")


@pytest.fixture(scope="module")
def support_non_explicit_file():
    """Path to a non-explicit environment file in the test support directory"""
    return support_file("requirements.txt")


def test_can_handle_explicit_file(support_explicit_file):
    """Ensures ExplicitRequirementsSpec can handle a file with @EXPLICIT marker"""
    assert ExplicitRequirementsSpec(filename=support_explicit_file).can_handle()


def test_explicit_file_spec_rejects_non_explicit_file(support_non_explicit_file):
    """Ensures ExplicitRequirementsSpec rejects a file without @EXPLICIT marker"""
    spec = ExplicitRequirementsSpec(filename=support_non_explicit_file)
    assert not spec.can_handle()
    assert "does not contain @EXPLICIT marker" in spec.msg


def test_environment_creation(support_explicit_file):
    """Test that environment is correctly created from explicit file"""
    spec = ExplicitRequirementsSpec(filename=support_explicit_file)

    # Test the raw parsed packages
    packages = spec._parse_explicit_file()
    assert packages is not None
    assert len(packages) == 3  # @EXPLICIT marker + 2 packages

    # Verify we have both Python and NumPy packages (excluding @EXPLICIT marker)
    pkg_names = [str(pkg).lower() for pkg in packages if pkg != "@EXPLICIT"]
    assert len(pkg_names) == 2, "Should have 2 actual packages"
    assert any("python" in pkg for pkg in pkg_names), "No Python package found"
    assert any("numpy" in pkg for pkg in pkg_names), "No NumPy package found"

    # Check raw dependencies length and content
    raw_deps = spec.environment.dependencies.raw
    assert len(raw_deps) == 3  # @EXPLICIT marker + 2 packages

    # Verify environment dependencies include both packages
    env_pkgs = [str(dep).lower() for dep in raw_deps]
    assert any("python" in pkg for pkg in env_pkgs), "No Python package in environment"
    assert any("numpy" in pkg for pkg in env_pkgs), "No NumPy package in environment"


class ExplicitSpecPlugin:
    @plugins.hookimpl
    def conda_environment_specifiers(self):
        yield CondaEnvironmentSpecifier(
            name="explicit-test",
            environment_spec=ExplicitRequirementsSpec,
        )


@pytest.fixture()
def explicit_file_spec_plugin(plugin_manager):
    plugin = ExplicitSpecPlugin()
    plugin_manager.register(plugin)
    return plugin_manager


def test_explicit_file_spec_is_registered(
    explicit_file_spec_plugin, support_explicit_file
):
    """Ensures that the explicit spec has been registered and can handle explicit files"""
    # Verify plugin registration and correct name
    env_spec_backend = explicit_file_spec_plugin.detect_environment_specifier(
        support_explicit_file
    )
    assert env_spec_backend.name == "explicit-test"

    # Test environment creation through the plugin
    env = env_spec_backend.environment_spec(support_explicit_file).environment

    # Check environment structure and content
    assert "conda" in env.dependencies
    assert len(env.dependencies.raw) == 3  # @EXPLICIT marker + 2 packages
    assert len(env.dependencies["conda"]) == 3  # @EXPLICIT marker + 2 packages

    # Verify expected packages are present (excluding @EXPLICIT marker)
    conda_pkgs = [str(dep).lower() for dep in env.dependencies["conda"] if str(dep).lower() != "@explicit"]
    assert len(conda_pkgs) == 2, "Should have 2 actual packages"
    assert any("python" in pkg for pkg in conda_pkgs), "No Python package found"
    assert any("numpy" in pkg for pkg in conda_pkgs), "No NumPy package found"


def test_raises_error_if_not_explicit_file(
    explicit_file_spec_plugin, support_non_explicit_file
):
    """Ensures explicit spec plugin rejects non-explicit files"""
    with pytest.raises(EnvironmentSpecPluginNotDetected):
        explicit_file_spec_plugin.detect_environment_specifier(support_non_explicit_file)
