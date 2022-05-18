# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from datetime import datetime
from typing import Sequence, Tuple, Optional, Set
from urllib import parse

from conda.base.constants import NOTICES_FN
from conda.models.channel import Channel

from .types import ChannelNotice, ChannelNoticeResponse


def get_locale_timestamp(timestamp: datetime) -> str:
    """
    Returns best attempt at a locale aware timestamp.
    """
    return timestamp.strftime("%c")


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
    return tuple(ntc for chn in channel_notice_responses for ntc in chn.notices)


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
