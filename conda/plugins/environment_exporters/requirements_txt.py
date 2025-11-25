# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Built-in conda requirements environment exporter plugin.

This module implements the requirements format defined in CEP 23:
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


#: The name of the requirements format
REQUIREMENTS_FORMAT: Final = "requirements"


def export_requirements(env: Environment) -> str:
    """Export Environment to requirements format with MatchSpecs (CEP 23 compliant)."""
    lines = ["# This file may be used to create an environment using:"]
    lines.append("# $ conda create --name <env> --file <this file>")
    lines.append(f"# platform: {env.platform}")
    lines.append(f"# created-by: conda {__version__}")

    # Only create requirements files if we have requested packages
    if not env.requested_packages:
        raise CondaValueError(
            "Cannot export requirements format: no requested packages found. "
            "Use 'explicit' format for environments with installed packages, "
            "or ensure the environment has package specifications."
        )

    # Create CEP 23 compliant non-explicit requirements file (no @EXPLICIT)
    lines.append("# Note: This is a conda requirements file (MatchSpec format)")
    lines.append("# Contains conda package specifications, not pip requirements")
    lines.append("")

    for spec in env.requested_packages:
        # Use MatchSpec string representation (CEP 23 compliant)
        lines.append(str(spec))

    return "\n".join(lines)


@hookimpl
def conda_environment_exporters():
    """Environment exporter plugin for requirements format."""
    yield CondaEnvironmentExporter(
        name=REQUIREMENTS_FORMAT,
        aliases=("reqs", "txt"),
        export=export_requirements,
        default_filenames=("requirements.txt", "spec.txt"),
    )
