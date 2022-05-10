# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

import logging
import os.path
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
from functools import wraps
from typing import NamedTuple, Optional, Sequence, Tuple, Literal
from urllib import parse

from ._vendor.appdirs import user_cache_dir
from .base.constants import NOTICES_FN, APP_NAME
from .common.io import Spinner
from .gateways.connection.session import CondaSession
from .gateways.disk import mkdir_p
from .models.channel import Channel

logger = logging.getLogger(__name__)


class ChannelNoticeResponse(NamedTuple):
    url: str
    name: str
    json_data: Optional[dict]

    @property
    def notices(self) -> Sequence["ChannelNotice"]:
        if self.json_data:
            return tuple(
                ChannelNotice(
                    id=msg.get("id"),
                    channel_name=self.name,
                    message=msg.get("message"),
                    level=msg.get("level"),
                    created_at=msg.get("created_at"),
                    expiry=msg.get("expiry"),
                    interval=msg.get("interval"),
                )
                for msg in self.json_data.get("notices", tuple())
            )

    @classmethod
    def get_cache_key(cls, cache_dir: str, url: str, name: str) -> str:
        url_obj = parse.urlparse(url)
        path = url_obj.path.replace("/", "-")
        cache_filename = f"{name}{path}"
        cache_key = os.path.join(cache_dir, cache_filename)

        return cache_key


class ChannelNotice(NamedTuple):
    """
    Represents an individual channel notice
    """
    id: Optional[str]
    channel_name: Optional[str]
    message: Optional[str]
    level: Optional[Literal["critical", "warning", "info"]]
    created_at: Optional[str]
    expiry: Optional[int]
    interval: Optional[int]


def notifications(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        return_value = func(*args, **kwargs)
        return return_value

    return wrapper


def cached_response(func):
    @wraps(func)
    def wrapper(url: str, name: str):
        cache_val = get_notice_response_from_cache(url, name)

        if cache_val:
            return cache_val

        return_value = func(url, name)
        if return_value is not None:
            write_notice_response_to_cache(return_value)
        return return_value

    return wrapper


def get_notice_responses(
    url_and_names: Sequence[Tuple[str, str]], silent: bool = False, max_workers: int = 10
) -> Sequence[ChannelNoticeResponse]:
    """
    Provided a list of channel notification url/name tuples, return a sequence of
    ChannelNoticeResponse objects.

    Options:
        - silent: turn off "loading animation" (defaults to False)
        - max_workers: increase worker number in thread executor (defaults to 10)
    """
    executor = ThreadPoolExecutor(max_workers=max_workers)

    def _get_notices() -> Sequence[ChannelNoticeResponse]:
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

    if silent:
        return _get_notices()

    with Spinner("Retrieving notices"):
        return _get_notices()


def flatten_notice_responses(
    channel_notice_responses: Sequence[ChannelNoticeResponse],
) -> Sequence[ChannelNotice]:
    return tuple(ntc for chn in channel_notice_responses for ntc in chn.notices)


@cached_response
def get_channel_notice_response(url: str, name: str) -> Optional[ChannelNoticeResponse]:
    """
    Return a channel response object. We use this to wrap the response with
    additional channel information to use. If the response was invalid we suppress/log
    and error message.
    """
    session = CondaSession()
    resp = session.get(url, allow_redirects=False)

    try:
        if resp.status_code < 300:
            return ChannelNoticeResponse(url, name, json_data=resp.json())
        else:
            logger.error(f"Received {resp.status_code} when trying to GET {url}")
    except ValueError:
        logger.error(f"Unable able to parse JSON data for {url}")
        return ChannelNoticeResponse(url, name, json_data=None)


def is_notice_response_cache_expired(channel_notice_response: ChannelNoticeResponse) -> bool:
    """
    This checks the contents of the cache response to see if it is expired.

    If for whatever reason we encounter an exception while parsing the individual
    messages, we assume an invalid cache and return true.
    """
    now = datetime.now(timezone.utc)

    def is_channel_notice_expired(created_at: str, expiry: int) -> bool:
        try:
            created_at_obj = datetime.fromisoformat(created_at)
        except (ValueError, TypeError):
            # If the value is somehow invalid or corrupted,
            # we just invalidate the cache
            return True

        expires_at = created_at_obj + timedelta(seconds=expiry)
        zero = timedelta(seconds=0)

        return expires_at - now < zero

    return any(
        (
            is_channel_notice_expired(chn.created_at, chn.expiry)
            for chn in channel_notice_response.notices
        )
    )


def get_notice_response_from_cache(url: str, name: str) -> Optional[ChannelNoticeResponse]:
    """
    Retrieves a notice response object from cache if it exists.
    """
    cache_dir = user_cache_dir(APP_NAME)
    cache_key = ChannelNoticeResponse.get_cache_key(cache_dir, url, name)

    if os.path.isfile(cache_key):
        with open(cache_key, "r") as fp:
            data = json.load(fp)
        chn_ntc_resp = ChannelNoticeResponse(url, name, data)

        if not is_notice_response_cache_expired(chn_ntc_resp):
            return chn_ntc_resp


def write_notice_response_to_cache(channel_notice_response: ChannelNoticeResponse) -> None:
    """
    Writes our notice data to our local cache location
    """
    # TODO: Not sure this is the best place to call this.
    #       It would be better to call once on start up.
    cache_dir = mkdir_p(user_cache_dir(APP_NAME))
    cache_key = ChannelNoticeResponse.get_cache_key(
        cache_dir, channel_notice_response.url, channel_notice_response.name
    )

    with open(cache_key, "w") as fp:
        json.dump(channel_notice_response.json_data, fp)


def print_notices(channel_notices: Sequence[ChannelNotice], limit: Optional[int] = None):
    """
    Accepts a list of channel notice responses
    """
    remaining_notices = 0

    if limit is not None:
        remaining_notices = len(channel_notices) - limit
        channel_notices = channel_notices[:limit]

    cur_chn = None
    ident = " " * 2

    for ntc in channel_notices:
        if cur_chn != ntc.channel_name:
            print()
            print(f"Channel: {ntc.channel_name}")
            cur_chn = ntc.channel_name
        print(f"{ident}[{ntc.level}]\n{ident}{ntc.message}")
        print()

    if remaining_notices > 0:
        print(
            f'There are {remaining_notices} more message{"s" if remaining_notices > 1 else ""}.'
            "To retrieve them run:\n\n"
            "conda notices\n"
        )


def get_channel_objs(channel_names: Sequence[str]) -> Sequence[Channel]:
    """Get a list of channel base urls from a single channel name"""
    return tuple(Channel(chn) for chn in channel_names)


def get_channel_name_and_urls(channels: [Sequence[Channel]]) -> Sequence[Tuple[str, str]]:
    """Return a sequence of Ch"""

    def ensure_endswith(value: str, ends: str) -> str:
        return value if value.endswith(ends) else f"{value}{ends}"

    def join_url(value: str, join_val: str) -> str:
        return parse.urljoin(ensure_endswith(value, "/"), join_val)

    return tuple(
        (join_url(chn_url, NOTICES_FN), chn_obj.name or chn_obj.location)
        for chn_obj in channels
        for chn_url in chn_obj.base_urls
    )
