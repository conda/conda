# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
Defines a JSON reporter backend

This reporter backend is used to provide JSON strings for output rendering. It is
essentially just a wrapper around ``conda.common.serialize.json_dump``.
"""

from __future__ import annotations

from threading import RLock
from typing import TYPE_CHECKING

from ...common.io import swallow_broken_pipe
from ...common.serialize import json_dump
from .. import CondaReporterBackend, hookimpl
from ..types import ProgressBarBase, ReporterRendererBase

if TYPE_CHECKING:
    from typing import Any, Callable, ContextManager


class JSONProgressBar(ProgressBarBase):
    """
    Progress bar that outputs JSON to stdout
    """

    def __init__(
        self,
        description: str,
        io_context_manager: Callable[[], ContextManager],
        enabled: bool = True,
        **kwargs,
    ):
        super().__init__(description, io_context_manager)
        self.file = self._io_context_manager.__enter__()
        self.enabled = enabled

    def update_to(self, fraction) -> None:
        with self.get_lock():
            if self.enabled:
                self.file.write(
                    f'{{"fetch":"{self.description}","finished":false,"maxval":1,"progress":{fraction:f}}}\n\0'
                )

    def refresh(self):
        pass

    @swallow_broken_pipe
    def close(self):
        with self.get_lock():
            if self.enabled:
                self.file.write(
                    f'{{"fetch":"{self.description}","finished":true,"maxval":1,"progress":1}}\n\0'
                )
                self.file.flush()

        self._io_context_manager.__exit__(None, None, None)

    @classmethod
    def get_lock(cls):
        """
        Used for our own sys.stdout.write/flush calls
        """
        if not hasattr(cls, "_lock"):
            cls._lock = RLock()
        return cls._lock


class JSONReporterRenderer(ReporterRendererBase):
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
        self,
        description: str,
        io_context_manager: Callable[[], ContextManager],
        **kwargs,
    ) -> ProgressBarBase:
        return JSONProgressBar(description, io_context_manager, **kwargs)


@hookimpl
def conda_reporter_backends():
    """
    Reporter backend for JSON

    This is the default reporter backend that returns objects as JSON strings
    that can be passed to reporter outputs.
    """
    yield CondaReporterBackend(
        name="json",
        description="Default implementation for JSON reporting in conda",
        renderer=JSONReporterRenderer,
    )
