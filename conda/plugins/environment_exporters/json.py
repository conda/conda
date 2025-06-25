# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""JSON environment exporter plugin."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from .. import hookimpl
from ..types import CondaEnvironmentExporter, EnvironmentExporter

if TYPE_CHECKING:
    from ...models.environment import Environment


class JSONExporter(EnvironmentExporter):
    """Exporter for JSON environment format."""

    format = "json"
    extensions = {".json"}

    def can_handle(
        self, filename: str | None = None, format: str | None = None
    ) -> bool:
        """Check if this exporter can handle the given filename and/or format."""
        # Check format if provided
        if format is not None:
            if format != self.format:
                return False

        # Check filename if provided
        if filename is not None:
            if not any(filename.endswith(ext) for ext in self.extensions):
                return False

        # If we get here, all provided criteria matched
        return True

    def export(self, env: Environment, format: str) -> str:
        """Export Environment to JSON format."""
        if not self.can_handle(format=format):
            raise ValueError(
                f"{self.__class__.__name__} doesn't support format: {format}"
            )

        env_dict = env.to_dict()
        return json.dumps(env_dict, indent=2, ensure_ascii=False)


@hookimpl
def conda_environment_exporters():
    yield CondaEnvironmentExporter(
        name="json",
        handler=JSONExporter,
    )
