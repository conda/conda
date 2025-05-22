# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Installer for conda packages from a direct reference (e.g. by a URL)."""

from ...direct import direct


def install(prefix, specs, args, env, *_, **kwargs):
    """Install packages into an environment"""
    return direct(specs, prefix)
