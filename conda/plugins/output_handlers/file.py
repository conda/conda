# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
Defines the default output handler for conda which renders output to a file
"""

import logging
from datetime import datetime
from typing import Any

from .. import CondaOutputHandler, hookimpl
from ..types import OutputRenderer

logger = logging.getLogger(__name__)

#: Current timestamp used for file name
TIMESTAMP = int(datetime.now().timestamp())

#: Filename for log file
CONDA_LOG_FILENAME = f"conda-{TIMESTAMP}.log"


class FileRenderer(OutputRenderer):
    def __call__(self, renderable: str, **kwargs: Any) -> None:
        try:
            with open(CONDA_LOG_FILENAME, "a") as fp:
                fp.write(renderable)
        except (OSError, TypeError) as exc:
            logger.error(f"Unable to create file: {exc}")


@hookimpl
def conda_output_handlers():
    """
    Output handler for stdout

    This is a default output handler provided by conda and writes the renderables it
    receives to stdout using the ``sys`` module.
    """
    render = FileRenderer()

    yield CondaOutputHandler(
        name="file",
        description="Default implementation of a output handler that writes to a file",
        render=render,
    )
