# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Helpers for rendering CLI help text."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..common.io import dashlist
from ..plugins.types import EnvironmentFormat

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from ..plugins.types import (
        CondaEnvironmentExporter,
        CondaPluginWithEnvironmentFormat,
    )


def get_available_environment_formats(
    formats: Mapping[EnvironmentFormat, Sequence[CondaPluginWithEnvironmentFormat]],
    *,
    indent: int = 0,
) -> str:
    """Render epilog text for grouped environment format plugins.

    Each plugin is one bullet line: ``NAME``, ``NAME (aliases: ...)``,
    ``NAME: FILENAME, ...``, or combined aliases plus filenames.
    """
    if not formats:
        return ""

    sections = []
    for category, plugins in formats.items():
        entries = []
        for plugin in plugins:
            line = plugin.name
            if plugin.aliases:
                line = f"{line} (aliases: {', '.join(plugin.aliases)})"
            if plugin.default_filenames:
                line = f"{line}: {', '.join(plugin.default_filenames)}"
            entries.append(line)
        sections.append(
            f"{' ' * indent}{category.label}:{dashlist(entries, indent=indent + 2)}"
        )
    return "\n\n".join(sections)


def get_multiplatform_lockfile(
    formats: Mapping[EnvironmentFormat, Sequence[CondaEnvironmentExporter]],
) -> str | None:
    """Return first ``default_filenames`` from the first multiplatform lockfile."""
    return next(
        (
            exporter.default_filenames[0]
            for exporter in formats.get(EnvironmentFormat.lockfile, ())
            if exporter.multiplatform_export and exporter.default_filenames
        ),
        None,
    )
