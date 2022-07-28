# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from datetime import datetime
import hashlib
from pathlib import Path
from typing import NamedTuple, Optional, Sequence

from ..base.constants import NoticeLevel


class ChannelNotice(NamedTuple):
    """
    Represents an individual channel notice
    """

    id: Optional[str]
    channel_name: Optional[str]
    message: Optional[str]
    level: NoticeLevel
    created_at: Optional[datetime]
    expired_at: Optional[datetime]
    interval: Optional[int]


class ChannelNoticeResponse(NamedTuple):
    url: str
    name: str
    json_data: Optional[dict]

    @property
    def notices(self) -> Sequence[ChannelNotice]:
        if self.json_data:
            notices = self.json_data.get("notices", tuple())

            return tuple(
                ChannelNotice(
                    id=notice.get("id"),
                    channel_name=self.name,
                    message=notice.get("message"),
                    level=self._parse_notice_level(notice.get("level")),
                    created_at=self._parse_iso_timestamp(notice.get("created_at")),
                    expired_at=self._parse_iso_timestamp(notice.get("expired_at")),
                    interval=notice.get("interval"),
                )
                for notice in notices
            )

        # Default value
        return tuple()

    @staticmethod
    def _parse_notice_level(level: Optional[str]) -> NoticeLevel:
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
    def _parse_iso_timestamp(iso_timestamp: Optional[str]) -> Optional[datetime]:
        """
        We try to parse this as a valid ISO timestamp and fail over to a default value of none.
        """
        if iso_timestamp is None:
            return None
        try:
            return datetime.fromisoformat(iso_timestamp)
        except ValueError:
            return None

    @classmethod
    def get_cache_key(cls, url: str, cache_dir: Path) -> Path:
        """
        Returns the place where this channel response will be stored as cache by hashing the url.
        """
        bytes_filename = url.encode()
        sha256_hash = hashlib.sha256(bytes_filename)
        cache_filename = f"{sha256_hash.hexdigest()}.json"

        return cache_dir.joinpath(cache_filename)
