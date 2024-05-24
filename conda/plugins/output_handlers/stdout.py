# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
Defines the default output handler for conda which renders output to stdout
It is essentially a proxy to the ``sys.stdout`` object.
"""

import sys
from contextlib import contextmanager
from typing import TextIO

from .. import CondaOutputHandler, hookimpl


@contextmanager
def stdout_io() -> TextIO:
    yield sys.stdout


@hookimpl
def conda_output_handlers():
    """
    Output handler for stdout
    This is a default output handler provided by conda and writes the renderables it
    receives to stdout using the ``sys`` module.
    """
    yield CondaOutputHandler(
        name="stdout",
        description="Default implementation of a output handler that acts as a proxy to "
        "``sys.stdout.write``",
        get_output_io=stdout_io,
    )
