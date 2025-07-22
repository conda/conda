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

    format = "yaml"
    extensions = {".yaml", ".yml"}

    def can_handle(
        self, filename: str | None = None, format: str | None = None
    ) -> bool:
        """Check if this exporter can handle the given filename and/or format."""
        # Check format if provided
        if format is not None and format not in ("yaml", "yml"):
            return False

        # Check filename if provided
        elif filename is not None and not any(
            filename.lower().endswith(ext) for ext in self.extensions
        ):
            return False
        else:
            return True

    def export(self, env: Environment, format: str) -> str:
        """Export Environment to YAML format."""
        if not self.can_handle(format=format):
            raise CondaValueError(
                f"{self.__class__.__name__} doesn't support format: {format}"
            )

        from ...common.serialize import yaml_safe_dump

        # Transform Environment model to environment.yaml format
        env_dict = self._to_environment_yaml_format(env)
        yaml_content = yaml_safe_dump(env_dict)
        if yaml_content is None:
            raise CondaValueError("Failed to export environment to YAML")
        return yaml_content

    def _to_environment_yaml_format(self, env: Environment) -> dict:
        """Transform Environment model to environment.yaml format."""
        env_dict = {"name": env.name}

        # Add channels if present
        if env.config and env.config.channels:
            env_dict["channels"] = list(env.config.channels)

        # Convert requested_packages to dependencies list
        if env.requested_packages:
            env_dict["dependencies"] = [str(spec) for spec in env.requested_packages]
        elif env.explicit_packages:
            # Fall back to explicit packages if no requested packages
            env_dict["dependencies"] = [
                f"{pkg.name}={pkg.version}={pkg.build}" for pkg in env.explicit_packages
            ]

        # Add variables if present
        if env.variables:
            env_dict["variables"] = env.variables

        # Add prefix if present (though this is less common in environment.yaml)
        if env.prefix:
            env_dict["prefix"] = env.prefix

        return env_dict


@hookimpl(tryfirst=True)  # Ensure built-in YAML exporter loads first and has priority
def conda_environment_exporters():
    """Register the built-in YAML environment exporter."""
    yield CondaEnvironmentExporter(
        name="yaml",
        handler=YamlEnvironmentExporter,
        default_filenames=["environment.yaml", "environment.yml"],
    )
