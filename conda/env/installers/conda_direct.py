# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Installer for conda packages from a direct reference (e.g. by a URL)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ...direct import direct

if TYPE_CHECKING:
    from ...direct import DirectPackages


def install(prefix: str, specs: DirectPackages, *_, **kwargs):
    """Install packages into an environment"""
    return direct(specs, prefix)
