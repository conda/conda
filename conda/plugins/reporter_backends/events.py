# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
Event types used to communicate with reporter backends.

Events are immutable data objects sent through
:meth:`conda.reporters.CondaReporter.send`, which hands each event to
:meth:`conda.plugins.types.ReporterRendererBase.handle`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any

    from ...common.path import PathType
    from ...core.prefix_data import PrefixData


@dataclass(frozen=True)
class Event:
    """
    Immutable base class for all reporter events.
    """


@dataclass(frozen=True)
class RenderDataEvent(Event):
    """
    Generic data-render event.

    Args:
        data: The data to render.
        style: Optional renderer style name. ``None`` means plain rendering.
    """

    data: Any
    style: str | None = None


@dataclass(frozen=True)
class DetailViewEvent(Event):
    """
    Render a key/value mapping as a tabular detail view.

    Args:
        data: Mapping of header strings to primitive values.
    """

    data: dict[str, str | int | bool]


@dataclass(frozen=True)
class EnvsListEvent(Event):
    """
    Render a list of conda environments.

    Args:
        prefixes: Paths or ``PrefixData`` objects to list.
        show_size: Whether to include a disk-size column.
    """

    prefixes: tuple[PathType | PrefixData, ...]
    show_size: bool = False


@dataclass(frozen=True)
class SpinnerStartEvent(Event):
    """
    Signal that a spinner should start.

    Args:
        message: Label shown next to the spinner.
        fail_message: Text shown when the operation fails.
    """

    message: str
    fail_message: str = "failed\n"


@dataclass(frozen=True)
class SpinnerEndEvent(Event):
    """
    Signal that the spinner with a matching message should stop.

    Args:
        message: Must match the ``message`` of the corresponding start event.
        success: Whether the guarded operation completed without error.
    """

    message: str
    success: bool


@dataclass(frozen=True)
class FetchSectionStartEvent(Event):
    """
    Signal that a fetch-and-extract section is beginning.
    """


@dataclass(frozen=True)
class FetchTaskStartEvent(Event):
    """
    Signal that a single package fetch task is starting.

    Args:
        task_id: Identifier unique within the enclosing fetch section.
        name: Package name.
        version: Package version.
        size: Download size in bytes, or ``None`` if unknown.
    """

    task_id: int
    name: str
    version: str
    size: int | None = None


@dataclass(frozen=True)
class FetchTaskProgressEvent(Event):
    """
    Report progress on an in-flight fetch task.

    Args:
        task_id: Must match a previously sent :class:`FetchTaskStartEvent`.
        fraction: Completion fraction between ``0.0`` and ``1.0``.
    """

    task_id: int
    fraction: float


@dataclass(frozen=True)
class FetchTaskEndEvent(Event):
    """
    Signal that a fetch task has finished.

    Args:
        task_id: Must match a previously sent :class:`FetchTaskStartEvent`.
        success: Whether the task completed without error.
    """

    task_id: int
    success: bool


@dataclass(frozen=True)
class FetchSectionEndEvent(Event):
    """
    Signal that the fetch-and-extract section has finished.

    Args:
        success: Whether all tasks completed without error.
    """

    success: bool
