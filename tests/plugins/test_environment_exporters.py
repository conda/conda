# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Tests for environment exporter plugins."""

from __future__ import annotations

import json

import pytest

from conda.exceptions import CondaValueError
from conda.models.environment import Environment
from conda.models.match_spec import MatchSpec
from conda.plugins.environment_exporters.explicit import ExplicitEnvironmentExporter
from conda.plugins.environment_exporters.json import JsonEnvironmentExporter
from conda.plugins.environment_exporters.yaml import YamlEnvironmentExporter
from conda.plugins.manager import get_plugin_manager
from conda.plugins.types import EnvironmentExporter


@pytest.fixture
def test_env():
    """Create a test environment for exporter testing."""
    return Environment(
        name="test-env",
        prefix="/tmp/test-env",
        platform="linux-64",
        requested_packages=[MatchSpec("python=3.9"), MatchSpec("numpy")],
    )


@pytest.fixture
def loaded_plugin_manager():
    """Get the plugin manager with built-in plugins loaded."""
    return get_plugin_manager()


class TestEnvironmentExporter(EnvironmentExporter):
    """Test environment exporter for testing purposes."""

    format = "test"

    def export(self, env: Environment, format: str) -> str:
        return f"TEST FORMAT: {env.name}"


def test_environment_exporter_base_class():
    """Test the EnvironmentExporter abstract class."""
    exporter = TestEnvironmentExporter()

    # Test export functionality
    env = Environment(
        name="test-env",
        prefix="/tmp/test-env",
        platform="linux-64",
        requested_packages=[MatchSpec("python")],
    )
    result = exporter.export(env, "test")
    assert result == "TEST FORMAT: test-env"


def test_builtin_yaml_exporter(loaded_plugin_manager, test_env):
    """Test the built-in YAML environment exporter."""
    # Test that exporter is available
    exporter_config = loaded_plugin_manager.get_environment_exporter_by_format(
        format_name="environment-yaml"
    )
    assert exporter_config is not None
    assert exporter_config.name == "environment-yaml"

    # Test export functionality
    exporter = exporter_config.handler()
    result = exporter.export(test_env, "environment-yaml")

    # Verify YAML content
    expected_content = ["name: test-env", "python=3.9", "numpy"]
    for content in expected_content:
        assert content in result


def test_builtin_json_exporter(loaded_plugin_manager, test_env):
    """Test the built-in JSON environment exporter."""
    # Test that exporter is available
    exporter_config = loaded_plugin_manager.get_environment_exporter_by_format(
        format_name="environment-json"
    )
    assert exporter_config is not None
    assert exporter_config.name == "environment-json"

    # Test export functionality
    exporter = exporter_config.handler()
    result = exporter.export(test_env, "environment-json")

    # Verify it's valid JSON with correct structure
    parsed = json.loads(result)
    assert parsed["name"] == "test-env"
    assert "python=3.9" in parsed["dependencies"]
    assert "numpy" in parsed["dependencies"]


def test_builtin_explicit_exporter(loaded_plugin_manager, test_env):
    """Test the built-in explicit environment exporter."""
    # Test that exporter is available
    exporter_config = loaded_plugin_manager.get_environment_exporter_by_format(
        format_name="explicit"
    )
    assert exporter_config is not None
    assert exporter_config.name == "explicit"

    # Test export functionality
    exporter = exporter_config.handler()
    result = exporter.export(test_env, "explicit")

    # Verify explicit format content
    expected_content = ["@EXPLICIT", "python=3.9", "numpy"]
    for content in expected_content:
        assert content in result

    # Critically important: ensure package specs are NOT commented out
    lines = result.split("\n")
    package_lines = [
        line
        for line in lines
        if line and not line.startswith("#") and line != "@EXPLICIT"
    ]
    assert "python=3.9" in package_lines, (
        "python=3.9 should be an installable spec, not a comment"
    )
    assert "numpy" in package_lines, (
        "numpy should be an installable spec, not a comment"
    )


def test_get_environment_exporters(loaded_plugin_manager):
    """Test getting environment exporters mapping."""
    exporters = loaded_plugin_manager.get_environment_exporters()

    # Convert to list to work with the iterable
    exporter_list = list(exporters)
    exporter_names = [exporter.name for exporter in exporter_list]

    # Should include expected formats
    assert "environment-yaml" in exporter_names
    assert "environment-json" in exporter_names
    assert "explicit" in exporter_names
    assert isinstance(exporter_list, list)
    assert all(hasattr(exporter, "name") for exporter in exporter_list)


@pytest.mark.parametrize(
    "filename,expected_format",
    [
        ("environment.yaml", "environment-yaml"),
        ("environment.yml", "environment-yaml"),
        ("environment.json", "environment-json"),
        ("requirements.txt", "explicit"),
        ("my-env.yaml", None),  # Not a recognized default filename
        ("env.unknown", None),
    ],
)
def test_detect_environment_exporter(loaded_plugin_manager, filename, expected_format):
    """Test detecting exporter by exact filename matching."""
    exporter = loaded_plugin_manager.detect_environment_exporter(filename)

    if expected_format is None:
        assert exporter is None
    else:
        assert exporter is not None
        assert exporter.name == expected_format


