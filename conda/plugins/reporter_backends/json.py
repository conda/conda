# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
Defines a JSON reporter backend

This reporter backend is used to provide JSON strings for output rendering. It is
essentially just a wrapper around ``conda.common.serialize.json.dumps``.
"""

from __future__ import annotations

import logging
import sys
from threading import RLock
from typing import TYPE_CHECKING

from ...base.constants import DEFAULT_JSON_REPORTER_BACKEND
from ...common.io import swallow_broken_pipe
from ...common.serialize import json
from ...deprecations import deprecated
from .. import hookimpl
from ..types import (
    CondaReporterBackend,
    ProgressBarBase,
    ReporterRendererBase,
    SpinnerBase,
)
from .events import (
    DetailViewEvent,
    EnvsListEvent,
    FetchSectionEndEvent,
    FetchSectionStartEvent,
    FetchTaskEndEvent,
    FetchTaskProgressEvent,
    FetchTaskStartEvent,
    RenderDataEvent,
    SpinnerEndEvent,
    SpinnerStartEvent,
)

if TYPE_CHECKING:
    from typing import Any

    from .events import Event

logger = logging.getLogger(__name__)


class JSONProgressBar(ProgressBarBase):
    """
    Progress bar that outputs JSON to stdout
    """

    def __init__(
        self,
        description: str,
        enabled: bool = True,
        **kwargs,
    ):
        super().__init__(description)
        self.enabled = enabled

    def update_to(self, fraction) -> None:
        with self.get_lock():
            if self.enabled:
                sys.stdout.write(
                    f'{{"fetch":"{self.description}","finished":false,"maxval":1,"progress":{fraction:f}}}\n\0'
                )

    def refresh(self):
        pass

    @swallow_broken_pipe
    def close(self):
        with self.get_lock():
            if self.enabled:
                sys.stdout.write(
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


class JSONReporterRenderer(ReporterRendererBase):
    """
    Default implementation for JSON reporting in conda
    """

    def __init__(self) -> None:
        self._fetch_bars: dict[int, JSONProgressBar] = {}

    def handle(self, event: Event) -> None:
        match event:
            case RenderDataEvent() | DetailViewEvent():
                sys.stdout.write(json.dumps(event.data))
            case EnvsListEvent():
                sys.stdout.write(json.dumps({"envs": list(event.prefixes)}))
            case SpinnerStartEvent() | SpinnerEndEvent():
                # Spinners are intentionally silent in JSON output.
                pass
            case FetchSectionStartEvent():
                self._fetch_bars.clear()
            case FetchTaskStartEvent():
                description = f"{event.name}-{event.version}" if event.name else ""
                self._fetch_bars[event.task_id] = JSONProgressBar(description)
            case FetchTaskProgressEvent():
                if (bar := self._fetch_bars.get(event.task_id)) is not None:
                    bar.update_to(event.fraction)
            case FetchTaskEndEvent():
                if (bar := self._fetch_bars.get(event.task_id)) is not None:
                    if event.success:
                        bar.finish()
                    bar.refresh()
            case FetchSectionEndEvent():
                for bar in self._fetch_bars.values():
                    bar.close()
                self._fetch_bars.clear()
            case _:
                logger.debug("No handler for %s; ignoring", type(event).__name__)

    @deprecated(
        "27.3",
        "27.9",
        addendum="Implement `handle` and handle `RenderDataEvent` instead.",
    )
    def render(self, data: Any, **kwargs) -> str:
        return json.dumps(data)

    @deprecated(
        "27.3",
        "27.9",
        addendum="Use `DetailViewEvent` instead.",
    )
    def detail_view(self, data: dict[str, str | int | bool], **kwargs) -> str:
        return json.dumps(data)

    @deprecated(
        "27.3",
        "27.9",
        addendum="Use `EnvsListEvent` instead.",
    )
    def envs_list(
        self, data: list[str] | dict[str, dict[str, str | bool | None]], **kwargs
    ) -> str:
        if isinstance(data, (list, tuple)):
            return json.dumps({"envs": data})
        return json.dumps(data)

    @deprecated(
        "27.3",
        "27.9",
        addendum="Use the `FetchTask*Event` events instead.",
    )
    def progress_bar(
        self,
        description: str,
        **kwargs,
    ) -> ProgressBarBase:
        return JSONProgressBar(description, **kwargs)

    @deprecated(
        "27.3",
        "27.9",
        addendum="Use `SpinnerStartEvent` and `SpinnerEndEvent` instead.",
    )
    def spinner(self, message: str, fail_message: str = "failed\n") -> SpinnerBase:
        return JSONSpinner(message, fail_message)

    def prompt(
        self, message: str = "Proceed", choices=("yes", "no"), default: str = "yes"
    ) -> str:
        """
        For this class, we want this method to do nothing
        """


class JSONSpinner(SpinnerBase):
    """
    This class for a JSONSpinner does nothing because we do not want to include this output.
    """

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


@hookimpl(
    tryfirst=True
)  # make sure the default json reporter backend can't be overridden
def conda_reporter_backends():
    """
    Reporter backend for JSON

    This is the default reporter backend that returns objects as JSON strings.
    """
    yield CondaReporterBackend(
        name=DEFAULT_JSON_REPORTER_BACKEND,
        description="Default implementation for JSON reporting in conda",
        renderer=JSONReporterRenderer,
    )
