# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
Defines the default reporter output for conda that renders output to stdout

It is essentially a proxy to the ``sys.stdout`` object.
"""

import sys
from contextlib import contextmanager
from typing import TextIO

from .. import CondaReporterOutput, hookimpl


@contextmanager
def stdout_io() -> TextIO:
    yield sys.stdout


@hookimpl
def conda_reporter_outputs():
    """
    Reporter stream for stdout
    """
    yield CondaReporterOutput(
        name="stdout",
        description="Default implementation of a reporter output that acts as a proxy to "
        "``sys.stdout.write``",
        stream=stdout_io,
    )
