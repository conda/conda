# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from functools import wraps
import time
from typing import Sequence, Optional, Union
from urllib import parse

from ..base.context import context, Context
from ..base.constants import NOTICES_FN, NOTICES_DECORATOR_DISPLAY_INTERVAL
from ..models.channel import Channel, MultiChannel, get_channel_objs

from . import cache
from . import views
from . import fetch
from .types import ChannelNotice, ChannelNoticeResponse, ChannelNoticeResultSet

# Used below in type hints
ChannelName = str
ChannelUrl = str


def retrieve_notices(
    limit: Optional[int] = None,
    always_show_viewed: bool = True,
    silent: bool = False,
) -> ChannelNoticeResultSet:
    """
    Function used for retrieving notices. This is called by the "notices" decorator as well
    as the sub-command "notices"

    Args:
        limit: Limit the number of notices to show (defaults to None).
        always_show_viewed: Whether all notices should be shown, not only the unread ones
                            (defaults to True).
        silent: Whether to use a spinner when fetching and caching notices.
    """
    channel_name_urls = get_channel_name_and_urls(get_channel_objs(context))
    channel_notice_responses = fetch.get_notice_responses(channel_name_urls, silent=silent)
    channel_notices = flatten_notice_responses(channel_notice_responses)
    num_total_notices = len(channel_notices)

    cache_file = cache.get_notices_cache_file()

    # We always want to modify the mtime attribute of the file if we are trying to retrieve notices
    # This is used later in "is_channel_notices_cache_expired"
    cache_file.touch()

    viewed_notices = None
    num_viewed_notices = 0
    if not always_show_viewed:
        viewed_notices = cache.get_viewed_channel_notice_ids(cache_file, channel_notices)
        num_viewed_notices = len(viewed_notices)

    channel_notices = filter_notices(channel_notices, limit=limit, exclude=viewed_notices)

    return ChannelNoticeResultSet(
        channel_notices=channel_notices,
        viewed_channel_notices=num_viewed_notices,
        total_number_channel_notices=num_total_notices,
    )


def display_notices(channel_notice_set: ChannelNoticeResultSet) -> None:
    """
    Prints the channel notices to std out
    """
    views.print_notices(channel_notice_set.channel_notices)

    # Updates cache database, marking displayed notices as "viewed"
    cache_file = cache.get_notices_cache_file()
    cache.mark_channel_notices_as_viewed(cache_file, channel_notice_set.channel_notices)

    views.print_more_notices_message(
        channel_notice_set.total_number_channel_notices,
        len(channel_notice_set.channel_notices),
        channel_notice_set.viewed_channel_notices,
    )


def notices(func):
    """
    Wrapper for "execute" entry points for subcommands.

    Args:
        func: Function to be decorated
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        if is_channel_notices_enabled(context) and is_channel_notices_cache_expired():
            channel_notice_set = retrieve_notices(
                limit=context.number_channel_notices,
                always_show_viewed=False,
                silent=True,
            )
            return_value = func(*args, **kwargs)
            display_notices(channel_notice_set)

            return return_value

        else:
            return func(*args, **kwargs)

    return wrapper


def get_channel_name_and_urls(
    channels: Sequence[Union[Channel, MultiChannel]],
) -> Sequence[tuple[ChannelUrl, ChannelName]]:
    """Return a sequence of Channel URL and name"""

    def ensure_endswith(value: str, ends: str) -> str:
        return value if value.endswith(ends) else f"{value}{ends}"

    def join_url(value: str, join_val: str) -> str:
        return parse.urljoin(ensure_endswith(value, "/"), join_val)

    channel_name_and_urls = []

    for channel in channels:
        name = channel.name or channel.location

        if type(channel) is Channel:
            channel_name_and_urls.append((join_url(channel.base_url, NOTICES_FN), name))

        elif type(channel) is MultiChannel:
            for url in channel.base_urls:
                channel_name_and_urls.append((join_url(url, NOTICES_FN), name))

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
    limit: Optional[int] = None,
    exclude: Optional[set[str]] = None,
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
    Determines whether channel notices are enabled and therefore displayed when
    invoking the `notices` command decorator.

    This only happens when:
     - offline is False
     - number_channel_notices is greater than 0

    Args:
        ctx: The conda context object
    """
    return ctx.number_channel_notices > 0 and not ctx.offline and not ctx.json


def is_channel_notices_cache_expired() -> bool:
    """
    Checks to see if the notices cache file we use to keep track of
    displayed notices is expired. This involves checking the mtime
    attribute of the file. Anything older than what is specified as
    the NOTICES_DECORATOR_DISPLAY_INTERVAL is considered expired.
    """
    cache_file = cache.get_notices_cache_file()

    cache_file_stat = cache_file.stat()
    now = time.time()
    seconds_since_checked = now - cache_file_stat.st_mtime

    return seconds_since_checked >= NOTICES_DECORATOR_DISPLAY_INTERVAL
