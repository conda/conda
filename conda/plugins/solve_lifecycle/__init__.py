# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Built-in solve lifecycle hook registrations (use entry points for more)."""

from .reporter_bridge import builtin_solve_lifecycle_reporter_bridge

plugins = [builtin_solve_lifecycle_reporter_bridge]
"""The list of solve-lifecycle plugins for easier registration with pluggy."""
