# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
Holds functions for output rendering in conda
"""

from __future__ import annotations

import logging
import sys

from .base.constants import (
    DEFAULT_CONSOLE_REPORTER_BACKEND,
    DEFAULT_JSON_REPORTER_BACKEND,
)
from .base.context import context
from .exceptions import CondaError

logger = logging.getLogger(__name__)


def render(data, style: str | None = None, **kwargs) -> None:
    """
    Used to render output in conda

    The output will either be rendered as "json" or normal "console" output to stdout.
    This function allows us to configure different reporter backends for these two types
    of output.
    """
    if context.json is True:
        backend = DEFAULT_JSON_REPORTER_BACKEND
    elif isinstance(context.json, str):
        backend = context.json
    else:
        backend = context.console

    reporter = context.plugin_manager.get_reporter_backend(backend)

    if reporter is None:
        logger.warning(
            f'Unable to find reporter backend: "{backend}"; '
            f'falling back to using "{DEFAULT_CONSOLE_REPORTER_BACKEND}"'
        )
        reporter = context.plugin_manager.get_reporter_backend(
            DEFAULT_CONSOLE_REPORTER_BACKEND
        )

        if reporter is None:
            raise CondaError(
                "There are no available reporter backends to render output. This conda installation"
                " is most likely corrupt and requires a re-installation."
            )

    renderer = reporter.renderer()

    if style is not None:
        render_func = getattr(renderer, style, None)
        if render_func is None:
            raise AttributeError(f"'{style}' is not a valid reporter backend style")
    else:
        render_func = getattr(renderer, "render")

    data_str = render_func(data, **kwargs)

    sys.stdout.write(data_str)
