# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Tests for environment export functionality."""

from __future__ import annotations

import json

import pytest
import yaml

from conda.exceptions import CondaValueError
from conda.models.environment import Environment
from conda.models.match_spec import MatchSpec


@pytest.fixture
def plugin_manager_with_exporters(plugin_manager):
    """Get plugin manager with environment exporter plugins loaded."""
    from conda.plugins.environment_exporters import explicit, json, yaml

    plugin_manager.load_plugins(explicit, json, yaml)
    return plugin_manager


@pytest.fixture
def test_env():
    """Create a test environment for exporter testing."""
    return Environment(
        name="test-env",
        prefix="/tmp/test-env",
        platform="linux-64",
        requested_packages=[MatchSpec("python=3.9"), MatchSpec("numpy")],
    )


def test_builtin_yaml_exporter(plugin_manager_with_exporters, test_env):
    """Test the built-in YAML environment exporter."""
    # Test that exporter is available
    exporter_config = plugin_manager_with_exporters.get_environment_exporter_by_format(
        format_name="environment-yaml"
    )
    assert exporter_config is not None
    assert exporter_config.name == "environment-yaml"

    # Test export functionality using the export callable directly
    result = exporter_config.export(test_env)

    # Verify it's valid YAML by parsing it
    parsed = yaml.safe_load(result)

    # Check actual structure, not exact formatting
    assert parsed["name"] == "test-env"
    assert "dependencies" in parsed
    assert len(parsed["dependencies"]) >= 2  # At least the packages we put in

    # Verify our test packages are represented somehow in dependencies
    deps_str = str(parsed["dependencies"])
    assert "python" in deps_str
    assert "numpy" in deps_str


def test_builtin_json_exporter(plugin_manager_with_exporters, test_env):
    """Test the built-in JSON environment exporter."""
    # Test that exporter is available
    exporter_config = plugin_manager_with_exporters.get_environment_exporter_by_format(
        format_name="environment-json"
    )
    assert exporter_config is not None
    assert exporter_config.name == "environment-json"

    # Test export functionality using the export callable directly
    result = exporter_config.export(test_env)

    # Parse JSON to verify structure
    parsed = json.loads(result)
    assert parsed["name"] == "test-env"
    assert "dependencies" in parsed
    assert len(parsed["dependencies"]) >= 2  # At least the packages we put in

    # Verify our test packages are present
    deps_str = str(parsed["dependencies"])
    assert "python" in deps_str
    assert "numpy" in deps_str


def test_builtin_explicit_exporter(plugin_manager_with_exporters, test_env):
    """Test the built-in explicit environment exporter."""
    # Test that exporter is available
    exporter_config = plugin_manager_with_exporters.get_environment_exporter_by_format(
        format_name="explicit"
    )
    assert exporter_config is not None
    assert exporter_config.name == "explicit"

    # Test export functionality using the export callable directly
    result = exporter_config.export(test_env)

    # Verify it's an @EXPLICIT format
    assert "@EXPLICIT" in result

    # Verify it contains package specifications that are NOT commented out
    # This is the critical bug we fixed - package specs were being commented with "#"
    lines = result.split("\n")
    package_specs = [
        line
        for line in lines
        if line and not line.startswith("#") and line != "@EXPLICIT"
    ]

    # Should have actual package specifications
    assert len(package_specs) > 0, "Should contain package specifications"

    # Verify none of our package specs got accidentally commented out
    for spec in package_specs:
        assert not spec.strip().startswith("# "), (
            f"Package spec should not be commented out: {spec}"
        )


def test_get_environment_exporters(plugin_manager_with_exporters):
    """Test getting environment exporters mapping."""
    exporters = plugin_manager_with_exporters.get_environment_exporters()

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
def test_detect_environment_exporter(
    plugin_manager_with_exporters, filename, expected_format
):
    """Test detecting exporter by exact filename matching."""
    exporter = plugin_manager_with_exporters.detect_environment_exporter(filename)

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
    plugin_manager_with_exporters, format_name, should_exist
):
    """Test getting exporter by format name including aliases."""
    exporter = plugin_manager_with_exporters.get_environment_exporter_by_format(
        format_name
    )

    if should_exist:
        assert exporter is not None
        # For aliases, verify that an exporter was found and has a valid canonical name
        assert exporter.name is not None
        assert len(exporter.name) > 0

        # If format_name is an alias, verify it actually resolves to the exporter
        is_alias = format_name in exporter.aliases
        is_canonical = format_name == exporter.name
        assert is_alias or is_canonical, (
            f"Format '{format_name}' should be either canonical name or alias"
        )
    else:
        assert exporter is None


