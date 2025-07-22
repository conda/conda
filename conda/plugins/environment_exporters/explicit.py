# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Built-in conda explicit environment exporter plugin."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ... import __version__
from ..hookspec import hookimpl
from ..types import CondaEnvironmentExporter

if TYPE_CHECKING:
    from ...models.environment import Environment


def export_explicit(env: Environment) -> str:
    """Export Environment to explicit format."""
    lines = ["# This file may be used to create an environment using:"]
    lines.append(f"# $ conda create --name {env.name} --file <this file>")
    lines.append(f"# platform: {env.platform}")
    lines.append(f"# created-by: conda {__version__}")
    lines.append("@EXPLICIT")
    lines.append("")

    # Add explicit packages if available
    if env.explicit_packages:
        for pkg in env.explicit_packages:
            # Format as full URL or package specification
            if hasattr(pkg, "url") and pkg.url:
                lines.append(pkg.url)
            else:
                # Fallback to name=version=build format
                lines.append(f"{pkg.name}={pkg.version}={pkg.build}")
    elif env.requested_packages:
        # If no explicit packages, use requested packages
        # Note: Converting from requested packages to explicit format
        lines.append("# Note: Converting from requested packages to explicit format")
        for spec in env.requested_packages:
            lines.append(str(spec))

    return "\n".join(lines)


@hookimpl
def conda_environment_exporters():
    """Register the built-in explicit environment exporter."""
    yield CondaEnvironmentExporter(
        name="explicit",
        aliases=(),
        default_filenames=("requirements.txt",),
        export=export_explicit,
    )
