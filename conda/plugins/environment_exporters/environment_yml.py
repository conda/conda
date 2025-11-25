# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Built-in conda standard environment exporter plugins (YAML and JSON)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from ruamel.yaml.error import YAMLError

from ...common.serialize import json, yaml_safe_dump
from ...exceptions import CondaValueError
from ..hookspec import hookimpl
from ..types import CondaEnvironmentExporter

if TYPE_CHECKING:
    from typing import Any, Final

    from ...models.environment import Environment

#: The name of the environment-json format
ENVIRONMENT_JSON_FORMAT: Final = "environment-json"

#: The name of the environment-yaml format
ENVIRONMENT_YAML_FORMAT: Final = "environment-yaml"

#: Type alias for format validation
EnvironmentFormatType = Literal["environment-json", "environment-yaml"]


def to_dict(env: Environment) -> dict[str, Any]:
    """
    Convert Environment to standard dictionary format used by YAML and JSON exporters.

    This represents the common dictionary structure that both YAML and JSON
    environment formats use.

    :param env: Environment model to convert
    :return: Dictionary with standard environment fields
    """
    env_dict = {"name": env.name}

    # Add channels if present
    if env.config and env.config.channels:
        env_dict["channels"] = list(env.config.channels)

    # Convert requested_packages to dependencies list
    if env.requested_packages:
        dependencies = []
        for item in env.requested_packages:
            if isinstance(item, dict):
                # Handle pip dependencies (dict format: {"pip": [...]})
                dependencies.append(item)
            else:
                # Handle conda packages (MatchSpec objects)
                # Use the conda_env_form() method for proper conda env export format
                dependencies.append(item.conda_env_form())

        # Add external packages (e.g. Python packages) if present
        if env.external_packages:
            dependencies.append(env.external_packages)

        env_dict["dependencies"] = dependencies
    elif env.explicit_packages:
        # Fall back to explicit packages if no requested packages
        env_dict["dependencies"] = [
            explicit_package.spec for explicit_package in env.explicit_packages
        ]

    # Add variables if present
    if env.variables:
        env_dict["variables"] = env.variables

    # Add prefix if present (though this is less common in standard formats)
    if env.prefix:
        env_dict["prefix"] = env.prefix

    return env_dict


def export_yaml(env: Environment) -> str:
    """Export Environment to YAML format."""
    env_dict = to_dict(env)
    try:
        return yaml_safe_dump(env_dict)
    except YAMLError as e:
        raise CondaValueError(f"Failed to export environment to YAML: {e}")


def export_json(env: Environment) -> str:
    """Export Environment to JSON format."""
    env_dict = to_dict(env)
    try:
        return json.dumps(env_dict, indent=2, ensure_ascii=False)
    except (TypeError, ValueError, RecursionError) as e:
        raise CondaValueError(f"Failed to export environment to JSON: {e}")


@hookimpl(tryfirst=True)  # Ensure built-in YAML exporter loads first and has priority
def conda_environment_exporters():
    """Register the built-in YAML and JSON environment exporters."""
    yield CondaEnvironmentExporter(
        name=ENVIRONMENT_YAML_FORMAT,
        aliases=("yaml", "yml"),
        default_filenames=("environment.yaml", "environment.yml"),
        export=export_yaml,
    )

    yield CondaEnvironmentExporter(
        name=ENVIRONMENT_JSON_FORMAT,
        aliases=("json",),
        default_filenames=("environment.json",),
        export=export_json,
    )
