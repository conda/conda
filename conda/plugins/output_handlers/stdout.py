# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
Defines the default output handler for conda which renders output to stdout

It is essentially a proxy to the ``sys.stdout.write`` function.
"""

import sys
from typing import Any

from .. import CondaOutputHandler, hookimpl
from ..types import OutputRenderer


class StdoutRender(OutputRenderer):
    def __call__(self, renderable: str, **kwargs: Any) -> None:
        sys.stdout.write(renderable)


@hookimpl
def conda_output_handlers():
    """
    Output handler for stdout

    This is a default output handler provided by conda and writes the renderables it
    receives to stdout using the ``sys`` module.
    """
    render = StdoutRender()

    yield CondaOutputHandler(
        name="stdout",
        description="Default implementation of a output handler that acts as a proxy to "
        "``sys.stdout.write``",
        render=render,
    )
