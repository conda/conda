# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from datetime import datetime
from enum import Enum
from pathlib import Path
from urllib import parse
from typing import NamedTuple, Optional, Sequence, Any

from conda.base.constants import NoticeLevel


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


class ChannelNoticeResponse(NamedTuple):
    url: str
    name: str
    json_data: Optional[dict]

    @property
    def notices(self) -> Sequence[ChannelNotice]:
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
