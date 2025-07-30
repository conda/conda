# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Built-in conda specs environment exporter plugin.

This module implements the specs format defined in CEP 23:
Files with MatchSpec strings (no @EXPLICIT marker) for flexible package specifications.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ... import __version__
from ...exceptions import CondaValueError
from ..hookspec import hookimpl
from ..types import CondaEnvironmentExporter

if TYPE_CHECKING:
    from typing import Final

    from ...models.environment import Environment


#: The name of the specs format
SPECS_FORMAT: Final = "specs"


def export_specs(env: Environment) -> str:
    """Export Environment to specs file with MatchSpecs (CEP 23 compliant)."""
    lines = ["# This file may be used to create an environment using:"]
    lines.append("# $ conda create --name <env> --file <this file>")
    lines.append(f"# platform: {env.platform}")
    lines.append(f"# created-by: conda {__version__}")

    # Only create specs file if we have requested packages
    if not env.requested_packages:
        raise CondaValueError(
            "Cannot export specs format: no requested packages found. "
            "Use 'explicit' format for environments with installed packages, "
            "or ensure the environment has package specifications."
        )

    # Create CEP 23 compliant non-explicit specs file (no @EXPLICIT)
    lines.append("# Note: This is a conda specs file (MatchSpec format)")
    lines.append("# Contains conda package specifications, not pip requirements")
    lines.append("")

    for spec in env.requested_packages:
        # Use MatchSpec string representation (CEP 23 compliant)
        lines.append(str(spec))

    return "\n".join(lines)


@hookimpl
def conda_environment_exporters():
    """Environment exporter plugin for specs format."""
    yield CondaEnvironmentExporter(
        name=SPECS_FORMAT,
        aliases=("txt",),
        export=export_specs,
        default_filenames=("specs.txt",),
    )
