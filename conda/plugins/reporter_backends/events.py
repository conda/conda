# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
Typed event dataclasses for the conda reporter event system.

This module is the canonical registry of every reportable event in conda.
All events are frozen dataclasses — immutable and safe to pass across threads.

Renderers respond to events by implementing ``render_*`` methods on
:class:`~conda.plugins.types.ReporterRendererBase`.  The dispatcher
(:class:`~conda.reporters.CondaReporter`) maps each event type to its
corresponding renderer method via a static dispatch table.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any


# ---------------------------------------------------------------------------
# Output events
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RenderDataEvent:
    """Generic data-render event.

    Args:
        data: The data to render.
        style: Optional renderer style name (e.g. ``"detail_view"``,
            ``"envs_list"``).  ``None`` means plain string rendering.
    """

    data: Any
    style: str | None = None


@dataclass(frozen=True)
class DetailViewEvent:
    """Render a key/value mapping as a tabular detail view.

    Args:
        data: Mapping of header strings to primitive values.
    """

    data: dict[str, str | int | bool]


@dataclass(frozen=True)
class EnvsListEvent:
    """Render a list of conda environments.

    Args:
        prefixes: Tuple of path strings or ``PrefixData`` objects.
        show_size: Whether to include disk-size column.
    """

    prefixes: tuple
    show_size: bool = False


# ---------------------------------------------------------------------------
# Spinner events
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SpinnerStartEvent:
    """Signal that a spinner (indeterminate progress indicator) should start.

    Args:
        message: Label shown next to the spinner.
        fail_message: Text appended when the operation fails.
    """

    message: str
    fail_message: str = "failed\n"


@dataclass(frozen=True)
class SpinnerEndEvent:
    """Signal that the active spinner should stop.

    Args:
        message: Must match the ``message`` of the corresponding
            :class:`SpinnerStartEvent`.
        success: ``True`` if the guarded operation completed without error.
    """

    message: str
    success: bool


# ---------------------------------------------------------------------------
# Fetch / extract pipeline events
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FetchSectionStartEvent:
    """Signal that a fetch-and-extract section is beginning.

    Renderers use this to set up any shared layout context (e.g. a
    ``rich.progress.Progress`` group) before individual task events arrive.
    """


@dataclass(frozen=True)
class FetchTaskStartEvent:
    """Signal that a single package fetch task is starting.

    Args:
        task_id: Caller-supplied identifier, typically ``id(prec_or_spec)``.
            Must be unique within the enclosing fetch section.
        name: Package name.
        version: Package version string.
        size: Download size in bytes, or ``None`` if unknown.
    """

    task_id: int
    name: str
    version: str
    size: int | None


@dataclass(frozen=True)
class FetchTaskProgressEvent:
    """Report progress on an in-flight fetch task.

    Args:
        task_id: Must match a previously emitted :class:`FetchTaskStartEvent`.
        fraction: Completion fraction in the range ``[0.0, 1.0]``.
    """

    task_id: int
    fraction: float


@dataclass(frozen=True)
class FetchTaskEndEvent:
    """Signal that a fetch (and optional extract) task has completed.

    Args:
        task_id: Must match a previously emitted :class:`FetchTaskStartEvent`.
        success: ``True`` if the task completed without error.
    """

    task_id: int
    success: bool


@dataclass(frozen=True)
class FetchSectionEndEvent:
    """Signal that the fetch-and-extract section has finished.

    Args:
        success: ``True`` if all tasks completed without error.
    """

    success: bool


# ---------------------------------------------------------------------------
# RenderEvent — union type alias for type annotations
# ---------------------------------------------------------------------------

RenderEvent = (
    RenderDataEvent
    | DetailViewEvent
    | EnvsListEvent
    | SpinnerStartEvent
    | SpinnerEndEvent
    | FetchSectionStartEvent
    | FetchTaskStartEvent
    | FetchTaskProgressEvent
    | FetchTaskEndEvent
    | FetchSectionEndEvent
)
