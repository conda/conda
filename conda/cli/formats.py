# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Helpers for rendering environment format plugin listings in CLI help.

Obtain the *by_category* mapping from
``CondaPluginManager.get_environment_exporter_format_mapping()`` or
``get_environment_specifier_format_mapping()`` (same grouping the manager
uses elsewhere).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..common.io import dashlist

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from ..plugins.types import CondaEnvironmentFormatPlugin, EnvironmentFormat


def describe_environment_formats(
    by_category: Mapping[EnvironmentFormat, Sequence[CondaEnvironmentFormatPlugin]],
    indent: int = 2,
) -> str:
    """Render epilog text for grouped environment format plugins.

    *by_category* is the ``EnvironmentFormat`` → plugins mapping from
    ``get_environment_exporter_format_mapping()`` or
    ``get_environment_specifier_format_mapping()``.
    Each category uses its :attr:`EnvironmentFormat.label` as a section
    header.

    Each plugin is rendered as a single line:

    .. code-block:: text
      - NAME
      - NAME (aliases: ...)
      - NAME: FILENAME, ...
      - NAME (aliases: ...): FILENAME, ...
    """
    if not by_category:
        return ""

    sections = []
    for category, plugins in by_category.items():
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
