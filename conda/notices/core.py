# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Core conda notices logic."""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

from ..base.constants import NOTICES_DECORATOR_DISPLAY_INTERVAL_NS, NOTICES_FN
from ..base.context import context
from ..deprecations import deprecated
from .dispatch import NoticeBus

if TYPE_CHECKING:
    from collections.abc import Sequence

    from ..base.context import Context
    from ..models.channel import Channel, MultiChannel
    from .types import ChannelNotice, ChannelNoticeResponse, ChannelNoticeResultSet

# Used below in type hints
ChannelName = str
ChannelUrl = str

logger = logging.getLogger(__name__)


@deprecated("27.3", "27.9", addendum="Use NoticeBus and broadcast helpers directly.")
def retrieve_notices(
    limit: int | None = None,
    always_show_viewed: bool = True,
    silent: bool = False,
    plugin_only: bool = False,
) -> ChannelNoticeResultSet:
    """
    Deprecated: prefer ``NoticeBus`` / ``broadcast_channel_notices()`` /
    ``broadcast_plugin_notices()`` directly.

    Provided as a thin wrapper over the bus path for backward compatibility.
    """
    from ..models.channel import get_channel_objs
    from . import cache
    from .types import ChannelNoticeResultSet

    NoticeBus.clear()
    if not plugin_only:
        broadcast_channel_notices(
            get_channel_name_and_urls(get_channel_objs(context)),
            force=True,
        )
    broadcast_plugin_notices()

    notices = NoticeBus.consume()

    total_number = len(notices)

    viewed_notices = None
    viewed_channel_notices = 0
    if not always_show_viewed:
        cache_file = cache.get_notices_cache_file()
        viewed_notices = cache.get_viewed_channel_notice_ids(cache_file, notices)
        viewed_channel_notices = len(viewed_notices)

    notices = list(filter_notices(notices, limit=limit, exclude=viewed_notices))

    result = ChannelNoticeResultSet(
        channel_notices=notices,
        viewed_channel_notices=viewed_channel_notices,
        total_number_channel_notices=total_number,
    )
    NoticeBus.commit_channel_fetch_interval()
    return result


@deprecated(
    "27.3",
    "27.9",
    addendum="Use show_notices() with notices from NoticeBus.consume().",
)
def display_notices(channel_notice_set: ChannelNoticeResultSet) -> None:
    """
    Deprecated: prefer ``show_notices()`` with notices from
    ``NoticeBus.consume()``.
    """
    from . import cache, views

    views.print_notices(channel_notice_set.channel_notices)

    cache_file = cache.get_notices_cache_file()
    cache.mark_channel_notices_as_viewed(cache_file, channel_notice_set.channel_notices)

    views.print_more_notices_message(
        channel_notice_set.total_number_channel_notices,
        len(channel_notice_set.channel_notices),
        channel_notice_set.viewed_channel_notices,
    )


def broadcast_channel_notices(
    url_and_names: list[tuple[ChannelUrl, ChannelName]],
    *,
    silent: bool = True,
    force: bool = False,
) -> None:
    """Fetch notices.json for each (name, url) and broadcast to the bus.

    When ``force`` is False (repodata side effect), gated on
    ``is_channel_notices_enabled`` (configured + not ``--json``), the
    channel-notice fetch interval, and at most one attempt per command.
    Pass ``force=True`` for explicit ``conda notices`` invocations (still
    requires ``channel_notices_configured``).

    Args:
        url_and_names: Sequence of ``(url, channel_name)`` tuples.
        silent: Whether to suppress the spinner during fetch (default ``True``).
        force: Bypass JSON / fetch-interval gates (default ``False``).
    """
    if force:
        if not channel_notices_configured(context):
            return
        NoticeBus.mark_channel_fetch()
    else:
        if not is_channel_notices_enabled(context):
            return
        if not is_channel_notices_cache_expired():
            return
        # Claim before I/O so concurrent RepodataFetch callers (one per subdir)
        # do not each hit notices.json.
        if not NoticeBus.try_begin_channel_fetch():
            return

    from . import fetch

    for response in fetch.get_notice_responses(url_and_names, silent=silent):
        for notice in response.notices:
            NoticeBus.broadcast(notice)


def broadcast_plugin_notices() -> None:
    """Collect notices from plugin hook implementations and broadcast to the bus."""
    from datetime import datetime, timezone

    from .types import ChannelNotice

    for conda_notice in context.plugin_manager.get_notices():
        source = getattr(getattr(conda_notice, "impl", None), "plugin_name", None)
        if not source:
            source = "unknown"

        notice_id = f"plugin:{source}:{conda_notice.name}"

        NoticeBus.broadcast(
            ChannelNotice(
                id=notice_id,
                channel_name=source,
                message=conda_notice.message,
                level=conda_notice.level,
                created_at=conda_notice.created_at or datetime.now(timezone.utc),
                expired_at=conda_notice.expired_at,
                interval=None,
            )
        )


