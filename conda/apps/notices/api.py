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
from typing import Optional

from conda.base.context import context
from conda.base.constants import NOTICES_MESSAGE_LIMIT

from . import cache
from . import utils
from . import views
from . import http
from .constants import NOTICES_DECORATOR_CONFIG_ERROR


def display_notices(
    limit: Optional[int] = None,
    ansi_colors: bool = True,
    always_show_viewed: bool = True,
    silent: bool = False,
) -> None:
    """
    Entry point for displaying notices. This is called by the "notices" decorator as well
    as the sub-command "notices"
    """
    channel_name_urls = utils.get_channel_name_and_urls(context.channel_objs)
    channel_notice_responses = http.get_notice_responses(channel_name_urls, silent=silent)
    channel_notices = utils.flatten_notice_responses(channel_notice_responses)
    num_total_notices = len(channel_notices)

    with cache.notices_cache_db(cache.get_notices_cache_dir()) as conn:
        viewed_notices = None
        num_viewed_notices = 0
        if not always_show_viewed:
            viewed_notices = cache.get_viewed_channel_notice_ids(conn, channel_notices)
            num_viewed_notices = len(viewed_notices)

        channel_notices = utils.filter_notices(
            channel_notices, limit=limit, exclude=viewed_notices
        )
        if len(channel_notices) == 0:
            return

        views.print_notices(channel_notices, ansi_colors=ansi_colors)

        # Updates cache database, marking displayed notices as "viewed"
        tuple(cache.mark_channel_notices_as_viewed(conn, ntc) for ntc in channel_notices)

    views.print_more_notices_message(num_total_notices, len(channel_notices), num_viewed_notices)


def notices(func):
    """
    Wrapper for "execute" entry points for subcommands.

    This decorator assumes two positional arguments:
        - args
        - parser

    If it's not configured correctly, we do our best to provide a friendly
    error message.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            cmd_args, _ = args
        except ValueError:
            print(NOTICES_DECORATOR_CONFIG_ERROR, file=sys.stderr)
            return

        if context.disable_channel_notices:
            return func(*args, **kwargs)

        return_value = func(*args, **kwargs)

        display_notices(
            ansi_colors=not cmd_args.no_ansi_colors,
            limit=NOTICES_MESSAGE_LIMIT,
            always_show_viewed=False,
            silent=True,
        )

        return return_value

    return wrapper
