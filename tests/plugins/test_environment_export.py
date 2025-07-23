# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Tests for environment export functionality."""

from __future__ import annotations

import json

import pytest
import yaml

from conda.exceptions import CondaValueError, PluginError
from conda.models.channel import Channel
from conda.models.environment import Environment
from conda.models.match_spec import MatchSpec
from conda.models.records import PackageRecord
from conda.plugins.types import CondaEnvironmentExporter


@pytest.fixture
def plugin_manager_with_exporters(plugin_manager):
    """Get plugin manager with environment exporter plugins loaded."""
    from conda.plugins.environment_exporters import (
        environment_yml,
        explicit,
        requirements_txt,
    )

    plugin_manager.load_plugins(environment_yml, explicit, requirements_txt)
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


@pytest.fixture
def test_env_with_explicit_packages():
    """Create a test environment with explicit packages (URLs) for explicit exporter testing."""
    # Create mock PackageRecord objects with proper URLs
    python_pkg = PackageRecord(
        name="python",
        version="3.9.7",
        build="h12debd9_0",
        build_number=0,
        channel=Channel("https://repo.anaconda.com/pkgs/main"),
        subdir="linux-64",
        fn="python-3.9.7-h12debd9_0.conda",
        url="https://repo.anaconda.com/pkgs/main/linux-64/python-3.9.7-h12debd9_0.conda",
    )

    numpy_pkg = PackageRecord(
        name="numpy",
        version="1.21.0",
        build="py39hdbf815f_0",
        build_number=0,
        channel=Channel("https://repo.anaconda.com/pkgs/main"),
        subdir="linux-64",
        fn="numpy-1.21.0-py39hdbf815f_0.conda",
        url="https://repo.anaconda.com/pkgs/main/linux-64/numpy-1.21.0-py39hdbf815f_0.conda",
    )

    return Environment(
        name="test-env",
        prefix="/tmp/test-env",
        platform="linux-64",
        explicit_packages=[python_pkg, numpy_pkg],
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
    """Test the built-in explicit environment exporter with requested packages only."""
    # Test that exporter is available
    exporter_config = plugin_manager_with_exporters.get_environment_exporter_by_format(
        format_name="explicit"
    )
    assert exporter_config is not None
    assert exporter_config.name == "explicit"

    # Test export functionality with requested packages only (should fail for explicit exporter)
    try:
        exporter_config.export(test_env)
        assert False, (
            "Expected CondaValueError for explicit exporter with requested packages only"
        )
    except CondaValueError as e:
        assert "Cannot export explicit format" in str(e)
        assert "requirements" in str(e)


def test_builtin_requirements_exporter(plugin_manager_with_exporters, test_env):
    """Test the built-in requirements environment exporter with requested packages."""
    # Test that exporter is available
    exporter_config = plugin_manager_with_exporters.get_environment_exporter_by_format(
        format_name="requirements"
    )
    assert exporter_config is not None
    assert exporter_config.name == "requirements"

    # Test export functionality with requested packages (should create requirements file)
    result = exporter_config.export(test_env)

    # Verify it's NOT an @EXPLICIT format (CEP 23 compliance)
    assert "@EXPLICIT" not in result

    # Verify it's a requirements file with MatchSpec strings
    assert "# Note: This is a conda requirements file (MatchSpec format)" in result
    assert "# Contains conda package specifications, not pip requirements" in result

    # Verify platform information is included
    assert f"# platform: {test_env.platform}" in result

    # Check that MatchSpec strings are preserved (not converted)
    lines = result.split("\n")
    package_specs = [line for line in lines if line and not line.startswith("#")]

    # Should have 2 package specifications
    assert len(package_specs) == 2

    # Check the MatchSpec format (should use original MatchSpec string representation)
    specs_text = "\n".join(package_specs)
    assert "python" in specs_text
    assert "numpy" in specs_text


def test_builtin_explicit_exporter_with_urls(
    plugin_manager_with_exporters, test_env_with_explicit_packages
):
    """Test the built-in explicit environment exporter with actual package URLs."""
    # Test that exporter is available
    exporter_config = plugin_manager_with_exporters.get_environment_exporter_by_format(
        format_name="explicit"
    )
    assert exporter_config is not None

    # Test export functionality with explicit packages (should create true explicit file)
    result = exporter_config.export(test_env_with_explicit_packages)

    # Verify it IS an @EXPLICIT format (CEP 23 compliance)
    assert "@EXPLICIT" in result

    # Verify platform information is included
    assert f"# platform: {test_env_with_explicit_packages.platform}" in result

    # Check that URLs are included
    lines = result.split("\n")
    url_lines = [line for line in lines if line.startswith("https://")]

    # Should have URLs for both packages
    assert len(url_lines) == 2
    assert "python-3.9.7-h12debd9_0.conda" in result
    assert "numpy-1.21.0-py39hdbf815f_0.conda" in result


def test_requirements_exporter_with_explicit_packages(
    plugin_manager_with_exporters, test_env_with_explicit_packages
):
    """Test the requirements exporter fails appropriately when only explicit packages are available."""
    # Test that exporter is available
    exporter_config = plugin_manager_with_exporters.get_environment_exporter_by_format(
        format_name="requirements"
    )
    assert exporter_config is not None

    # Test export functionality with explicit packages only (should fail for requirements exporter)
    try:
        exporter_config.export(test_env_with_explicit_packages)
        assert False, (
            "Expected CondaValueError for requirements exporter with explicit packages only"
        )
    except CondaValueError as e:
        assert "Cannot export requirements format" in str(e)
        assert "explicit" in str(e)


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
    assert "requirements" in exporter_names
    assert isinstance(exporter_list, list)
    assert all(hasattr(exporter, "name") for exporter in exporter_list)


@pytest.mark.parametrize(
    "filename,expected_format",
    [
        ("environment.yaml", "environment-yaml"),
        ("environment.yml", "environment-yaml"),
        ("environment.json", "environment-json"),
        ("explicit.txt", "explicit"),
        ("requirements.txt", "requirements"),
        ("spec.txt", "requirements"),
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
        ("requirements", True),
        ("yaml", True),  # Test alias
        ("json", True),  # Test alias
        ("txt", True),  # Test alias for requirements
        ("reqs", True),  # Test alias for requirements
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

    # Test requirements exporter has txt and reqs aliases
    requirements_exporter = (
        plugin_manager_with_exporters.get_environment_exporter_by_format("requirements")
    )
    assert requirements_exporter is not None
    assert "txt" in requirements_exporter.aliases
    assert "reqs" in requirements_exporter.aliases


def test_alias_normalization_and_collision_detection():
    """Test that aliases are normalized and collision detection works."""
    # Test alias normalization
    exporter = CondaEnvironmentExporter(
        name="test-exporter",
        aliases=(" YAML ", "YML", "  json  "),  # Mixed case and whitespace
        default_filenames=("test.yaml",),
        export=lambda env: "test",
    )

    # Aliases should be normalized to lowercase and stripped
    assert exporter.aliases == ("yaml", "yml", "json")

    # Test invalid alias type raises error
    with pytest.raises(PluginError, match="Invalid plugin aliases"):
        CondaEnvironmentExporter(
            name="bad-exporter",
            aliases=(123, "valid"),  # Non-string alias
            default_filenames=("test.yaml",),
            export=lambda env: "test",
        )
