# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Expose conda version."""

from .. import hookimpl
from ..types import CondaVirtualPackage


@hookimpl
def conda_virtual_packages():
    from ... import __version__

    yield CondaVirtualPackage("conda", __version__, None)
