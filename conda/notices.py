# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

import logging
import os.path
import json
import sqlite3
import sys
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
from enum import Enum
from functools import wraps
from pathlib import Path
from typing import NamedTuple, Optional, Sequence, Tuple, Any, Set
from urllib import parse

import requests.exceptions

from ._vendor.appdirs import user_cache_dir
from .base.constants import (
    APP_NAME,
    NOTICES_FN,
    NOTICES_CACHE_SUBDIR,
    NOTICES_MESSAGE_LIMIT,
    NOTICES_CACHE_DB,
    NoticeLevel,
)
from .base.context import context
from .common.io import Spinner
from .gateways.connection.session import CondaSession
from .models.channel import Channel
from .utils import ensure_dir_exists

logger = logging.getLogger(__name__)


class ChannelNoticeResponse(NamedTuple):
    url: str
    name: str
    json_data: Optional[dict]

    @property
    def notices(self) -> Sequence["ChannelNotice"]:
        if self.json_data:
            notice_data = self.json_data.get("notices", tuple())

            return tuple(
                ChannelNotice(
                    id=msg.get("id"),
                    channel_name=self.name,
                    message=msg.get("message"),
                    level=self._parse_notice_level(msg.get("level")),
                    created_at=self._parse_iso_timestamp(msg.get("created_at")),
                    expiry=msg.get("expiry"),
                    interval=msg.get("interval"),
                )
                for msg in notice_data
            )

    @staticmethod
    def _parse_notice_level(level: str) -> NoticeLevel:
        """
        We use this to validate notice levels and provide reasonable defaults
        if any are invalid.
        """
        try:
            return NoticeLevel(level)
        except ValueError:
            # If we get an invalid value, rather than fail, we simply use a reasonable default
            return NoticeLevel(NoticeLevel.INFO)

    @staticmethod
    def _parse_iso_timestamp(iso_timestamp: str) -> Optional[datetime]:
        """
        We try to parse this as a valid ISO timestamp and fail over to a default value of none.
        """
        try:
            return datetime.fromisoformat(iso_timestamp)
        except ValueError:
            return

    @classmethod
    def get_cache_key(cls, url: str, name: str, cache_dir: Path) -> str:
        """Returns the place where this channel response will be stored as cache"""
        url_obj = parse.urlparse(url)
        path = url_obj.path.replace("/", "-")
        cache_filename = f"{name}{path}"
        cache_key = cache_dir.joinpath(cache_filename)

        return cache_key


class ChannelNotice(NamedTuple):
    """
    Represents an individual channel notice
    """
    id: Optional[str]
    channel_name: Optional[str]
    message: Optional[str]
    level: NoticeLevel
    created_at: Optional[datetime]
    expiry: Optional[int]
    interval: Optional[int]


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


def cached_response(func):
    @wraps(func)
    def wrapper(url: str, name: str):
        cache_dir = get_notices_cache_dir()
        cache_val = get_notice_response_from_cache(url, name, cache_dir)

        if cache_val:
            return cache_val

        return_value = func(url, name)
        if return_value is not None:
            write_notice_response_to_cache(return_value, cache_dir)

        return return_value

    return wrapper


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
    channel_name_urls = get_channel_name_and_urls(context.channel_objs)
    channel_notice_responses = get_notice_responses(channel_name_urls, silent=silent)
    channel_notices = flatten_notice_responses(channel_notice_responses)
    num_total_notices = len(channel_notices)

    with notices_cache_db(get_notices_cache_dir()) as conn:
        viewed_notices = None
        num_viewed_notices = 0
        if not always_show_viewed:
            viewed_notices = get_viewed_channel_notice_ids(conn, channel_notices)
            num_viewed_notices = len(viewed_notices)

        channel_notices = filter_notices(channel_notices, limit=limit, exclude=viewed_notices)
        if len(channel_notices) == 0:
            return

        print_notices(channel_notices, ansi_colors=ansi_colors)

        # Updates cache database, marking displayed notices as "viewed"
        tuple(mark_channel_notices_as_viewed(conn, ntc) for ntc in channel_notices)

    print_more_notices_message(num_total_notices, len(channel_notices), num_viewed_notices)


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


@cached_response
def get_channel_notice_response(url: str, name: str) -> Optional[ChannelNoticeResponse]:
    """
    Return a channel response object. We use this to wrap the response with
    additional channel information to use. If the response was invalid we suppress/log
    and error message.
    """
    session = CondaSession()
    try:
        resp = session.get(url, allow_redirects=False, timeout=5)  # timeout: connect, read
    except requests.exceptions.Timeout:
        logger.info(f"Request timed out for channel: {name} url: {url}")
        return

    try:
        if resp.status_code < 300:
            return ChannelNoticeResponse(url, name, json_data=resp.json())
        else:
            logger.info(f"Received {resp.status_code} when trying to GET {url}")
    except ValueError:
        logger.info(f"Unable able to parse JSON data for {url}")
        return ChannelNoticeResponse(url, name, json_data=None)


