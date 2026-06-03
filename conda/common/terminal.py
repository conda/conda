# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
Utility functions for terminal output.
"""

import os
import sys


def is_tty() -> bool:
    """Return True if stdout is connected to a TTY."""
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


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
    """
    return "NO_COLOR" in os.environ


def force_color() -> bool:
    """
    Return True when color output should be forced even in non-TTY contexts.

    Respects the ``FORCE_COLOR`` environment variable when it is set to a
    non-empty value.
    """
    return bool(os.environ.get("FORCE_COLOR"))


def should_use_color() -> bool:
    """
    Determine whether ANSI color output should be produced.

    The precedence order (highest to lowest) is:

    1. ``NO_COLOR`` set -> no color.
    2. non-empty ``FORCE_COLOR`` set -> color even in non-TTY.
    3. ``TERM=dumb``/``TERM=unknown`` -> no color.
    4. stdout is a TTY -> color.
    5. Otherwise -> no color.
    """
    if no_color():
        return False
    if force_color():
        return True
    if term_dumb():
        return False
    return is_tty()
