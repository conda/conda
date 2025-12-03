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
    from typing import Final

    from ...models.environment import Environment


#: The name of the explicit format
EXPLICIT_FORMAT: Final = "explicit"


def export_explicit(env: Environment) -> str:
    """Export Environment to explicit format with @EXPLICIT and URLs (CEP 23 compliant)."""
    lines = ["# This file may be used to create an environment using:"]
    lines.append("# $ conda create --name <env> --file <this file>")
    lines.append(f"# platform: {env.platform}")
    lines.append(f"# created-by: conda {__version__}")

    # Only create true explicit files if we have explicit packages with URLs
    if not env.explicit_packages:
        raise CondaValueError(
            "Cannot export explicit format: no explicit packages with installation metadata found. "
            "Use 'requirements' format for environments with only requested packages, "
            "or ensure the environment has been solved and installed."
        )
    # Error if external packages (pip) are present - explicit format can't represent them
    elif env.external_packages:
        raise CondaValueError(
            "Cannot export explicit format: environment contains external packages that cannot be represented in explicit format. "
            "Use a different format to include external packages."
        )
    # Error if requested packages exist but aren't fully represented in explicit packages
    elif env.requested_packages:
        explicit_names = {pkg.name for pkg in env.explicit_packages}
        requested_names = {pkg.name for pkg in env.requested_packages}
        missing_explicit = requested_names - explicit_names
        if missing_explicit:
            raise CondaValueError(
                f"Cannot export explicit format: some requested packages lack installation metadata: "
                f"{', '.join(sorted(missing_explicit))}. "
                "Use 'requirements' format or ensure all packages are properly installed."
            )

    # Create CEP 23 compliant explicit file with @EXPLICIT and URLs
    lines.append("@EXPLICIT")

    for pkg in env.explicit_packages:
        # Use existing URL or construct from channel metadata
        url = getattr(pkg, "url", None)
        if (
            not url
            and (channel := getattr(pkg, "channel", None))
            and (base_url := getattr(channel, "base_url", None))
            and (subdir := getattr(pkg, "subdir", None))
            and (fn := getattr(pkg, "fn", None))
        ):
            url = join_url(base_url, subdir, fn)

        if url:
            lines.append(url)
        else:
            raise CondaValueError(
                f"Cannot export '{pkg.name}': explicit format requires package URLs"
            )

    return "\n".join(lines)


@hookimpl
def conda_environment_exporters():
    """Environment exporter plugin for explicit format."""
    yield CondaEnvironmentExporter(
        name=EXPLICIT_FORMAT,
        aliases=(),
        export=export_explicit,
        default_filenames=("explicit.txt",),
    )
