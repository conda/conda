# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""CLI implementation for `conda install`.

Installs the specified packages into an existing environment.
"""
import sys

from ..base.context import context
from ..notices import notices
from .install import install


@notices
def execute(args, parser):
    if context.force:
        print(
            "\n\n"
            "WARNING: The --force flag will be removed in a future conda release.\n"
            "         See 'conda install --help' for details about the --force-reinstall\n"
            "         and --clobber flags.\n"
            "\n",
            file=sys.stderr,
        )

    install(args, parser, "install")
