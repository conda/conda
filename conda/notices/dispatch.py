# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Notice broadcast bus -- like logging, not a global singleton.

Modules broadcast notices via ``NoticeBus.broadcast()`` during command
execution. ``conda.cli.conda_argparse.do_call()`` wraps subcommands in the
notices lifecycle and consumes/renders afterward.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import ClassVar

    from .types import ChannelNotice


class NoticeBus:
    """Class-level broadcast bus for channel/plugin notices.

    Use ``NoticeBus.broadcast(notice)`` from any module.  Call
    ``NoticeBus.consume()`` to drain and display.  Tests can call
    ``NoticeBus.clear()`` between runs.
    """

    _notices: ClassVar[list[ChannelNotice]] = []
    _ids: ClassVar[set[str]] = set()
    _channel_fetches_this_command: ClassVar[bool] = False

    @classmethod
    def broadcast(cls, notice: ChannelNotice) -> None:
        if notice.id not in cls._ids:
            cls._ids.add(notice.id)
            cls._notices.append(notice)

    @classmethod
    def consume(cls) -> list[ChannelNotice]:
        notices = cls._notices[:]
        cls._notices.clear()
        cls._ids.clear()
        return notices

    @classmethod
    def clear(cls) -> None:
        cls._notices.clear()
        cls._ids.clear()
        cls._channel_fetches_this_command = False

    @classmethod
    def mark_channel_fetch(cls) -> None:
        cls._channel_fetches_this_command = True

    @classmethod
    def commit_channel_fetch_interval(cls) -> None:
        """Reset the channel-notice fetch interval after a decorated command."""
        if cls._channel_fetches_this_command:
            from . import cache

            cache.get_notices_cache_file().touch()
            cls._channel_fetches_this_command = False
