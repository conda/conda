# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
Defines a JSON reporter backend

This reporter backend is used to provide JSON strings for output rendering. It is
essentially just a wrapper around ``conda.common.serialize.json.dumps``.
"""

from __future__ import annotations

import sys
from threading import RLock
from typing import TYPE_CHECKING

from ...base.constants import DEFAULT_JSON_REPORTER_BACKEND
from ...common.io import swallow_broken_pipe
from ...common.serialize import json
from .. import hookimpl
from ..types import (
    CondaReporterBackend,
    ProgressBarBase,
    ReporterRendererBase,
    SpinnerBase,
)

if TYPE_CHECKING:
    from typing import Any

    from ..reporter_backends.events import (
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


# ---------------------------------------------------------------------------
# Private widget classes (kept for legacy progress_bar() / spinner() factory)
# ---------------------------------------------------------------------------


class _JSONProgressBar(ProgressBarBase):
    """
    Progress bar that outputs JSON to stdout.
    """

    _lock: RLock  # class-level lock shared across all instances

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
        """Used for our own sys.stdout.write/flush calls."""
        if not hasattr(cls, "_lock"):
            cls._lock = RLock()
        return cls._lock


class _JSONSpinner(SpinnerBase):
    """JSON mode spinner — intentionally silent."""

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


# Deprecated public aliases kept for third-party plugins during migration.
JSONProgressBar = _JSONProgressBar
JSONSpinner = _JSONSpinner


# ---------------------------------------------------------------------------
# JSONReporterRenderer
# ---------------------------------------------------------------------------


class JSONReporterRenderer(ReporterRendererBase):
    """
    Default implementation for JSON reporting in conda.
    """

    def __init__(self) -> None:
        self._fetch_tasks: dict[int, str] = {}  # task_id → description

    # ------------------------------------------------------------------
    # render_* event handlers
    # ------------------------------------------------------------------

    def render_data(self, event: RenderDataEvent) -> None:
        sys.stdout.write(json.dumps(event.data))

    def render_detail_view(self, event: DetailViewEvent) -> None:
        sys.stdout.write(json.dumps(event.data))

    def render_envs_list(self, event: EnvsListEvent) -> None:
        prefixes = list(event.prefixes)
        sys.stdout.write(json.dumps({"envs": prefixes}))

    def render_spinner_start(self, event: SpinnerStartEvent) -> None:
        # JSON mode: spinners are silent.
        pass

    def render_spinner_end(self, event: SpinnerEndEvent) -> None:
        # JSON mode: spinners are silent.
        pass

    def render_fetch_section_start(self, event: FetchSectionStartEvent) -> None:
        self._fetch_tasks.clear()

    def render_fetch_task_start(self, event: FetchTaskStartEvent) -> None:
        description = f"{event.name}-{event.version}" if event.name else ""
        self._fetch_tasks[event.task_id] = description

    def render_fetch_task_progress(self, event: FetchTaskProgressEvent) -> None:
        description = self._fetch_tasks.get(event.task_id, "")
        with _JSONProgressBar.get_lock():
            sys.stdout.write(
                f'{{"fetch":"{description}","finished":false,"maxval":1,"progress":{event.fraction:f}}}\n\0'
            )

    def render_fetch_task_end(self, event: FetchTaskEndEvent) -> None:
        description = self._fetch_tasks.pop(event.task_id, "")
        if event.success:
            with _JSONProgressBar.get_lock():
                sys.stdout.write(
                    f'{{"fetch":"{description}","finished":true,"maxval":1,"progress":1}}\n\0'
                )
                sys.stdout.flush()

    def render_fetch_section_end(self, event: FetchSectionEndEvent) -> None:
        self._fetch_tasks.clear()

    # ------------------------------------------------------------------
    # Synchronous query
    # ------------------------------------------------------------------

    def prompt(
        self, message: str = "Proceed", choices=("yes", "no"), default: str = "yes"
    ) -> str:
        """For JSON mode, prompting is a no-op."""

    # ------------------------------------------------------------------
    # Legacy factory methods — kept for third-party renderers during migration.
    # ------------------------------------------------------------------

    def render(self, data: Any, **kwargs) -> str:
        return json.dumps(data)

    def detail_view(self, data: dict[str, str | int | bool], **kwargs) -> str:
        return json.dumps(data)

    def envs_list(
        self, data: list[str] | dict[str, dict[str, str | bool | None]], **kwargs
    ) -> str:
        if isinstance(data, (list, tuple)):
            return json.dumps({"envs": data})
        return json.dumps(data)

    def progress_bar(
        self,
        description: str,
        **kwargs,
    ) -> ProgressBarBase:
        return _JSONProgressBar(description, **kwargs)

    def spinner(self, message: str, fail_message: str = "failed\n") -> SpinnerBase:
        return _JSONSpinner(message, fail_message)


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
