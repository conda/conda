# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
Holds functions for output rendering in conda.

The primary entry point is :func:`get_reporter`, which returns the process-wide
:class:`CondaReporter` singleton.  Calling code emits typed events via
:meth:`CondaReporter.send`; the singleton dispatches each event to the
corresponding ``render_*`` method on the active
:class:`~conda.plugins.types.ReporterRendererBase` implementation.

Module-level helper functions (``get_spinner``, ``render``, ``confirm_yn``, …)
are preserved for backward compatibility.  ``get_progress_bar`` and
``get_progress_bar_context_manager`` are deprecated — migrate to emitting
:class:`~conda.plugins.reporter_backends.events.FetchTask*` events directly.
"""

from __future__ import annotations

import logging
import threading
from contextlib import contextmanager
from typing import TYPE_CHECKING

from .base.context import context
from .exceptions import CondaSystemExit, DryRunExit
from .plugins.reporter_backends.events import (
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
    from contextlib import AbstractContextManager

    from .plugins.reporter_backends.events import RenderEvent
    from .plugins.types import ProgressBarBase, ReporterRendererBase

logger = logging.getLogger(__name__)


class CondaReporter:
    """
    Process-wide singleton that coordinates all output rendering in conda.

    Calling code emits typed events via :meth:`send`; ``CondaReporter``
    dispatches each event to the corresponding ``render_*`` method on the
    active :class:`~conda.plugins.types.ReporterRendererBase`.

    Thread safety: events listed in ``_THREAD_SAFE_EVENTS`` are serialized
    through ``_lock`` before being dispatched to the renderer.  This covers
    fetch-progress events that are emitted concurrently from download threads.
    """

    _DISPATCH: dict[type, str] = {
        # Import is deferred to avoid heavy imports at module load time;
        # the mapping is populated at first instantiation below.
    }
    """Maps each event type to the renderer method that handles it."""

    _THREAD_SAFE_EVENTS: frozenset[type] = frozenset()
    """Events that must be serialized across threads."""

    def __init__(self, renderer: ReporterRendererBase) -> None:
        self._renderer = renderer
        self._lock = threading.Lock()

    def send(self, event: RenderEvent) -> None:
        """Dispatch *event* to the active renderer.

        Unknown event types are silently ignored (logged at DEBUG level) so
        that new events can be introduced without breaking existing renderers.
        """
        method_name = self._DISPATCH.get(type(event))
        if method_name is None:
            logger.debug("unhandled reporter event type: %s", type(event).__name__)
            return
        if type(event) in self._THREAD_SAFE_EVENTS:
            with self._lock:
                getattr(self._renderer, method_name)(event)
        else:
            getattr(self._renderer, method_name)(event)

    def prompt(
        self,
        message: str = "Proceed",
        choices: tuple[str, ...] = ("yes", "no"),
        default: str = "yes",
    ) -> str:
        """Delegate a synchronous prompt to the renderer."""
        return self._renderer.prompt(message, choices, default)


# Populate the dispatch table after all event classes are defined.
from .plugins.reporter_backends.events import (
    DetailViewEvent,
    EnvsListEvent,
)

CondaReporter._DISPATCH = {
    RenderDataEvent: "render_data",
    DetailViewEvent: "render_detail_view",
    EnvsListEvent: "render_envs_list",
    SpinnerStartEvent: "render_spinner_start",
    SpinnerEndEvent: "render_spinner_end",
    FetchSectionStartEvent: "render_fetch_section_start",
    FetchTaskStartEvent: "render_fetch_task_start",
    FetchTaskProgressEvent: "render_fetch_task_progress",
    FetchTaskEndEvent: "render_fetch_task_end",
    FetchSectionEndEvent: "render_fetch_section_end",
}

CondaReporter._THREAD_SAFE_EVENTS = frozenset(
    {
        FetchTaskStartEvent,
        FetchTaskProgressEvent,
        FetchTaskEndEvent,
    }
)


# ---------------------------------------------------------------------------
# Singleton management
# ---------------------------------------------------------------------------

_reporter: CondaReporter | None = None


def get_reporter() -> CondaReporter:
    """Return the process-wide :class:`CondaReporter` singleton.

    The singleton is created lazily on first access using the reporter backend
    configured in :attr:`~conda.base.context.Context.console`.
    """
    global _reporter
    if _reporter is None:
        backend = context.plugin_manager.get_reporter_backend(context.console)
        _reporter = CondaReporter(backend.renderer())
    return _reporter


def reset_reporter() -> None:
    """Clear the singleton so it is re-created on the next :func:`get_reporter` call.

    Called by :func:`~conda.base.context.reset_context` whenever the context
    is reset (e.g. between CLI invocations in tests).
    """
    global _reporter
    _reporter = None


# ---------------------------------------------------------------------------
# Public module-level API (preserved for backward compatibility)
# ---------------------------------------------------------------------------


@contextmanager
def get_spinner(message: str, fail_message: str = "failed\n"):
    """Context manager that displays a spinner for the duration of the block.

    Emits :class:`~conda.plugins.reporter_backends.events.SpinnerStartEvent`
    on entry and :class:`~conda.plugins.reporter_backends.events.SpinnerEndEvent`
    on exit.  The call shape ``with get_spinner("message"):`` is unchanged.
    """
    reporter = get_reporter()
    reporter.send(SpinnerStartEvent(message=message, fail_message=fail_message))
    success = True
    try:
        yield
    except Exception:
        success = False
        raise
    finally:
        reporter.send(SpinnerEndEvent(message=message, success=success))


def render(data, style: str | None = None, **kwargs) -> None:
    """Render *data* to stdout via the active reporter backend.

    Emits the appropriate event based on *style*:

    * ``"detail_view"`` → :class:`~conda.plugins.reporter_backends.events.DetailViewEvent`
    * ``"envs_list"``   → :class:`~conda.plugins.reporter_backends.events.EnvsListEvent`
    * ``None`` or other → :class:`~conda.plugins.reporter_backends.events.RenderDataEvent`
    """
    reporter = get_reporter()
    from .plugins.reporter_backends.events import DetailViewEvent, EnvsListEvent

    if style == "detail_view":
        reporter.send(DetailViewEvent(data=data))
    elif style == "envs_list":
        show_size = kwargs.get("show_size", False)
        prefixes = tuple(data) if not isinstance(data, tuple) else data
        reporter.send(EnvsListEvent(prefixes=prefixes, show_size=show_size))
    else:
        reporter.send(RenderDataEvent(data=data, style=style))


def confirm_yn(message: str = "Proceed", default="yes", dry_run=None) -> bool:
    """Display a "yes/no" confirmation input."""
    if (dry_run is None and context.dry_run) or dry_run:
        raise DryRunExit()

    if context.always_yes:
        return True

    try:
        choice = get_reporter().prompt(message, choices=("yes", "no"), default=default)
    except KeyboardInterrupt:  # pragma: no cover
        raise CondaSystemExit("\nOperation aborted.  Exiting.")

    if choice == "no":
        raise CondaSystemExit("Exiting.")

    return True


# ---------------------------------------------------------------------------
# Deprecated public API — kept for backward compatibility
# ---------------------------------------------------------------------------


def get_progress_bar(description: str, **kwargs) -> ProgressBarBase:
    """Return a progress bar for the active reporter backend.

    .. deprecated:: 25.3
        Use :func:`get_reporter` and emit
        :class:`~conda.plugins.reporter_backends.events.FetchTask*` events
        directly.  Will be removed in 27.9.
    """
    from .deprecations import deprecated

    deprecated.topic(
        "25.3",
        "27.9",
        topic="conda.reporters.get_progress_bar",
        addendum=(
            "Use ``get_reporter().send(FetchTaskStartEvent(...))`` "
            "and related events instead."
        ),
    )
    # Delegate to the renderer's legacy progress_bar() factory so existing
    # callers keep working through the deprecation window.
    backend = context.plugin_manager.get_reporter_backend(context.console)
    renderer = backend.renderer()
    return renderer.progress_bar(description, **kwargs)


def get_progress_bar_context_manager() -> AbstractContextManager:
    """Return the progress-bar context manager for the active backend.

    .. deprecated:: 25.3
        Emit :class:`~conda.plugins.reporter_backends.events.FetchSectionStartEvent`
        and :class:`~conda.plugins.reporter_backends.events.FetchSectionEndEvent`
        instead.  Will be removed in 27.9.
    """
    from .deprecations import deprecated

    deprecated.topic(
        "25.3",
        "27.9",
        topic="conda.reporters.get_progress_bar_context_manager",
        addendum=(
            "Use ``get_reporter().send(FetchSectionStartEvent())`` "
            "and ``FetchSectionEndEvent`` instead."
        ),
    )
    backend = context.plugin_manager.get_reporter_backend(context.console)
    renderer = backend.renderer()
    return renderer.progress_bar_context_manager()
