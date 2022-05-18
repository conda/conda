# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

"""
Handles all display/view logic
"""
from typing import Sequence

from .types import ChannelNotice, TerminalStyle
from .utils import get_locale_timestamp


def print_notices(channel_notices: Sequence[ChannelNotice], ansi_colors: bool = True):
    """
    Accepts a list of channel notice responses and prints a display.
    """
    cur_chn = None

    for ntc in channel_notices:
        if cur_chn != ntc.channel_name:
            print()
            if ansi_colors:
                channel_header = TerminalStyle.wrap_style("Channel:", TerminalStyle.BOLD)
            else:
                channel_header = "Channel:"
            channel_header += f" {ntc.channel_name}"
            print(channel_header)
            cur_chn = ntc.channel_name
        print_notice_message(ntc, ansi_colors=ansi_colors)
        print()


def print_notice_message(
    notice: ChannelNotice, indent: str = "  ", ansi_colors: bool = True
) -> None:
    """
    Prints a single channel notice
    """
    timestamp = "" if not notice.created_at else get_locale_timestamp(notice.created_at)

    if ansi_colors:
        level_style = TerminalStyle.get_color_from_level(notice.level)
        level_text = TerminalStyle.wrap_style(notice.level, level_style)
        level = f"[{level_text}]"

        if notice.created_at:
            level += TerminalStyle.wrap_style(f" -- {timestamp}", TerminalStyle.GRAY)
    else:
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
