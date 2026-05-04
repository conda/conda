# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
Common utilities for the ng CLI layer.
"""

from __future__ import annotations

from rich.console import Console


class CondaConsole(Console):
    """A :class:`rich.console.Console` that honours ``NO_COLOR``,
    ``FORCE_COLOR`` and ``TERM=dumb`` / ``TERM=unknown``.

    The following variables are honoured (in precedence order):

    * ``TERM=dumb`` or ``TERM=unknown`` – Rich disables all ANSI escape codes
      natively when it reads ``TERM`` from the environment; we don't override.
    * ``NO_COLOR`` (https://no-color.org/) – disables color only; bold and
      underline may still appear.
    * ``FORCE_COLOR`` – enables Rich markup even when stdout is not a TTY.
    * TTY detection via ``sys.stdout.isatty()`` – the default Rich behaviour.

    In non-TTY contexts the ``width`` is set to a very large value so piped /
    CI output isn't line-wrapped.
    """

    def __init__(self, *args, soft_wrap: bool = True, **kwargs) -> None:
        from conda.common.io import force_color, is_tty, no_color, term_dumb

        if "force_terminal" not in kwargs:
            if term_dumb():
                pass  # Rich disables escape codes natively for TERM=dumb
            elif no_color():
                kwargs.setdefault("no_color", True)
            elif force_color():
                kwargs.setdefault("force_terminal", True)

        if not is_tty():
            kwargs.setdefault("width", 100_000)

        super().__init__(*args, soft_wrap=soft_wrap, **kwargs)

    def to_text(self, *objects) -> str:
        """Render Rich renderables (or plain strings) to a plain string."""
        with self.capture() as capture:
            self.print(*objects)
        return capture.get()
