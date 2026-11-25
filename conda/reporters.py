# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
Holds functions for output rendering in conda
"""

from __future__ import annotations

import logging
import sys
import warnings
from contextlib import contextmanager
from functools import cache
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from contextlib import AbstractContextManager

from .base.context import context
from .deprecations import deprecated
from .exceptions import CondaSystemExit, DryRunExit
from .plugins.reporter_backends.events import (
    DetailViewEvent,
    EnvsListEvent,
    RenderDataEvent,
    SpinnerEndEvent,
    SpinnerStartEvent,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from typing import Any

    from .plugins.reporter_backends.events import Event
    from .plugins.types import ProgressBarBase, ReporterRendererBase, SpinnerBase

logger = logging.getLogger(__name__)


class CondaReporter:
    """
    Dispatches events to one or more reporter renderers.

    Every event is sent to each registered renderer in registration order. This
    allows, for example, rendering to stdout, a log file and telemetry at once.
    An exception raised by one renderer is logged and does not prevent the
    remaining renderers from receiving the event.

    Args:
        *renderers: Renderers to register initially.
    """

    def __init__(self, *renderers: ReporterRendererBase):
        self._renderers: list[ReporterRendererBase] = list(renderers)

    @property
    def renderers(self) -> tuple[ReporterRendererBase, ...]:
        """
        The registered renderers, in registration order.
        """
        return tuple(self._renderers)

    def add_renderer(self, renderer: ReporterRendererBase) -> None:
        """
        Register another renderer to receive all subsequent events.

        Args:
            renderer: The renderer to add.
        """
        self._renderers.append(renderer)

    def send(self, event: Event) -> None:
        """
        Send an event to the
        :meth:`~conda.plugins.types.ReporterRendererBase.handle` method of every
        registered renderer.

        Args:
            event: The event to dispatch.
        """
        for renderer in self._renderers:
            try:
                renderer.handle(event)
            except Exception:
                logger.exception(
                    "%s failed to handle %s",
                    type(renderer).__name__,
                    type(event).__name__,
                )


_reporter: CondaReporter | None = None


def get_reporter() -> CondaReporter:
    """
    Return the :class:`CondaReporter` for the currently configured reporter backend.
    """
    global _reporter
    if _reporter is None:
        backend = context.plugin_manager.get_reporter_backend(context.console)
        _reporter = CondaReporter(backend.renderer())
    return _reporter


def reset_reporter() -> None:
    """
    Discard the cached :class:`CondaReporter` so it is rebuilt on next use.
    """
    global _reporter
    _reporter = None


@contextmanager
def spinner(message: str, fail_message: str = "failed\n") -> Iterator[None]:
    """
    Show a spinner for the duration of the ``with`` block.

    Sends a :class:`~conda.plugins.reporter_backends.events.SpinnerStartEvent` on entry
    and a :class:`~conda.plugins.reporter_backends.events.SpinnerEndEvent` on exit.

    Args:
        message: Label shown next to the spinner.
        fail_message: Text shown if the block raises.
    """
    reporter = get_reporter()
    reporter.send(SpinnerStartEvent(message=message, fail_message=fail_message))
    success = False
    try:
        yield
        success = True
    finally:
        reporter.send(SpinnerEndEvent(message=message, success=success))


def render_data(
    data: Any, style: str | None = None, *, show_size: bool = False
) -> None:
    """
    Render data to stdout through the active reporter backend.

    Args:
        data: The data to render.
        style: ``"detail_view"`` or ``"envs_list"`` select a specialised view; anything
            else renders ``data`` as-is. An ``"envs_list"`` mapping is also rendered
            as-is, since it is already structured data (e.g. ``conda info --json``).
        show_size: Include a size column. Only used by the ``"envs_list"`` style.

    Raises:
        AttributeError: If ``style`` is not a known reporter backend style.
    """
    reporter = get_reporter()
    match style:
        case "detail_view":
            reporter.send(DetailViewEvent(data=data))
        case "envs_list" if isinstance(data, dict):
            # ``conda info --json`` passes a pre-built mapping rather than prefixes
            reporter.send(RenderDataEvent(data=data))
        case "envs_list":
            reporter.send(EnvsListEvent(prefixes=tuple(data), show_size=show_size))
        case None:
            reporter.send(RenderDataEvent(data=data))
        case _:
            raise AttributeError(f"'{style}' is not a valid reporter backend style")


@contextmanager
def _legacy_renderer_warnings_suppressed() -> Iterator[None]:
    """
    Silence deprecation warnings from the legacy renderer methods.

    The deprecated functions in this module already warn once per call, so the legacy
    renderer methods they delegate to should not warn a second time.
    """
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", PendingDeprecationWarning)
        warnings.simplefilter("ignore", DeprecationWarning)
        yield


@cache
def _get_render_func(style: str | None = None) -> Callable:
    """
    Retrieves the render function to use
    """
    backend = context.console
    reporter = context.plugin_manager.get_reporter_backend(backend)

    renderer = reporter.renderer()

    if style is not None:
        render_func = getattr(renderer, style, None)
        if render_func is None:
            raise AttributeError(f"'{style}' is not a valid reporter backend style")
    else:
        render_func = getattr(renderer, "render")

    return render_func


@deprecated(
    "27.3",
    "27.9",
    addendum="Use `conda.reporters.render_data` instead.",
)
def render(data, style: str | None = None, **kwargs) -> None:
    """
    Used to render output in conda

    The output will either be rendered as "json" or normal "console" output to stdout.
    This function allows us to configure different reporter backends for these two types
    of output.
    """
    render_func = _get_render_func(style)
    with _legacy_renderer_warnings_suppressed():
        data_str = render_func(data, **kwargs)
    sys.stdout.write(data_str)


@deprecated(
    "27.3",
    "27.9",
    addendum="Send `FetchTaskStartEvent`, `FetchTaskProgressEvent` and `FetchTaskEndEvent` with `get_reporter().send()` instead.",
)
def get_progress_bar(description: str, **kwargs) -> ProgressBarBase:
    """
    Retrieve the progress bar for the currently configured reporter backend
    """
    with _legacy_renderer_warnings_suppressed():
        return _get_render_func("progress_bar")(description, **kwargs)


@deprecated(
    "27.3",
    "27.9",
    addendum="Send `FetchSectionStartEvent` and `FetchSectionEndEvent` with `get_reporter().send()` instead.",
)
def get_progress_bar_context_manager() -> AbstractContextManager:
    """
    Retrieve progress bar context manager to use with registered reporter
    """
    with _legacy_renderer_warnings_suppressed():
        return _get_render_func("progress_bar_context_manager")()


@deprecated(
    "27.3",
    "27.9",
    addendum="Use `conda.reporters.spinner` instead.",
)
def get_spinner(message: str, fail_message: str = "failed\n") -> SpinnerBase:
    """
    Retrieve spinner to use with registered reporter
    """
    with _legacy_renderer_warnings_suppressed():
        return _get_render_func("spinner")(message, fail_message)


def confirm_yn(message: str = "Proceed", default="yes", dry_run=None) -> bool:
    """
    Display a "yes/no" confirmation input
    """
    if (dry_run is None and context.dry_run) or dry_run:
        raise DryRunExit()

    if context.always_yes:
        return True

    try:
        choice = _get_render_func("prompt")(
            message, choices=("yes", "no"), default=default
        )

    except KeyboardInterrupt:  # pragma: no cover
        raise CondaSystemExit("\nOperation aborted.  Exiting.")

    if choice == "no":
        raise CondaSystemExit("Exiting.")

    return True
