# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Repodata filter plugin that excludes packages newer than a configured threshold."""

from __future__ import annotations

from functools import lru_cache
from logging import getLogger
from time import time
from typing import TYPE_CHECKING

from ...cli.helpers import parse_duration_to_seconds
from .. import hookimpl
from ..types import CondaRepodataFilter

if TYPE_CHECKING:
    from typing import Any

log = getLogger(__name__)

# Year 9999 in seconds — any timestamp above this must be in milliseconds
_MAX_SECONDS_TIMESTAMP = 253402300799


class ExcludeNewerFilter:
    """Repodata filter that excludes packages newer than a configured threshold.

    Reads ``context.exclude_newer`` (a duration or timestamp string) and
    ``context.exclude_newer_package`` (per-package overrides) to decide
    whether each package record should be kept or excluded.

    Config parsing is cached via ``resolve()`` so it only runs when the
    config values actually change.
    """

    def __init__(self):
        self._key: tuple = ()

    @staticmethod
    @lru_cache(maxsize=1)
    def resolve(config_key: tuple) -> tuple[int, dict[str, int | None]]:
        """Resolve raw config into (default_seconds, per_package_overrides)."""
        raw_threshold, raw_overrides = config_key[0], config_key[1:]

        if isinstance(raw_threshold, str) and raw_threshold:
            threshold = parse_duration_to_seconds(raw_threshold)
        else:
            threshold = int(raw_threshold) if raw_threshold else 0

        overrides: dict[str, int | None] = {}
        for pkg_name, value in raw_overrides:
            if value is False or (isinstance(value, str) and value.lower() == "false"):
                overrides[pkg_name] = None
            elif isinstance(value, (int, float)):
                overrides[pkg_name] = int(value)
            else:
                overrides[pkg_name] = parse_duration_to_seconds(str(value))

        return threshold, overrides

    def __call__(self, filename: str, info: dict[str, Any]) -> bool:
        from ...base.context import context

        exclude_newer = context.exclude_newer
        if not exclude_newer:
            return True

        key = (exclude_newer, *sorted(context.exclude_newer_package.items()))
        if key != self._key:
            self._key = key

        threshold, overrides = self.resolve(self._key)

        pkg_name = info["name"]
        if pkg_name in overrides:
            override = overrides[pkg_name]
            if override is None:
                return True
            threshold = override

        timestamp = info.get("indexed_timestamp") or info.get("timestamp", 0)
        if not timestamp:
            return True

        if timestamp > _MAX_SECONDS_TIMESTAMP:
            timestamp /= 1000

        cutoff = time() - threshold
        if timestamp > cutoff:
            log.debug(
                "exclude-newer: excluding %s (%.1f days old, threshold is %.1f days)",
                filename,
                (time() - timestamp) / 86400,
                threshold / 86400,
            )
            return False

        return True


exclude_newer_filter = ExcludeNewerFilter()


@hookimpl
def conda_repodata_filters():
    from ...base.context import context

    yield CondaRepodataFilter(
        name="exclude-newer",
        filter=exclude_newer_filter,
        cache_key=lambda: (
            context.exclude_newer,
            *sorted(context.exclude_newer_package.items()),
        ),
    )