@pytest.mark.parametrize(
    "format_name,should_exist",
    [
        ("environment-yaml", True),
        ("environment-json", True),
        ("explicit", True),
        ("yaml", True),  # Test alias
        ("json", True),  # Test alias
        ("unknown", False),
    ],
)
def test_get_environment_exporter_by_format(
    loaded_plugin_manager, format_name, should_exist
):
    """Test getting exporter by format name including aliases."""
    exporter = loaded_plugin_manager.get_environment_exporter_by_format(format_name)

    if should_exist:
        assert exporter is not None
        # For aliases, verify that an exporter was found and has a valid canonical name
        assert exporter.name is not None
        assert len(exporter.name) > 0

        # If format_name is an alias, verify it actually resolves to the exporter
        exporter_instance = exporter.handler()
        is_alias = format_name in exporter_instance.aliases
        is_canonical = format_name == exporter.name
        assert is_alias or is_canonical, (
            f"Format '{format_name}' should be either canonical name or alias"
        )
    else:
        assert exporter is None


def test_yaml_exporter_handles_missing_name(loaded_plugin_manager):
    """Test YAML exporter handles case where environment has no name."""
    exporter_config = loaded_plugin_manager.get_environment_exporter_by_format(
        "environment-yaml"
    )
    assert exporter_config is not None

    exporter = exporter_config.handler()
    # Create environment without name
    env = Environment(
        name=None,
        prefix="/tmp/test-env",
        platform="linux-64",
        requested_packages=[MatchSpec("python")],
    )

    result = exporter.export(env, "environment-yaml")
    # Should still work, just with name: None
    assert "name:" in result


def test_custom_exporter_aliases():
    """Test that custom exporters can define their own aliases."""

    class CustomExporter(EnvironmentExporter):
        format = "custom-format"
        aliases = ["custom", "cf", "my-format"]

        def export(self, env, format):
            return f"Custom export: {env.name}"

    # Test that the exporter defines its aliases correctly
    exporter = CustomExporter()
    assert exporter.aliases == ["custom", "cf", "my-format"]

    # Test that base class default is empty (check class attribute directly)
    assert EnvironmentExporter.aliases == []


def test_dynamic_alias_resolution(loaded_plugin_manager):
    """Test that alias resolution works dynamically without hardcoded mappings."""

    # Test that yaml alias resolves correctly
    yaml_exporter = loaded_plugin_manager.get_environment_exporter_by_format("yaml")
    assert yaml_exporter is not None

    # Test that the resolved exporter actually defines "yaml" as an alias
    yaml_instance = yaml_exporter.handler()
    assert "yaml" in yaml_instance.aliases

    # Test that json alias resolves correctly
    json_exporter = loaded_plugin_manager.get_environment_exporter_by_format("json")
    assert json_exporter is not None

    # Test that the resolved exporter actually defines "json" as an alias
    json_instance = json_exporter.handler()
    assert "json" in json_instance.aliases

    # Test that canonical names still work
    canonical_yaml = loaded_plugin_manager.get_environment_exporter_by_format(
        "environment-yaml"
    )
    canonical_json = loaded_plugin_manager.get_environment_exporter_by_format(
        "environment-json"
    )

    # Verify aliases resolve to the same exporters as canonical names
    assert yaml_exporter.name == canonical_yaml.name
    assert json_exporter.name == canonical_json.name


def test_builtin_exporters_define_expected_aliases():
    """Test that built-in exporters define their expected aliases."""

    yaml_exporter = YamlEnvironmentExporter()
    assert "yaml" in yaml_exporter.aliases

    json_exporter = JsonEnvironmentExporter()
    assert "json" in json_exporter.aliases

    explicit_exporter = ExplicitEnvironmentExporter()
    assert explicit_exporter.aliases == []  # No aliases for explicit


def test_get_environment_exporter_unified(loaded_plugin_manager):
    """Test the unified get_environment_exporter entry point."""
    # Test by format
    exporter = loaded_plugin_manager.get_environment_exporter(
        format_name="environment-yaml"
    )
    assert exporter is not None
    assert exporter.name == "environment-yaml"

    # Test by filename
    exporter = loaded_plugin_manager.get_environment_exporter(
        filename="environment.json"
    )
    assert exporter is not None
    assert exporter.name == "environment-json"

    # Test error cases
    with pytest.raises(
        CondaValueError, match="Must provide either filename or format_name"
    ):
        loaded_plugin_manager.get_environment_exporter()

    with pytest.raises(
        CondaValueError, match="Cannot specify both filename and format_name"
    ):
        loaded_plugin_manager.get_environment_exporter(
            filename="environment.yaml", format_name="environment-json"
        )
