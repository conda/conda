# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
Common utilities for the ng CLI layer.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rich.console import Console


def create_console(*args, **kwargs) -> Console:
    """
    Create a :class:`rich.console.Console` instance that respects standard
    terminal output-mode environment variables.

    The following variables are honoured (in precedence order):

    * ``TERM=dumb`` or ``TERM=unknown`` – disables *all* ANSI escape codes
      (colour, bold, underline, animations).  Rich handles this natively; we
      do not override it.
    * ``NO_COLOR`` (see https://no-color.org/) – disables color only; non-color
      formatting such as bold and underline may still appear.  We pass
      ``no_color=True`` to Rich explicitly to make the intent clear.
    * ``FORCE_COLOR`` – enables Rich markup even when stdout is **not** a TTY
      (useful for CI pipelines that capture coloured output).
    * TTY detection via ``sys.stdout.isatty()`` – the default Rich behaviour.

    Additional keyword arguments are forwarded to :class:`rich.console.Console`.
    In non-TTY contexts the ``width`` is set to a very large value to prevent
    Rich from line-wrapping output intended for downstream processing.
    """
    from rich.console import Console

    from conda.common.io import force_color, is_tty, no_color, term_dumb

    kwargs.setdefault("soft_wrap", True)

    if "force_terminal" not in kwargs:
        if term_dumb():
            # TERM=dumb: Rich already disables all escape codes natively when
            # it reads TERM from the environment.  We do not pass no_color=True
            # here because that only suppresses colour while still emitting
            # bold/underline codes, which a dumb terminal cannot render.
            pass
        elif no_color():
            # NO_COLOR: suppress colour only; bold/underline are still allowed.
            kwargs.setdefault("no_color", True)
        elif force_color():
            # FORCE_COLOR: enable Rich markup even in non-TTY contexts.
            # Rich respects this automatically since v13.3.3, but we keep the
            # explicit override for older versions and clarity.
            kwargs.setdefault("force_terminal", True)

    # Disable line-wrapping in non-interactive contexts so that piped / CI
    # output is not truncated.
    if not is_tty():
        kwargs.setdefault("width", 100_000)

    return Console(*args, **kwargs)


def export_rich_renderable(*objects) -> str:
    """
    Serialize Rich renderables (or plain strings) to plain text.

    Uses :func:`create_console` so that ``NO_COLOR`` / ``FORCE_COLOR`` /
    ``TERM=dumb`` are all respected automatically.
    """
    console = create_console(record=True)
    with console.capture() as capture:
        console.print(*objects)
    return capture.get()
