# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Tests for environment exporter plugins."""

import pytest

from conda.env.env import Environment
from conda.plugins.manager import get_plugin_manager
from conda.plugins.types import CondaEnvironmentExporter, EnvironmentExporter


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


def test_builtin_yaml_exporter():
    """Test the built-in YAML environment exporter."""
    plugin_manager = get_plugin_manager()

    # Test that YAML exporter is available
    exporter_config = plugin_manager.find_exporter_by_format("yaml")
    assert exporter_config is not None
    assert exporter_config.name == "yaml"

    # Test YAML export functionality
    exporter = exporter_config.handler()
    env = Environment(name="test-env", dependencies=["python=3.9", "numpy"])
    result = exporter.export(env, "yaml")

    # Verify it contains expected YAML content
    assert "name: test-env" in result
    assert "python=3.9" in result
    assert "numpy" in result


def test_builtin_json_exporter():
    """Test the built-in JSON environment exporter."""
    plugin_manager = get_plugin_manager()

    # Test that JSON exporter is available
    exporter_config = plugin_manager.find_exporter_by_format("json")
    assert exporter_config is not None
    assert exporter_config.name == "json"

    # Test JSON export functionality
    exporter = exporter_config.handler()
    env = Environment(name="test-env", dependencies=["python=3.9", "numpy"])
    result = exporter.export(env, "json")

    # Verify it's valid JSON
    import json

    parsed = json.loads(result)
    assert parsed["name"] == "test-env"
    assert "python=3.9" in parsed["dependencies"]
    assert "numpy" in parsed["dependencies"]


def test_get_available_export_formats():
    """Test getting available export formats."""
    plugin_manager = get_plugin_manager()
    formats = plugin_manager.get_available_export_formats()

    # Should include YAML format (canonical name only)
    assert "yaml" in formats
    # Should not include yml as a separate format
    assert "yml" not in formats

    # Should be sorted
    assert formats == sorted(formats)


def test_find_exporter_by_filename():
    """Test finding exporter by filename extension."""
    plugin_manager = get_plugin_manager()

    # Test YAML file extensions
    exporter = plugin_manager.find_exporter_by_filename("env.yaml")
    assert exporter is not None
    assert exporter.name == "yaml"

    exporter = plugin_manager.find_exporter_by_filename("env.yml")
    assert exporter is not None
    assert exporter.name == "yaml"

    # Test unknown extension
    exporter = plugin_manager.find_exporter_by_filename("env.unknown")
    assert exporter is None


def test_find_exporter_by_format():
    """Test the focused find_exporter_by_format method."""
    plugin_manager = get_plugin_manager()

    # Test finding YAML exporter
    yaml_exporter = plugin_manager.find_exporter_by_format("yaml")
    assert yaml_exporter is not None
    assert yaml_exporter.name == "yaml"

    # Test finding JSON exporter
    json_exporter = plugin_manager.find_exporter_by_format("json")
    assert json_exporter is not None
    assert json_exporter.name == "json"

    # Test unknown format returns None
    unknown_exporter = plugin_manager.find_exporter_by_format("unknown")
    assert unknown_exporter is None


def test_format_precedence():
    """Test that we can find exporters by both format and filename."""
    plugin_manager = get_plugin_manager()

    # Test that we can find exporters by format
    yaml_exporter = plugin_manager.find_exporter_by_format("yaml")
    assert yaml_exporter is not None
    assert yaml_exporter.name == "yaml"

    # And we can find by filename
    json_exporter = plugin_manager.find_exporter_by_filename("env.json")
    assert json_exporter is not None
    assert json_exporter.name == "json"


def test_exporter_extensions():
    """Test that exporters properly declare their file extensions."""
    plugin_manager = get_plugin_manager()

    # YAML exporter should support .yaml and .yml
    yaml_exporter = plugin_manager.find_exporter_by_format("yaml")
    assert yaml_exporter is not None
    yaml_instance = yaml_exporter.handler()
    assert ".yaml" in yaml_instance.extensions
    assert ".yml" in yaml_instance.extensions


def test_yaml_exporter_error_handling():
    """Test YAML exporter error handling."""
    plugin_manager = get_plugin_manager()

    # Test that YAML exporter raises error for unsupported format
    exporter_config = plugin_manager.find_exporter_by_format("yaml")
    assert exporter_config is not None

    exporter = exporter_config.handler()
    env = Environment(name="test-env")

    # Test unsupported format error
    with pytest.raises(ValueError, match="doesn't support format"):
        exporter.export(env, "unsupported")


def test_yaml_exporter_handles_none_content(mocker):
    """Test YAML exporter handles case where env.to_yaml() returns None."""
    plugin_manager = get_plugin_manager()
    exporter_config = plugin_manager.find_exporter_by_format("yaml")
    assert exporter_config is not None

    exporter = exporter_config.handler()

    # Create a mock environment that returns None from to_yaml()
    mock_env = mocker.Mock()
    mock_env.to_yaml.return_value = None

    # Test that it raises ValueError when to_yaml() returns None
    with pytest.raises(ValueError, match="Failed to export environment to YAML"):
        exporter.export(mock_env, "yaml")


def test_unknown_format_handling():
    """Test that unknown formats are handled properly by plugin manager."""
    plugin_manager = get_plugin_manager()

    # Unknown format should return None
    unknown_exporter = plugin_manager.find_exporter_by_format("unknown")
    assert unknown_exporter is None

    # Available formats should not include unknown formats, but should include valid ones
    formats = plugin_manager.get_available_export_formats()
    assert "unknown" not in formats
    assert "xml" not in formats
    # JSON is now a valid format
    assert "json" in formats
    assert "yaml" in formats
