# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
Holds functions for output rendering in conda
"""

from __future__ import annotations

import logging
import sys
from functools import cache
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from contextlib import AbstractContextManager

from .base.context import context
from .exceptions import CondaSystemExit, DryRunExit

if TYPE_CHECKING:
    from typing import Callable

    from .plugins.types import ProgressBarBase, SpinnerBase

logger = logging.getLogger(__name__)


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


def render(data, style: str | None = None, **kwargs) -> None:
    """
    Used to render output in conda

    The output will either be rendered as "json" or normal "console" output to stdout.
    This function allows us to configure different reporter backends for these two types
    of output.
    """
    render_func = _get_render_func(style)
    data_str = render_func(data, **kwargs)
    sys.stdout.write(data_str)


def get_progress_bar(description: str, **kwargs) -> ProgressBarBase:
    """
    Retrieve the progress bar for the currently configured reporter backend
    """
    return _get_render_func("progress_bar")(description, **kwargs)


def get_progress_bar_context_manager() -> AbstractContextManager:
    """
    Retrieve progress bar context manager to use with registered reporter
    """
    return _get_render_func("progress_bar_context_manager")()


def get_spinner(message: str, fail_message: str = "failed\n") -> SpinnerBase:
    """
    Retrieve spinner to use with registered reporter
    """
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
