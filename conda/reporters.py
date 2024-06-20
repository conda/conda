# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
Holds functions for output rendering in conda
"""

from __future__ import annotations

from .base.context import context


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
