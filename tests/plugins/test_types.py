# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Tests for plugin type classes (CondaEnvironmentSpecifier and CondaEnvironmentExporter)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from conda.env.specs.requirements import RequirementsSpec
from conda.plugins.types import (
    CondaEnvironmentExporter,
    CondaEnvironmentSpecifier,
    EnvironmentFormat,
)

if TYPE_CHECKING:
    from conda.models.environment import Environment


class TestCondaEnvironmentSpecifier:
    """Tests for CondaEnvironmentSpecifier plugin type."""

    def test_description_defaults_to_name(self):
        """When description is not provided, it defaults to the name."""
        specifier = CondaEnvironmentSpecifier(
            name="test-spec",
            environment_spec=RequirementsSpec,
        )
        assert specifier.description == "test-spec"

    def test_explicit_description_preserved(self):
        """When description is explicitly provided, it is preserved."""
        specifier = CondaEnvironmentSpecifier(
            name="test-spec",
            environment_spec=RequirementsSpec,
            description="Custom description",
        )
        assert specifier.description == "Custom description"

    def test_backward_compatibility_without_new_fields(self):
        """Plugin works without providing description or is_lockfile fields."""
        # This ensures third-party plugins remain compatible
        specifier = CondaEnvironmentSpecifier(
            name="test-spec",
            environment_spec=RequirementsSpec,
            default_filenames=("test.txt",),
            aliases=("test",),
        )
        assert specifier.description == "test-spec"  # Defaults to name
        assert specifier.default_filenames == ("test.txt",)
        assert specifier.aliases == ("test",)
        assert specifier.environment_format == EnvironmentFormat.environment


class TestCondaEnvironmentExporter:
    """Tests for CondaEnvironmentExporter plugin type."""

    @staticmethod
    def dummy_export(env: Environment) -> str:
        """Dummy export function for testing."""
        return f"name: {env.name}"

    def test_description_defaults_to_name(self):
        """When description is not provided, it defaults to the name."""
        exporter = CondaEnvironmentExporter(
            name="test-export",
            aliases=(),
            default_filenames=(),
            export=self.dummy_export,
        )
        assert exporter.description == "test-export"

    def test_explicit_description_preserved(self):
        """When description is explicitly provided, it is preserved."""
        exporter = CondaEnvironmentExporter(
            name="test-export",
            aliases=(),
            default_filenames=(),
            export=self.dummy_export,
            description="Custom description",
        )
        assert exporter.description == "Custom description"

    def test_backward_compatibility_without_new_fields(self):
        """Plugin works without providing description or environment_format fields."""
        # This ensures third-party plugins remain compatible
        exporter = CondaEnvironmentExporter(
            name="test-export",
            aliases=("test",),
            default_filenames=("test.txt",),
            export=self.dummy_export,
        )
        assert exporter.description == "test-export"  # Defaults to name
        assert exporter.default_filenames == ("test.txt",)
        assert exporter.aliases == ("test",)
        assert exporter.environment_format == EnvironmentFormat.environment
