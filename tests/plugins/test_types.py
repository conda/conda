# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Tests for plugin type classes (CondaEnvironmentSpecifier and CondaEnvironmentExporter)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from conda.env.specs.requirements import RequirementsSpec
from conda.exceptions import PluginError
from conda.plugins.types import (
    CondaEnvironmentExporter,
    CondaEnvironmentSpecifier,
    CondaSubcommand,
    EnvironmentFormat,
)

if TYPE_CHECKING:
    from conda.models.environment import Environment


def noop_action(args):
    pass


def test_subcommand_aliases_default_to_empty_tuple():
    subcommand = CondaSubcommand(
        name="custom",
        summary="Custom command.",
        action=noop_action,
    )

    assert subcommand.aliases == ()


def test_subcommand_aliases_normalized_and_deduplicated():
    subcommand = CondaSubcommand(
        name=" custom ",
        summary="Custom command.",
        action=noop_action,
        aliases=(" Alternate ", "alternate", "Other"),
    )

    assert subcommand.name == "custom"
    assert subcommand.aliases == ("alternate", "other")


@pytest.mark.parametrize(
    "aliases",
    [
        pytest.param(("",), id="empty-alias"),
        pytest.param(("custom",), id="alias-matches-name"),
        pytest.param((None,), id="non-string-alias"),
        pytest.param("alternate", id="aliases-is-string"),
    ],
)
def test_subcommand_invalid_aliases_raise_plugin_error(aliases):
    with pytest.raises(PluginError, match="Invalid plugin aliases"):
        CondaSubcommand(
            name="custom",
            summary="Custom command.",
            action=noop_action,
            aliases=aliases,
        )


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
