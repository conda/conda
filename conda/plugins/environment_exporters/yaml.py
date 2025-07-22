# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Built-in conda YAML environment exporter plugin."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ...exceptions import CondaValueError
from ..hookspec import hookimpl
from ..types import CondaEnvironmentExporter, EnvironmentExporter

if TYPE_CHECKING:
    from ...models.environment import Environment


class YamlEnvironmentExporter(EnvironmentExporter):
    """Export Environment to YAML format."""

    aliases = ["yaml"]

    def export(self, env: Environment, format: str) -> str:
        """Export Environment to YAML format."""
        from ...common.serialize import yaml_safe_dump

        # Use the model's own method that follows EnvironmentYaml.to_dict() pattern
        env_dict = env.to_yaml_dict()
        yaml_content = yaml_safe_dump(env_dict)
        if yaml_content is None:
            raise CondaValueError("Failed to export environment to YAML")
        return yaml_content


@hookimpl(tryfirst=True)  # Ensure built-in YAML exporter loads first and has priority
def conda_environment_exporters():
    """Register the built-in YAML environment exporter."""
    yield CondaEnvironmentExporter(
        name="environment-yaml",
        handler=YamlEnvironmentExporter,
        default_filenames=["environment.yaml", "environment.yml"],
    )
