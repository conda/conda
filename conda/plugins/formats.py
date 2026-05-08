# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Snapshot of registered format plugins for CLI help rendering."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..common.io import dashlist

if TYPE_CHECKING:
    from collections.abc import Iterable

    from .types import (
        CondaEnvironmentExporter,
        CondaEnvironmentSpecifier,
        EnvironmentFormat,
    )

    FormatPlugin = CondaEnvironmentExporter | CondaEnvironmentSpecifier


class FormatSummary:
    """Snapshot of registered format plugins, used to render CLI help.

    Plugins are grouped by :attr:`environment_format` once on construction
    so that repeated queries (e.g. several ``example_filename`` calls with
    different categories) don't re-scan the list.
    """

    __slots__ = ("by_category",)

    def __init__(
        self,
        plugins: Iterable[FormatPlugin],
    ) -> None:
        self.by_category: dict[EnvironmentFormat, list[FormatPlugin]] = {}
        for plugin in plugins:
            self.by_category.setdefault(plugin.environment_format, []).append(plugin)

    def __bool__(self) -> bool:
        return bool(self.by_category)

    def __len__(self) -> int:
        return sum(len(plugins) for plugins in self.by_category.values())

    def __repr__(self) -> str:
        categories = ", ".join(
            f"{category.label}: {len(plugins)}"
            for category, plugins in self.by_category.items()
        )
        return f"FormatSummary({categories})"

    def describe(self, heading: str | None = None) -> str:
        """Render a grouped, bulleted listing for an argparse epilog.

        Each category uses its :attr:`EnvironmentFormat.label` as a section
        header. Entries show ``name (alias, ...)`` when aliases exist.

        When *heading* is given it appears as the first section. Returns
        an empty string when no plugins were provided.
        """
        sections = []
        for category, plugins in self.by_category.items():
            entries = []
            for plugin in plugins:
                parts = [plugin.name]
                if plugin.aliases:
                    parts.append(f"(aliases: {', '.join(plugin.aliases)})")
                if plugin.default_filenames:
                    parts.append(f": {', '.join(plugin.default_filenames)}")
                entries.append(" ".join(parts))
            sections.append(f"{category.label}:{dashlist(entries)}")

        return "\n\n".join(
            [f"{heading}:", *sections] if heading and sections else sections
        )

    def example_filename(
        self,
        environment_format: EnvironmentFormat,
        *,
        require_multiplatform: bool = False,
    ) -> str | None:
        """Pick an example filename for *environment_format*.

        Returns the first ``default_filenames`` entry from the first
        matching plugin. *require_multiplatform* restricts to exporters
        that declare ``multiplatform_export``.
        """
        candidates = list(self.by_category.get(environment_format, ()))
        if not candidates:
            return None

        if require_multiplatform:
            candidates = [
                plugin
                for plugin in candidates
                if getattr(plugin, "multiplatform_export", None)
            ]

        for plugin in candidates:
            if plugin.default_filenames:
                return plugin.default_filenames[0]

        return None
