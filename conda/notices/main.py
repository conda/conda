# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

"""
Module that provides the unofficial API for this feature. In order to maintain
a good level of encapsulation, other parts of the application should only import
from this module.
"""

import sys
from functools import wraps
from typing import Sequence, Tuple, Optional, Set
from urllib import parse

from conda.base.context import context
from conda.base.constants import NOTICES_MESSAGE_LIMIT, NOTICES_FN
from conda.models.channel import Channel

from . import cache
from . import views
from . import http
from .types import ChannelNotice, ChannelNoticeResponse


def display_notices(
    limit: Optional[int] = None,
    always_show_viewed: bool = True,
    silent: bool = False,
) -> None:
    """
    Entry point for displaying notices. This is called by the "notices" decorator as well
    as the sub-command "notices"
    """
    channel_name_urls = get_channel_name_and_urls(context.channel_objs)
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


NOTICES_DECORATOR_CONFIG_ERROR = (
    "Unable to parse decorated function arguments for conda.notices."
    ' Please make sure the function being decorated accepts both "args"'
    ' and "parser" positional parameters'
)


def notices(func):
    """
    Wrapper for "execute" entry points for subcommands.

    This decorator assumes two positional arguments:
        - args
        - parser

    If it's not configured correctly, we do our best to provide a friendly
    error message.

    This decorator will only display notices when context.disable_channel_notices and
    context.offline are both False.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            cmd_args, _ = args
        except ValueError:
            print(NOTICES_DECORATOR_CONFIG_ERROR, file=sys.stderr)
            return

        return_value = func(*args, **kwargs)

        if not context.disable_channel_notices and not context.offline:
            display_notices(
                limit=NOTICES_MESSAGE_LIMIT,
                always_show_viewed=False,
                silent=True,
            )

        return return_value

    return wrapper


ChannelName = str
ChannelUrl = str


def get_channel_name_and_urls(
    channels: [Sequence[Channel]],
) -> Sequence[Tuple[ChannelUrl, ChannelName]]:
    """Return a sequence of Channel name and urls"""

    def ensure_endswith(value: str, ends: str) -> str:
        return value if value.endswith(ends) else f"{value}{ends}"

    def join_url(value: str, join_val: str) -> str:
        return parse.urljoin(ensure_endswith(value, "/"), join_val)

    return tuple(
        (join_url(chn_url, NOTICES_FN), chn_obj.name or chn_obj.location)
        for chn_obj in channels
        for chn_url in chn_obj.base_urls
    )


def flatten_notice_responses(
    channel_notice_responses: Sequence[ChannelNoticeResponse],
) -> Sequence[ChannelNotice]:
    return tuple(ntc for chn in channel_notice_responses if chn.notices for ntc in chn.notices)


def filter_notices(
    channel_notices: Sequence[ChannelNotice],
    limit: Optional[int] = None,
    exclude: Optional[Set[str]] = None,
) -> Sequence[ChannelNotice]:
    """
    Perform filtering actions for the provided sequence of ChannelNotice objects.
    """
    if exclude:
        channel_notices = tuple(chn for chn in channel_notices if chn.id not in exclude)

    if limit is not None:
        channel_notices = channel_notices[:limit]

    return channel_notices
