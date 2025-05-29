# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""YAML environment exporter plugin."""

from typing import TYPE_CHECKING

from .. import hookimpl
from ..types import CondaEnvironmentExporter, EnvironmentExporter

if TYPE_CHECKING:
    from ...env.env import Environment


class YAMLExporter(EnvironmentExporter):
    """Exporter for YAML environment format."""

    format = "yaml"
    extensions = {".yaml", ".yml"}

    def export(self, env: "Environment", format: str) -> str:
        """Export Environment to YAML format."""
        self.validate(format)

        # Use the existing YAML export functionality
        yaml_content = env.to_yaml()
        if yaml_content is None:
            raise ValueError("Failed to export environment to YAML")
        return yaml_content


@hookimpl(tryfirst=True)  # Ensure built-in YAML exporter loads first and has priority
def conda_environment_exporters():
    yield CondaEnvironmentExporter(
        name="yaml",
        handler=YAMLExporter,
    )
