# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
Defines the default output handler for conda that renders output to stdout

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
    """
    yield CondaOutputHandler(
        name="stdout",
        description="Default implementation of a output handler that acts as a proxy to "
        "``sys.stdout.write``",
        get_output_io=stdout_io,
    )
