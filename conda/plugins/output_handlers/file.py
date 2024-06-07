# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
Defines the default output handler for conda which renders output to a file
"""

import logging
from contextlib import contextmanager
from datetime import datetime
from typing import TextIO

from .. import CondaOutputHandler, hookimpl

logger = logging.getLogger(__name__)

#: Current timestamp used for file name
TIMESTAMP = int(datetime.now().timestamp())

#: Filename for log file
CONDA_LOG_FILENAME = f"conda-{TIMESTAMP}.log"


@contextmanager
def file_io() -> TextIO:
    try:
        with open(CONDA_LOG_FILENAME, "a") as fp:
            yield fp
    except (OSError, TypeError) as exc:
        logger.error(f"Unable to create file: {exc}")


@hookimpl
def conda_output_handlers():
    """
    Output handler for stdout

    This is a default output handler provided by conda and writes the renderables it
    receives to stdout using the ``sys`` module.
    """
    yield CondaOutputHandler(
        name="file",
        description="Default implementation of a output handler that writes to a file",
        get_output_io=file_io,
    )
