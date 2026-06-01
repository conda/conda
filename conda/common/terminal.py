# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
Utility functions for terminal output.
"""

import os
import sys


def is_tty() -> bool:
    """Return True if both stdin and stdout are connected to a TTY."""
    return (
        hasattr(sys.stdout, "isatty")
        and sys.stdout.isatty()
        and hasattr(sys.stdin, "isatty")
        and sys.stdin.isatty()
    )


def term_dumb() -> bool:
    """
    Return True when ``TERM`` indicates a non-capable terminal.

    ``TERM=dumb`` is the widely-followed terminfo convention for terminals
    that cannot render any ANSI escape sequences (color, bold, animations).
    ``TERM=unknown`` is treated the same way as a defensive fallback.
    """
    return os.environ.get("TERM") in ("dumb", "unknown")


def no_color() -> bool:
    """
    Return True when *color* output should be suppressed.

    Respects the ``NO_COLOR`` standard (https://no-color.org/): color is
    suppressed when the ``NO_COLOR`` environment variable is set to any value.
    Non-color ANSI formatting (bold, underline, etc.) may still be used.

    Note: ``TERM=dumb`` also implies no color, but it additionally disables
    *all* escape codes — use :func:`term_dumb` to check that condition.
    """
    return "NO_COLOR" in os.environ or term_dumb()


def force_color() -> bool:
    """
    Return True when color output should be forced even in non-TTY contexts.

    Respects the ``FORCE_COLOR`` environment variable (used by many CI
    systems and tools such as pytest).
    """
    return "FORCE_COLOR" in os.environ


def should_use_color() -> bool:
    """
    Determine whether ANSI color output should be produced.

    The precedence order (highest to lowest) is:

    1. ``NO_COLOR`` set or ``TERM=dumb``/``TERM=unknown`` → no color.
    2. ``FORCE_COLOR`` set → color even in non-TTY.
    3. stdout is a TTY → color.
    4. Otherwise → no color.
    """
    if no_color():
        return False
    if force_color():
        return True
    return is_tty()
