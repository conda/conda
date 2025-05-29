# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""JSON environment exporter plugin."""

import json
from typing import TYPE_CHECKING

from .. import hookimpl
from ..types import CondaEnvironmentExporter, EnvironmentExporter

if TYPE_CHECKING:
    from ...env.env import Environment


class JSONExporter(EnvironmentExporter):
    """Exporter for JSON environment format."""

    format = "json"
    extensions = {".json"}

    def export(self, env: "Environment", format: str) -> str:
        """Export Environment to JSON format."""
        self.validate(format)

        # Convert environment to dictionary and serialize as JSON
        env_dict = env.to_dict()
        return json.dumps(env_dict, indent=2, ensure_ascii=False)


@hookimpl
def conda_environment_exporters():
    yield CondaEnvironmentExporter(
        name="json",
        handler=JSONExporter,
    )
