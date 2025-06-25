# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Tests for environment exporter plugins."""

from __future__ import annotations

import json

import pytest

from conda.exceptions import CondaValueError
from conda.models.environment import Environment
from conda.models.match_spec import MatchSpec
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
    extensions = {".test"}

    def can_handle(
        self, filename: str | None = None, format: str | None = None
    ) -> bool:
        """Check if this exporter can handle the given filename and/or format."""
        # Check format if provided
        if format is not None:
            if format != self.format:
                return False

        # Check filename if provided
        if filename is not None:
            if not any(filename.endswith(ext) for ext in self.extensions):
                return False

        # If we get here, all provided criteria matched
        return True

    def export(self, env: Environment, format: str) -> str:
        if not self.can_handle(format=format):
            raise CondaValueError(
                f"{self.__class__.__name__} doesn't support format: {format}"
            )
        return f"TEST FORMAT: {env.name}"


def test_environment_exporter_base_class():
    """Test the EnvironmentExporter abstract class."""
    exporter = TestEnvironmentExporter()

    # Test format attribute
    assert exporter.format == "test"

    # Test filename support
    assert exporter.can_handle(filename="env.test")
    assert not exporter.can_handle(filename="env.yaml")

    # Test format support
    assert exporter.can_handle(format="test")
    assert not exporter.can_handle(format="yaml")

    # Test combined filename and format support
    assert exporter.can_handle(filename="env.test", format="test")
    assert not exporter.can_handle(filename="env.test", format="yaml")
    assert not exporter.can_handle(filename="env.yaml", format="test")

    # Test export functionality
    env = Environment(
        name="test-env",
        prefix="/tmp/test-env",
        platform="linux-64",
        requested_packages=[MatchSpec("python")],
    )
    result = exporter.export(env, "test")
    assert result == "TEST FORMAT: test-env"


@pytest.mark.parametrize(
    "format_name,expected_content",
    [
        ("yaml", ["name: test-env", "python=3.9", "numpy"]),
        ("json", None),  # JSON will be validated separately
    ],
)
def test_builtin_exporters(
    loaded_plugin_manager, test_env, format_name, expected_content
):
    """Test the built-in environment exporters."""
    # Test that exporter is available
    exporter_config = loaded_plugin_manager.get_environment_exporter_by_format(
        format_name
    )
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
        parsed = json.loads(result)
        assert parsed["name"] == "test-env"
        assert "python=3.9" in parsed["dependencies"]
        assert "numpy" in parsed["dependencies"]


def test_get_environment_exporters(loaded_plugin_manager):
    """Test getting environment exporters mapping."""
    exporters = loaded_plugin_manager.get_environment_exporters()

    # Should include expected formats
    assert "yaml" in exporters
    assert "json" in exporters
    assert isinstance(exporters, dict)
    assert all(isinstance(fmt, str) for fmt in exporters.keys())


@pytest.mark.parametrize(
    "filename,expected_format",
    [
        ("env.yaml", "yaml"),
        ("env.yml", "yaml"),
        ("env.json", "json"),
        ("env.unknown", None),
    ],
)
def test_detect_environment_exporter(loaded_plugin_manager, filename, expected_format):
    """Test detecting exporter by filename extension."""
    exporter = loaded_plugin_manager.detect_environment_exporter(filename)

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
def test_get_environment_exporter_by_format(
    loaded_plugin_manager, format_name, should_exist
):
    """Test getting exporter by format name."""
    exporter = loaded_plugin_manager.get_environment_exporter_by_format(format_name)

    if should_exist:
        assert exporter is not None
        assert exporter.name == format_name
    else:
        assert exporter is None


def test_yaml_exporter_extensions(loaded_plugin_manager):
    """Test that YAML exporter supports expected file extensions."""
    yaml_exporter = loaded_plugin_manager.get_environment_exporter_by_format("yaml")
    assert yaml_exporter is not None

    yaml_instance = yaml_exporter.handler()
    assert ".yaml" in yaml_instance.extensions
    assert ".yml" in yaml_instance.extensions


def test_exporter_error_handling(loaded_plugin_manager, test_env):
    """Test exporter error handling for unsupported formats."""
    exporter_config = loaded_plugin_manager.get_environment_exporter_by_format("yaml")
    assert exporter_config is not None

    exporter = exporter_config.handler()
    with pytest.raises(CondaValueError, match="doesn't support format"):
        exporter.export(test_env, "unsupported")


def test_yaml_exporter_handles_missing_name(loaded_plugin_manager):
    """Test YAML exporter handles case where environment has no name."""
    exporter_config = loaded_plugin_manager.get_environment_exporter_by_format("yaml")
    assert exporter_config is not None

    exporter = exporter_config.handler()
    # Create environment without name
    env = Environment(
        name=None,
        prefix="/tmp/test-env",
        platform="linux-64",
        requested_packages=[MatchSpec("python")],
    )

    result = exporter.export(env, "yaml")
    # Should still work, just with name: None
    assert "name:" in result


def test_get_environment_exporter_unified(loaded_plugin_manager):
    """Test the unified get_environment_exporter entry point."""
    # Test by format
    exporter = loaded_plugin_manager.get_environment_exporter(format_name="yaml")
    assert exporter is not None
    assert exporter.name == "yaml"

    # Test by filename
    exporter = loaded_plugin_manager.get_environment_exporter(filename="env.json")
    assert exporter is not None
    assert exporter.name == "json"

    # Test error cases
    with pytest.raises(
        CondaValueError, match="Must provide either filename or format_name"
    ):
        loaded_plugin_manager.get_environment_exporter()

    with pytest.raises(
        CondaValueError, match="Cannot specify both filename and format_name"
    ):
        loaded_plugin_manager.get_environment_exporter(
            filename="env.yaml", format_name="json"
        )
