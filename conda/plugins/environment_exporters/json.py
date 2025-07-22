# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Built-in conda JSON environment exporter plugin."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ...common.serialize import json
from ...exceptions import CondaValueError
from ..hookspec import hookimpl
from ..types import CondaEnvironmentExporter

if TYPE_CHECKING:
    from ...models.environment import Environment


def export_json(env: Environment) -> str:
    """Export Environment to JSON format."""
    # Use the model's own method that follows EnvironmentYaml.to_dict() pattern
    env_dict = env.to_yaml_dict()
    try:
        return json.dumps(env_dict, indent=2, ensure_ascii=False)
    except (TypeError, ValueError, RecursionError) as e:
        raise CondaValueError(f"Failed to export environment to JSON: {e}") from e


@hookimpl
def conda_environment_exporters():
    """Register the built-in JSON environment exporter."""
    yield CondaEnvironmentExporter(
        name="environment-json",
        aliases=("json",),
        default_filenames=("environment.json",),
        export=export_json,
    )
