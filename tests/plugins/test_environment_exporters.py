# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Tests for environment exporter plugins."""

import pytest

from conda.env.env import Environment
from conda.plugins.types import EnvironmentExporter


@pytest.fixture
def test_env():
    """Create a test environment for exporter testing."""
    return Environment(name="test-env", dependencies=["python=3.9", "numpy"])


class TestEnvironmentExporter(EnvironmentExporter):
    """Test environment exporter for testing purposes."""

    format = "test"
    extensions = {".test"}

    def export(self, env: Environment, format: str) -> str:
        self.validate(format)
        return f"TEST FORMAT: {env.name}"


def test_environment_exporter_base_class():
    """Test the EnvironmentExporter abstract class."""
    exporter = TestEnvironmentExporter()

    # Test format attribute
    assert exporter.format == "test"

    # Test filename support
    assert exporter.supports("env.test")
    assert not exporter.supports("env.yaml")

    # Test export functionality
    env = Environment(name="test-env")
    result = exporter.export(env, "test")
    assert result == "TEST FORMAT: test-env"


@pytest.mark.parametrize(
    "format_name,expected_content",
    [
        ("yaml", ["name: test-env", "python=3.9", "numpy"]),
        ("json", None),  # JSON will be validated separately
    ],
)
def test_builtin_exporters(plugin_manager, test_env, format_name, expected_content):
    """Test the built-in environment exporters."""
    # Test that exporter is available
    exporter_config = plugin_manager.find_exporter_by_format(format_name)
    assert exporter_config is not None
    assert exporter_config.name == format_name

    # Test export functionality
    exporter = exporter_config.handler()
    result = exporter.export(test_env, format_name)

    if format_name == "yaml":
        # Verify YAML content
        for content in expected_content:
            assert content in result
    elif format_name == "json":
        # Verify it's valid JSON with correct structure
        import json

        parsed = json.loads(result)
        assert parsed["name"] == "test-env"
        assert "python=3.9" in parsed["dependencies"]
        assert "numpy" in parsed["dependencies"]


def test_available_export_formats(plugin_manager):
    """Test getting available export formats."""
    formats = plugin_manager.get_available_export_formats()

    # Should include expected formats
    assert "yaml" in formats
    assert "json" in formats
    # Should not include extensions as separate formats
    assert "yml" not in formats
    # Should be sorted
    assert formats == sorted(formats)


@pytest.mark.parametrize(
    "filename,expected_format",
    [
        ("env.yaml", "yaml"),
        ("env.yml", "yaml"),
        ("env.json", "json"),
        ("env.unknown", None),
    ],
)
def test_find_exporter_by_filename(plugin_manager, filename, expected_format):
    """Test finding exporter by filename extension."""
    exporter = plugin_manager.find_exporter_by_filename(filename)

    if expected_format is None:
        assert exporter is None
    else:
        assert exporter is not None
        assert exporter.name == expected_format


@pytest.mark.parametrize(
    "format_name,should_exist",
    [
        ("yaml", True),
        ("json", True),
        ("unknown", False),
    ],
)
def test_find_exporter_by_format(plugin_manager, format_name, should_exist):
    """Test finding exporter by format name."""
    exporter = plugin_manager.find_exporter_by_format(format_name)

    if should_exist:
        assert exporter is not None
        assert exporter.name == format_name
    else:
        assert exporter is None


def test_yaml_exporter_extensions(plugin_manager):
    """Test that YAML exporter supports expected file extensions."""
    yaml_exporter = plugin_manager.find_exporter_by_format("yaml")
    assert yaml_exporter is not None

    yaml_instance = yaml_exporter.handler()
    assert ".yaml" in yaml_instance.extensions
    assert ".yml" in yaml_instance.extensions


def test_exporter_error_handling(plugin_manager, test_env):
    """Test exporter error handling for unsupported formats."""
    exporter_config = plugin_manager.find_exporter_by_format("yaml")
    assert exporter_config is not None

    exporter = exporter_config.handler()
    with pytest.raises(ValueError, match="doesn't support format"):
        exporter.export(test_env, "unsupported")


def test_yaml_exporter_handles_none_content(plugin_manager, mocker):
    """Test YAML exporter handles case where env.to_yaml() returns None."""
    exporter_config = plugin_manager.find_exporter_by_format("yaml")
    assert exporter_config is not None

    exporter = exporter_config.handler()
    mock_env = mocker.Mock()
    mock_env.to_yaml.return_value = None

    with pytest.raises(ValueError, match="Failed to export environment to YAML"):
        exporter.export(mock_env, "yaml")
