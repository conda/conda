# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
Defines a JSON reporter handler

This reporter handler is used to provide JSON strings for output rendering. It is
essentially just a wrapper around ``json.dumps``.
"""

from __future__ import annotations

import sys
from threading import RLock
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any, Callable

from ...common.io import ProgressBarBase, swallow_broken_pipe
from ...common.serialize import json_dump
from .. import CondaReporterHandler, hookimpl
from ..types import ReporterHandlerBase


class JSONProgressBar(ProgressBarBase):
    """
    Progress bar that outputs JSON to stdout
    """

    def update_to(self, fraction) -> None:
        with self.get_lock():
            self._render(
                f'{{"fetch":"{self.description}","finished":false,"maxval":1,"progress":{fraction:f}}}\n\0'
            )

    def refresh(self):
        pass

    @swallow_broken_pipe
    def close(self):
        with self.get_lock():
            self._render(
                f'{{"fetch":"{self.description}","finished":true,"maxval":1,"progress":1}}\n\0'
            )
            sys.stdout.flush()

    @classmethod
    def get_lock(cls):
        """
        Used for our own sys.stdout.write/flush calls
        """
        if not hasattr(cls, "_lock"):
            cls._lock = RLock()
        return cls._lock


class JSONReporterHandler(ReporterHandlerBase):
    """
    Default implementation for JSON reporting in conda
    """

    def render(self, data: Any, **kwargs) -> str:
        return json_dump(data)

    def detail_view(self, data: dict[str, str | int | bool], **kwargs) -> str:
        return json_dump(data)

    def envs_list(self, data, **kwargs) -> str:
        return json_dump({"envs": data})

    def progress_bar(
        self, description: str, render: Callable, **kwargs
    ) -> ProgressBarBase:
        return JSONProgressBar(description, render)


@hookimpl
def conda_reporter_handlers():
    """
    Reporter handler for JSON

    This is the default reporter handler that returns objects as JSON strings
    that can be passed to output handlers.
    """
    yield CondaReporterHandler(
        name="json",
        description="Default implementation for JSON reporting in conda",
        handler=JSONReporterHandler(),
    )
