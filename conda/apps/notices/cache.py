# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

"""
Handles all caching logic including:
  - Retrieving from cache
  - Saving to cache
  - Determining whether not certain items have expired and need to be refreshed
"""
import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from functools import wraps
from pathlib import Path
from typing import Optional, Sequence, Set

import requests

from conda._vendor.appdirs import user_cache_dir
from conda.base.constants import APP_NAME, NOTICES_CACHE_DB, NOTICES_CACHE_SUBDIR
from conda.gateways.connection.session import CondaSession
from conda.utils import ensure_dir_exists

from .types import ChannelNoticeResponse, ChannelNotice
from .logging import logger


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