def test_yaml_exporter_handles_missing_name(plugin_manager_with_exporters):
    """Test YAML exporter handles case where environment has no name."""
    exporter_config = plugin_manager_with_exporters.get_environment_exporter_by_format(
        "environment-yaml"
    )
    assert exporter_config is not None

    # Create environment without name
    env = Environment(
        name=None,  # No name
        prefix="/tmp/test-env",
        platform="linux-64",
        requested_packages=[MatchSpec("python")],
    )

    # Export should still work
    result = exporter_config.export(env)

    # Parse YAML to verify structure instead of checking string format
    parsed = yaml.safe_load(result)

    # Should have a name field (even if None/null)
    assert "name" in parsed


def test_dynamic_alias_resolution(plugin_manager_with_exporters):
    """Test that alias resolution works dynamically without hardcoded mappings."""

    # Test that yaml alias resolves correctly
    yaml_exporter = plugin_manager_with_exporters.get_environment_exporter_by_format(
        "yaml"
    )
    assert yaml_exporter is not None

    # Test that the resolved exporter actually defines "yaml" as an alias
    assert "yaml" in yaml_exporter.aliases

    # Test that json alias resolves correctly
    json_exporter = plugin_manager_with_exporters.get_environment_exporter_by_format(
        "json"
    )
    assert json_exporter is not None

    # Test that the resolved exporter actually defines "json" as an alias
    assert "json" in json_exporter.aliases

    # Test that canonical names still work
    canonical_yaml = plugin_manager_with_exporters.get_environment_exporter_by_format(
        "environment-yaml"
    )
    canonical_json = plugin_manager_with_exporters.get_environment_exporter_by_format(
        "environment-json"
    )

    # Verify aliases resolve to the same exporters as canonical names
    assert yaml_exporter.name == canonical_yaml.name
    assert json_exporter.name == canonical_json.name


def test_builtin_exporters_define_expected_aliases(plugin_manager_with_exporters):
    """Test that built-in exporters define their expected aliases."""

    # Test YAML exporter aliases
    yaml_exporter = plugin_manager_with_exporters.get_environment_exporter_by_format(
        "environment-yaml"
    )
    assert yaml_exporter is not None
    assert "yaml" in yaml_exporter.aliases

    # Test JSON exporter aliases
    json_exporter = plugin_manager_with_exporters.get_environment_exporter_by_format(
        "environment-json"
    )
    assert json_exporter is not None
    assert "json" in json_exporter.aliases

    # Test explicit exporter has no aliases
    explicit_exporter = (
        plugin_manager_with_exporters.get_environment_exporter_by_format("explicit")
    )
    assert explicit_exporter is not None
    assert explicit_exporter.aliases == ()


def test_get_environment_exporter_unified(plugin_manager_with_exporters):
    """Test the unified get_environment_exporter entry point."""
    # Test by format
    exporter = plugin_manager_with_exporters.get_environment_exporter(
        format_name="environment-yaml"
    )
    assert exporter is not None
    assert exporter.name == "environment-yaml"

    # Test by filename
    exporter = plugin_manager_with_exporters.get_environment_exporter(
        filename="environment.json"
    )
    assert exporter is not None
    assert exporter.name == "environment-json"

    # Test error cases
    with pytest.raises(
        CondaValueError, match="Must provide either filename or format_name"
    ):
        plugin_manager_with_exporters.get_environment_exporter()

    with pytest.raises(
        CondaValueError, match="Cannot specify both filename and format_name"
    ):
        plugin_manager_with_exporters.get_environment_exporter(
            filename="environment.yaml", format_name="environment-json"
        )
