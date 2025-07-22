# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Built-in conda JSON environment exporter plugin."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ...common.serialize import json
from ...exceptions import CondaValueError
from ..hookspec import hookimpl
from ..types import CondaEnvironmentExporter, EnvironmentExporter

if TYPE_CHECKING:
    from ...models.environment import Environment


class JsonEnvironmentExporter(EnvironmentExporter):
    """Export Environment to JSON format."""

    format = "json"
    extensions = {".json"}

    def can_handle(
        self, filename: str | None = None, format: str | None = None
    ) -> bool:
        """Check if this exporter can handle the given filename and/or format."""
        if format is not None and format != "json":
            return False
        elif filename is not None and not any(
            filename.lower().endswith(ext) for ext in self.extensions
        ):
            return False
        else:
            return True

    def export(self, env: Environment, format: str) -> str:
        """Export Environment to JSON format."""
        if not self.can_handle(format=format):
            raise CondaValueError(
                f"{self.__class__.__name__} doesn't support format: {format}"
            )

        # Transform Environment model to environment.yaml format (JSON follows same structure)
        env_dict = self._to_environment_yaml_format(env)
        return json.dumps(env_dict, indent=2, ensure_ascii=False)

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


@hookimpl
def conda_environment_exporters():
    """Register the built-in JSON environment exporter."""
    yield CondaEnvironmentExporter(
        name="json",
        handler=JsonEnvironmentExporter,
        default_filenames=["environment.json"],
    )
