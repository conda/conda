# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Placeholder for the actual version code injected by hatch-vcs.

The logic here is used during development installs only so keep it simple. Since conda
abides by CEP-8, which outlines using CalVer, our development version is simply:
    YY.MM.MICRO.devN+gHASH[.dirty]
"""
try:
    from setuptools_scm import get_version

    __version__ = get_version(root="..", relative_to=__file__)
except (ImportError, OSError):
    # ImportError: setuptools_scm isn't installed
    # OSError: git isn't installed
    __version__ = "0.0.0.dev0+placeholder"
