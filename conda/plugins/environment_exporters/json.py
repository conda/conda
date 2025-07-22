# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Built-in conda JSON environment exporter plugin."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ...common.serialize import json
from ..hookspec import hookimpl
from ..types import CondaEnvironmentExporter, EnvironmentExporter

if TYPE_CHECKING:
    from ...models.environment import Environment


class JsonEnvironmentExporter(EnvironmentExporter):
    """Export Environment to JSON format."""

    aliases = ["json"]

    def export(self, env: Environment, format: str) -> str:
        """Export Environment to JSON format."""
        # Use the model's own method that follows EnvironmentYaml.to_dict() pattern
        env_dict = env.to_yaml_dict()
        return json.dumps(env_dict, indent=2, ensure_ascii=False)


@hookimpl
def conda_environment_exporters():
    """Register the built-in JSON environment exporter."""
    yield CondaEnvironmentExporter(
        name="environment-json",
        handler=JsonEnvironmentExporter,
        default_filenames=["environment.json"],
    )
