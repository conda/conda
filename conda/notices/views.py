# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

"""
Handles all display/view logic
"""
from datetime import datetime
from typing import Sequence

from .types import ChannelNotice


def print_notices(channel_notices: Sequence[ChannelNotice]):
    """
    Accepts a list of channel notice responses and prints a display.
    """
    cur_chn = None

    for ntc in channel_notices:
        if cur_chn != ntc.channel_name:
            print()
            channel_header = "Channel:"
            channel_header += f" {ntc.channel_name}"
            print(channel_header)
            cur_chn = ntc.channel_name
        print_notice_message(ntc)
        print()


def print_notice_message(notice: ChannelNotice, indent: str = "  ") -> None:
    """
    Prints a single channel notice
    """
    timestamp = "" if not notice.created_at else get_locale_timestamp(notice.created_at)

    level = f"[{notice.level}] -- {timestamp}"

    print(f"{indent}{level}\n{indent}{notice.message}")


def print_more_notices_message(
    total_notices: int, displayed_notices: int, viewed_notices: int
) -> None:
    """
    Conditionally shows a message informing users how many more message there are.
    """
    notices_not_shown = total_notices - viewed_notices - displayed_notices

    if notices_not_shown > 0:
        if notices_not_shown > 1:
            msg = f"There are {notices_not_shown} more messages. " "To retrieve them run:\n\n"
        else:
            msg = f"There is {notices_not_shown} more message. " "To retrieve it run:\n\n"
        print(f"{msg}conda notices\n")


def get_locale_timestamp(timestamp: datetime) -> str:
    """
    Returns best attempt at a locale aware timestamp.
    """
    return timestamp.strftime("%c")
