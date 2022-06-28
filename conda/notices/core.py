# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from functools import wraps
from typing import Sequence, Tuple, Optional, Set
from urllib import parse

from ..base.context import context, Context
from ..base.constants import NOTICES_FN
from ..models.channel import Channel, get_channel_objs

from . import cache
from . import views
from . import http
from .types import ChannelNotice, ChannelNoticeResponse

# Used below in type hints
ChannelName = str
ChannelUrl = str


def display_notices(
    limit: Optional[int] = None,
    always_show_viewed: bool = True,
    silent: bool = False,
) -> None:
    """
    Entry point for displaying notices. This is called by the "notices" decorator as well
    as the sub-command "notices"

    Args:
        limit: Limit the number of notices to show (defaults to None).
        always_show_viewed: Whether all notices should be shown, not only the unread ones
                            (defaults to True).
        silent: Whether to use a spinner when fetching and caching notices.
    """
    channel_name_urls = get_channel_name_and_urls(get_channel_objs(context))
    channel_notice_responses = http.get_notice_responses(channel_name_urls, silent=silent)
    channel_notices = flatten_notice_responses(channel_notice_responses)
    num_total_notices = len(channel_notices)

    cache_file = cache.get_notices_cache_file()
    viewed_notices = None
    num_viewed_notices = 0
    if not always_show_viewed:
        viewed_notices = cache.get_viewed_channel_notice_ids(cache_file, channel_notices)
        num_viewed_notices = len(viewed_notices)

    channel_notices = filter_notices(channel_notices, limit=limit, exclude=viewed_notices)
    if len(channel_notices) == 0:
        return

    views.print_notices(channel_notices)

    # Updates cache database, marking displayed notices as "viewed"
    cache.mark_channel_notices_as_viewed(cache_file, channel_notices)

    views.print_more_notices_message(num_total_notices, len(channel_notices), num_viewed_notices)


def notices(func):
    """
    Wrapper for "execute" entry points for subcommands.

    Args:
        func: Function to be decorated
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        return_value = func(*args, **kwargs)

        if is_channel_notices_enabled(context):
            display_notices(
                limit=context.number_channel_notices,
                always_show_viewed=False,
                silent=True,
            )

        return return_value

    return wrapper


def get_channel_name_and_urls(
    channels: [Sequence[Channel]],
) -> Sequence[Tuple[ChannelUrl, ChannelName]]:
    """Return a sequence of Channel URL and name"""

    def ensure_endswith(value: str, ends: str) -> str:
        return value if value.endswith(ends) else f"{value}{ends}"

    def join_url(value: str, join_val: str) -> str:
        return parse.urljoin(ensure_endswith(value, "/"), join_val)

    return tuple(
        (join_url(base_url, NOTICES_FN), channel.name or channel.location)
        for channel in channels
        for base_url in channel.base_urls
    )


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
    limit: Optional[int] = None,
    exclude: Optional[Set[str]] = None,
) -> Sequence[ChannelNotice]:
    """
    Perform filtering actions for the provided sequence of ChannelNotice objects.
    """
    if exclude:
        channel_notices = tuple(
            channel_notice
            for channel_notice in channel_notices
            if channel_notice.id not in exclude
        )

    if limit is not None:
        channel_notices = channel_notices[:limit]

    return channel_notices


def is_channel_notices_enabled(ctx: Context) -> bool:
    """
    Determines whether channel notices should be displayed for `notices` decorator.

    This only happens when offline is False and number_channel_notices is greater
    than 0.

    Args:
        ctx: The conda context object
    """
    return ctx.number_channel_notices > 0 and not ctx.offline and not ctx.json
