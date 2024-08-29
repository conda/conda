# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
Holds functions for output rendering in conda
"""

from __future__ import annotations

import logging
import sys
from functools import lru_cache
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import ContextManager

from .base.constants import (
    DEFAULT_JSON_REPORTER_BACKEND,
)
from .base.context import context

if TYPE_CHECKING:
    from typing import Callable

    from .plugins.types import ProgressBarBase

logger = logging.getLogger(__name__)


def _get_reporter_backend() -> str:
    """
    Determine the current reporter backend being used
    """
    if context.json:
        backend = DEFAULT_JSON_REPORTER_BACKEND
    else:
        backend = context.console

    return backend


@lru_cache(maxsize=None)
def _get_render_func(style: str | None = None) -> Callable:
    """
    Retrieves the render function to use
    """
    backend = _get_reporter_backend()
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
    backend = _get_reporter_backend()
    reporter = context.plugin_manager.get_reporter_backend(backend)

    return reporter.renderer().progress_bar(description, **kwargs)


def get_progress_bar_context_manager() -> ContextManager:
    """
    Retrieve progress bar context manager to use with registered reporter
    """
    backend = _get_reporter_backend()
    reporter = context.plugin_manager.get_reporter_backend(backend)

    return reporter.renderer().progress_bar_context_manager()