def show_notices(
    notices: Sequence[ChannelNotice],
    *,
    limit: int | None = None,
    always_show_viewed: bool = False,
) -> None:
    """Render notices from the bus and persist viewed state."""
    if not notices:
        return

    from . import cache, views

    cache_file = cache.get_notices_cache_file()

    channel = [n for n in notices if not n.id.startswith("plugin:")]
    plugin = [n for n in notices if n.id.startswith("plugin:")]

    total_channel = len(channel)

    viewed_ids: set[str] | None = None
    viewed_count = 0
    if not always_show_viewed:
        viewed_ids = cache.get_viewed_channel_notice_ids(cache_file, channel)
        viewed_count = len(viewed_ids)
        channel = [n for n in channel if n.id not in viewed_ids]

    if limit is not None:
        channel = channel[:limit]

    combined = [*plugin, *channel]

    views.print_notices(combined)
    cache.mark_channel_notices_as_viewed(cache_file, combined)
    views.print_more_notices_message(
        total_channel,
        len(channel),
        viewed_count,
    )


def run_notices_sandwich(func):
    """Run a nullary callable within the notices pub/sub lifecycle.

    Plugin notices are broadcast first.  ``func`` runs next (during which
    channel notices may be broadcast via ``RepodataFetch``).  Accumulated
    notices are displayed afterward and the channel fetch interval is
    committed when any channel fetch ran.

    This ordering addresses https://github.com/conda/conda/issues/11847.
    """
    NoticeBus._channel_fetches_this_command = False
    broadcast_plugin_notices()

    try:
        # Load display deps before the command: upgrading/downgrading base
        # python rewrites site-packages under the running interpreter, so
        # show_notices() must not be the first import of views.
        # see https://github.com/conda/conda/issues/16126
        from . import cache, views  # noqa: F401

        result = func()

        notices = NoticeBus.consume()
        if notices_display_enabled(context):
            show_notices(notices, limit=context.number_channel_notices)

        NoticeBus.commit_channel_fetch_interval()
        return result

    except Exception:
        # Skip interval commit on failure (flag reset). Do not clear viewed-ID
        # / response caches: do_call wraps every subcommand, so wiping them
        # here would re-show notices after routine command failures.
        NoticeBus._channel_fetches_this_command = False
        raise


@deprecated(
    "27.3",
    "27.9",
    addendum="do_call() wraps all CLI subcommands in run_notices_sandwich(); "
    "the decorator is a no-op.",
)
def notices(func):
    """Legacy decorator retained for compatibility; ``do_call()`` wraps subcommands."""
    return func


def get_channel_name_and_urls(
    channels: Sequence[Channel | MultiChannel],
) -> list[tuple[ChannelUrl, ChannelName]]:
    """
    Return a sequence of Channel URL and name tuples.

    This function handles both Channel and MultiChannel object types.
    """
    channel_name_and_urls = []

    for channel in channels:
        name = channel.name or channel.location

        for url in channel.base_urls:
            full_url = url.rstrip("/")
            channel_name_and_urls.append((f"{full_url}/{NOTICES_FN}", name))

    return channel_name_and_urls


def flatten_notice_responses(
    channel_notice_responses: Sequence[ChannelNoticeResponse],
) -> Sequence[ChannelNotice]:
    return tuple(
        notice
        for channel in channel_notice_responses
        if channel.notices
        for notice in channel.notices
    )


def filter_notices(
    channel_notices: Sequence[ChannelNotice],
    limit: int | None = None,
    exclude: set[str] | None = None,
) -> Sequence[ChannelNotice]:
    """Perform filtering actions for the provided sequence of ChannelNotice objects."""
    if exclude:
        channel_notices = tuple(
            channel_notice
            for channel_notice in channel_notices
            if channel_notice.id not in exclude
        )

    if limit is not None:
        channel_notices = channel_notices[:limit]

    return channel_notices


def channel_notices_configured(ctx: Context) -> bool:
    """Whether channel-notice fetching is configured (count > 0, not offline).

    Used by explicit ``conda notices`` (``force=True``) and as the base for
    automatic enablement. Does not consider ``--json``.
    """
    return ctx.number_channel_notices > 0 and not ctx.offline


def is_channel_notices_enabled(ctx: Context) -> bool:
    """Whether automatic channel-notice fetch should run for a CLI command.

    Requires :func:`channel_notices_configured` and non-JSON output.
    """
    return channel_notices_configured(ctx) and notices_display_enabled(ctx)


def notices_display_enabled(ctx: Context) -> bool:
    """Whether notice text should be printed (suppressed under ``--json``)."""
    return not ctx.json


def is_channel_notices_cache_expired() -> bool:
    """
    Return whether the channel-notice fetch interval has elapsed.

    Uses the mtime of ``notices.cache``.  Anything older than
    ``NOTICES_DECORATOR_DISPLAY_INTERVAL_NS`` is considered expired.
    """
    from . import cache

    cache_file = cache.get_notices_cache_file()

    cache_file_stat = cache_file.stat()
    now = time.time_ns()
    ns_since_checked = now - cache_file_stat.st_mtime_ns

    return ns_since_checked >= NOTICES_DECORATOR_DISPLAY_INTERVAL_NS
