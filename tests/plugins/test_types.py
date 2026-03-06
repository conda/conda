# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Tests for plugin type classes (CondaEnvironmentSpecifier and CondaEnvironmentExporter)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from conda.env.specs.requirements import RequirementsSpec
from conda.plugins.types import CondaEnvironmentExporter, CondaEnvironmentSpecifier

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

    def test_is_lockfile_inferred_from_name(self):
        """When is_lockfile is not set and name contains 'lock', it is inferred as True."""
        # Various cases of "lock" in the name
        for name in ["lockfile", "my-lock", "conda-lock", "LOCK", "Lock-File"]:
            specifier = CondaEnvironmentSpecifier(
                name=name,
                environment_spec=RequirementsSpec,
            )
            assert specifier.is_lockfile is True, f"Failed for name: {name}"

    def test_is_lockfile_not_inferred_without_lock(self):
        """When is_lockfile is not set and name doesn't contain 'lock', it defaults to False."""
        specifier = CondaEnvironmentSpecifier(
            name="test-spec",
            environment_spec=RequirementsSpec,
        )
        assert specifier.is_lockfile is False

    def test_explicit_is_lockfile_true_preserved(self):
        """When is_lockfile is explicitly set to True, it is preserved."""
        specifier = CondaEnvironmentSpecifier(
            name="explicit",
            environment_spec=RequirementsSpec,
            is_lockfile=True,
        )
        assert specifier.is_lockfile is True

    def test_explicit_is_lockfile_false_overridden_by_inference(self):
        """When is_lockfile is False but name contains 'lock', inference overrides it."""
        # This is expected behavior per the implementation notes
        specifier = CondaEnvironmentSpecifier(
            name="my-lockfile",
            environment_spec=RequirementsSpec,
            is_lockfile=False,  # Explicitly set to False
        )
        # But inference overrides because "lock" is in the name
        assert specifier.is_lockfile is True

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
        assert specifier.is_lockfile is False  # Defaults to False
        assert specifier.default_filenames == ("test.txt",)
        assert specifier.aliases == ("test",)


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

    def test_is_lockfile_inferred_from_name(self):
        """When is_lockfile is not set and name contains 'lock', it is inferred as True."""
        # Various cases of "lock" in the name
        for name in ["lockfile", "my-lock", "conda-lock", "LOCK", "Lock-File"]:
            exporter = CondaEnvironmentExporter(
                name=name,
                aliases=(),
                default_filenames=(),
                export=self.dummy_export,
            )
            assert exporter.is_lockfile is True, f"Failed for name: {name}"

    def test_is_lockfile_not_inferred_without_lock(self):
        """When is_lockfile is not set and name doesn't contain 'lock', it defaults to False."""
        exporter = CondaEnvironmentExporter(
            name="test-export",
            aliases=(),
            default_filenames=(),
            export=self.dummy_export,
        )
        assert exporter.is_lockfile is False

    def test_explicit_is_lockfile_true_preserved(self):
        """When is_lockfile is explicitly set to True, it is preserved."""
        exporter = CondaEnvironmentExporter(
            name="explicit",
            aliases=(),
            default_filenames=(),
            export=self.dummy_export,
            is_lockfile=True,
        )
        assert exporter.is_lockfile is True

    def test_explicit_is_lockfile_false_overridden_by_inference(self):
        """When is_lockfile is False but name contains 'lock', inference overrides it."""
        # This is expected behavior per the implementation notes
        exporter = CondaEnvironmentExporter(
            name="my-lockfile",
            aliases=(),
            default_filenames=(),
            export=self.dummy_export,
            is_lockfile=False,  # Explicitly set to False
        )
        # But inference overrides because "lock" is in the name
        assert exporter.is_lockfile is True

    def test_backward_compatibility_without_new_fields(self):
        """Plugin works without providing description or is_lockfile fields."""
        # This ensures third-party plugins remain compatible
        exporter = CondaEnvironmentExporter(
            name="test-export",
            aliases=("test",),
            default_filenames=("test.txt",),
            export=self.dummy_export,
        )
        assert exporter.description == "test-export"  # Defaults to name
        assert exporter.is_lockfile is False  # Defaults to False
        assert exporter.default_filenames == ("test.txt",)
        assert exporter.aliases == ("test",)
