# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
Defines the default reporter stream for conda that renders output to stdout

It is essentially a proxy to the ``sys.stdout`` object.
"""

import sys
from contextlib import contextmanager
from typing import TextIO

from .. import CondaReporterStream, hookimpl


@contextmanager
def stdout_io() -> TextIO:
    yield sys.stdout


@hookimpl
def conda_reporter_streams():
    """
    Reporter stream for stdout
    """
    yield CondaReporterStream(
        name="stdout",
        description="Default implementation of a reporter stream that acts as a proxy to "
        "``sys.stdout.write``",
        stream=stdout_io,
    )
