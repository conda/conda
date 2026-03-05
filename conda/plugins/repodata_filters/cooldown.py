# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Repodata filter plugin that excludes packages newer than a cooldown threshold."""

from __future__ import annotations

from logging import getLogger
from time import time
from typing import TYPE_CHECKING

from .. import hookimpl

if TYPE_CHECKING:
    from typing import Any
from ..types import CondaRepodataFilter

log = getLogger(__name__)

# Year 9999 in seconds — any timestamp above this must be in milliseconds
_MAX_SECONDS_TIMESTAMP = 253402300799


def _cooldown_filter(filename: str, info: dict[str, Any]) -> bool:
    from ...base.context import context

    cooldown = context.cooldown
    if not cooldown:
        return True

    if info["name"] in frozenset(context.cooldown_exclude):
        return True

    timestamp = info.get("upload_timestamp") or info.get("timestamp", 0)
    if not timestamp:
        return True

    if timestamp > _MAX_SECONDS_TIMESTAMP:
        timestamp /= 1000

    cutoff = time() - cooldown
    if timestamp > cutoff:
        log.debug(
            "Cooldown: excluding %s (%.1f days old, cooldown is %.1f days)",
            filename,
            (time() - timestamp) / 86400,
            cooldown / 86400,
        )
        return False

    return True


def _cache_key():
    from ...base.context import context

    return context.cooldown


@hookimpl
def conda_repodata_filters():
    yield CondaRepodataFilter(
        name="cooldown",
        filter=_cooldown_filter,
        cache_key=_cache_key,
    )
