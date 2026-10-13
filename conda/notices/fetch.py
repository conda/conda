# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Notices network fetch logic."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING

import requests  # noqa: TID253

from ..gateways.connection.session import get_session
from ..reporters import get_spinner
from .cache import cached_response
from .types import ChannelNoticeResponse

if TYPE_CHECKING:
    from collections.abc import Sequence

logger = logging.getLogger(__name__)


def get_notice_responses(
    url_and_names: Sequence[tuple[str, str]],
    silent: bool = False,
    max_workers: int = 10,
) -> Sequence[ChannelNoticeResponse]:
    """
    Provided a list of channel notification url/name tuples, return a sequence of
    ChannelNoticeResponse objects.

    Args:
        url_and_names: channel url and the channel name
        silent: turn off "loading animation" (defaults to False)
        max_workers: increase worker number in thread executor (defaults to 10)
    Returns:
        Sequence[ChannelNoticeResponse]
    """
    executor = ThreadPoolExecutor(max_workers=max_workers)

    with get_spinner("Retrieving notices"):
        return tuple(
            filter(
                None,
                (
                    chn_info
                    for chn_info in executor.map(
                        lambda args: get_channel_notice_response(*args), url_and_names
                    )
                ),
            )
        )


@cached_response
def get_channel_notice_response(url: str, name: str) -> ChannelNoticeResponse | None:
    """
    Return a channel response object. We use this to wrap the response with
    additional channel information to use. If the response was invalid we suppress/log
    and error message.
    """
    session = get_session(url)
    try:
        resp = session.get(
            url, allow_redirects=False, timeout=5
        )  # timeout: connect, read
    except requests.exceptions.Timeout:
        logger.info("Request timed out for channel: %s url: %s", name, url)
        return
    except requests.exceptions.RequestException as exc:
        logger.error("Request error <%s> for channel: %s url: %s", exc, name, url)
        return

    try:
        if resp.status_code < 300:
            return ChannelNoticeResponse(url, name, json_data=resp.json())
        else:
            logger.info("Received %s when trying to GET %s", resp.status_code, url)
    except ValueError:
        logger.info("Unable to parse JSON data for %s", url)
        return ChannelNoticeResponse(url, name, json_data=None)
