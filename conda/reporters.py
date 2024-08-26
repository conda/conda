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

from .base.constants import (
    DEFAULT_JSON_REPORTER_BACKEND,
)
from .base.context import context

if TYPE_CHECKING:
    from typing import Callable

logger = logging.getLogger(__name__)


@lru_cache
def _get_render_func(style: str | None = None) -> Callable:
    """
    Retrieves the render function to use
    """
    if context.json:
        backend = DEFAULT_JSON_REPORTER_BACKEND
    else:
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