def is_notice_response_cache_expired(channel_notice_response: ChannelNoticeResponse) -> bool:
    """
    This checks the contents of the cache response to see if it is expired.

    If for whatever reason we encounter an exception while parsing the individual
    messages, we assume an invalid cache and return true.
    """
    now = datetime.now(timezone.utc)

    def is_channel_notice_expired(created_at: datetime, expiry: int) -> bool:
        expires_at = created_at + timedelta(seconds=expiry)
        zero = timedelta(seconds=0)

        return expires_at - now < zero

    return any(
        (
            is_channel_notice_expired(chn.created_at, chn.expiry)
            for chn in channel_notice_response.notices
        )
    )


@ensure_dir_exists
def get_notices_cache_dir() -> Path:
    """Returns the location of the notices cache as a Path object"""
    return Path(user_cache_dir(APP_NAME)).joinpath(NOTICES_CACHE_SUBDIR)


def get_notice_response_from_cache(
    url: str, name: str, cache_dir: Path
) -> Optional[ChannelNoticeResponse]:
    """
    Retrieves a notice response object from cache if it exists.
    """
    cache_key = ChannelNoticeResponse.get_cache_key(url, name, cache_dir)

    if os.path.isfile(cache_key):
        with open(cache_key, "r") as fp:
            data = json.load(fp)
        chn_ntc_resp = ChannelNoticeResponse(url, name, data)

        if not is_notice_response_cache_expired(chn_ntc_resp):
            return chn_ntc_resp


def write_notice_response_to_cache(
    channel_notice_response: ChannelNoticeResponse, cache_dir: Path
) -> None:
    """
    Writes our notice data to our local cache location
    """
    cache_key = ChannelNoticeResponse.get_cache_key(
        channel_notice_response.url, channel_notice_response.name, cache_dir
    )

    with open(cache_key, "w") as fp:
        json.dump(channel_notice_response.json_data, fp)


NOTICES_CACHE_TABLE_NAME = "notices"

NOTICES_CACHE_TABLE_DDL = f"""
CREATE TABLE IF NOT EXISTS {NOTICES_CACHE_TABLE_NAME} (
  id text,
  channel_name text,
  viewed bool,
  PRIMARY KEY (id)
)"""


@contextmanager
def notices_cache_db(cache_dir: Path):
    """Returns a sqlite connection to our cache database"""
    cache_db_path = cache_dir.joinpath(NOTICES_CACHE_DB)
    conn = sqlite3.connect(cache_db_path)
    conn.execute(NOTICES_CACHE_TABLE_DDL)

    yield conn

    conn.commit()
    conn.close()


def mark_channel_notices_as_viewed(
    conn: sqlite3.Connection, channel_notice: ChannelNotice
) -> None:
    """
    Insert channel notice into our database marking it as read.
    """
    sql = f"INSERT INTO {NOTICES_CACHE_TABLE_NAME} (id, channel_name, viewed) VALUES (?, ?, ?)"
    try:
        conn.execute(sql, (channel_notice.id, channel_notice.channel_name, True))
    except sqlite3.Error as exc:
        logger.debug(exc)
        logger.debug(channel_notice)


def get_viewed_channel_notice_ids(
    conn: sqlite3.Connection, channel_notices: Sequence[ChannelNotice]
) -> Set[str]:
    """
    Return the ids of the channel notices which have already been seen.
    """
    chn_ntc_ids = tuple(chn.id for chn in channel_notices)
    place_holders = ",".join("?" * len(chn_ntc_ids))
    sql = f"SELECT id FROM notices WHERE viewed = true AND id in ({place_holders})"
    result = conn.execute(sql, chn_ntc_ids)

    return {row[0] for row in result.fetchall()}


class TerminalStyle(Enum):
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    GRAY = "\033[90m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"

    def __str__(self):
        return self.value

    @classmethod
    def get_color_from_level(cls, level: NoticeLevel) -> "TerminalStyle":
        if level == NoticeLevel.CRITICAL:
            return cls.FAIL
        elif level == NoticeLevel.INFO:
            return cls.OKGREEN
        elif level == NoticeLevel.WARNING:
            return cls.WARNING
        else:
            return cls.OKBLUE

    @classmethod
    def wrap_style(cls, text: Any, style: "TerminalStyle") -> str:
        return f"{style}{text}{TerminalStyle.ENDC}"


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


def get_locale_timestamp(timestamp: datetime) -> str:
    """
    Returns best attempt at a locale aware timestamp.
    """
    return timestamp.strftime("%c")


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
