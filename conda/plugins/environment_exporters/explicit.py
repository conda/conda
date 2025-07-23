# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Built-in conda explicit environment exporter plugin.

This module implements the explicit format defined in CEP 23:
Files with @EXPLICIT marker and package URLs for reproducible installs.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ... import __version__
from ...common.url import join_url
from ...exceptions import CondaValueError
from ..hookspec import hookimpl
from ..types import CondaEnvironmentExporter

if TYPE_CHECKING:
    from ...models.environment import Environment


def export_explicit(env: Environment) -> str:
    """Export Environment to explicit format with @EXPLICIT and URLs (CEP 23 compliant)."""
    lines = ["# This file may be used to create an environment using:"]
    lines.append(f"# $ conda create --name {env.name or '<env>'} --file <this file>")
    lines.append(f"# platform: {env.platform}")
    lines.append(f"# created-by: conda {__version__}")

    # Only create true explicit files if we have explicit packages with URLs
    if not env.explicit_packages:
        raise CondaValueError(
            "Cannot export explicit format: no explicit packages with installation metadata found. "
            "Use 'requirements' format for environments with only requested packages, "
            "or ensure the environment has been solved and installed."
        )

    # Create CEP 23 compliant explicit file with @EXPLICIT and URLs
    lines.append("@EXPLICIT")
    lines.append("")

    for pkg in env.explicit_packages:
        # Format as full URL or construct URL from package metadata
        if hasattr(pkg, "url") and pkg.url:
            lines.append(pkg.url)
        elif hasattr(pkg, "channel") and hasattr(pkg, "fn"):
            # Construct URL from channel and filename
            base_url = getattr(pkg.channel, "base_url", None) if pkg.channel else None
            if base_url and hasattr(pkg, "subdir"):
                url = join_url(base_url, pkg.subdir, pkg.fn)
                lines.append(url)
            else:
                # Fallback to name=version=build format for explicit files
                spec_line = f"{pkg.name}={pkg.version}={pkg.build}"
                lines.append(spec_line)
        else:
            # Fallback to name=version=build format
            spec_line = f"{pkg.name}={pkg.version}={pkg.build}"
            lines.append(spec_line)

    return "\n".join(lines)


@hookimpl
def conda_environment_exporters():
    """Environment exporter plugin for explicit format."""
    yield CondaEnvironmentExporter(
        name="explicit",
        aliases=(),
        export=export_explicit,
        default_filenames=("explicit.txt",),
    )
