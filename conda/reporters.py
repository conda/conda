# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
Holds functions for output rendering in conda
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import ContextManager

from .base.context import context
from .plugins.types import ProgressBarBase


def render(data, style: str | None = None, **kwargs) -> None:
    for settings in context.reporters:
        reporter = context.plugin_manager.get_reporter_backend(settings.get("backend"))
        output = context.plugin_manager.get_reporter_output(settings.get("output"))

        if reporter is None or output is None:
            continue

        renderer = reporter.renderer()

        if style is not None:
            render_func = getattr(renderer, style, None)
            if render_func is None:
                raise AttributeError(f"'{style}' is not a valid reporter backend style")
        else:
            render_func = getattr(renderer, "render")

        data_str = render_func(data, **kwargs)

        with output.stream() as file:
            file.write(data_str)


class ProgressBarManager(ProgressBarBase):
    """
    Used to proxy calls to the registered reporter handler progress bar instances
    """

    def __init__(self, progress_bars):
        self._progress_bars = progress_bars

    def update_to(self, fraction) -> None:
        for progress_bar in self._progress_bars:
            progress_bar.update_to(fraction)

    def close(self) -> None:
        for progress_bar in self._progress_bars:
            progress_bar.close()

    def refresh(self) -> None:
        for progress_bar in self._progress_bars:
            progress_bar.refresh()


def get_progress_bar_manager(description: str, **kwargs) -> ProgressBarManager:
    progress_bars = []

    for settings in context.reporters:
        reporter = context.plugin_manager.get_reporter_backend(settings.get("backend"))
        output = context.plugin_manager.get_reporter_output(settings.get("output"))
        progress_bar = reporter.renderer().progress_bar(
            description, output.stream(), settings=settings, **kwargs
        )

        progress_bars.append(progress_bar)

    return ProgressBarManager(progress_bars)


def get_progress_bar_context_managers() -> list[ContextManager]:
    """
    Retrieve all progress bar context managers to use with registered reporters
    """
    context_managers = []

    for settings in context.reporters:
        output = context.plugin_manager.get_reporter_output(settings.get("output"))
        context_managers.append(output.stream())

    return context_managers
