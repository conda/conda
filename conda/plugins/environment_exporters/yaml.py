# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""YAML environment exporter plugin."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .. import hookimpl
from ..types import CondaEnvironmentExporter, EnvironmentExporter

if TYPE_CHECKING:
    from ...models.environment import Environment


class YAMLExporter(EnvironmentExporter):
    """Exporter for YAML environment format."""

    format = "yaml"
    extensions = {".yaml", ".yml"}

    def can_handle(self, filename: str) -> bool:
        """Check if this exporter can handle the given filename."""
        return any(filename.endswith(ext) for ext in self.extensions)

    def export(self, env: Environment, format: str) -> str:
        """Export Environment to YAML format."""
        self.validate(format)

        from ...common.serialize import yaml_safe_dump

        env_dict = env.to_dict()
        yaml_content = yaml_safe_dump(env_dict)
        if yaml_content is None:
            raise ValueError("Failed to export environment to YAML")
        return yaml_content


@hookimpl(tryfirst=True)  # Ensure built-in YAML exporter loads first and has priority
def conda_environment_exporters():
    yield CondaEnvironmentExporter(
        name="yaml",
        handler=YAMLExporter,
    )
