# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Clean path plugins for ``conda clean``."""

from __future__ import annotations

from . import notices

plugins = [notices]

__all__ = ["plugins"]
