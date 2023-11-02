# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""DEPRECATED: Use `conda.cli.main_env` instead.

Entry point for all conda-env subcommands.
"""
from conda.cli.main_env import configure_parser, execute  # noqa
from conda.deprecations import deprecated

deprecated.module("23.9", "24.3", addendum="Use `conda.cli.main_env` instead.")

import os
import sys

# pip_util.py import on_win from conda.exports
# conda.exports resets the context
# we need to import conda.exports here so that the context is not lost
# when importing pip (and pip_util)
import conda.exports  # noqa
from conda.base.context import context
from conda.cli.main import init_loggers
from conda.exceptions import conda_exception_handler
from conda.gateways.logging import initialize_logging


def main():
    initialize_logging()
    parser = configure_parser()
    args = parser.parse_args()
    os.environ["CONDA_AUTO_UPDATE_CONDA"] = "false"
    context.__init__(argparse_args=args)
    init_loggers()
    return conda_exception_handler(execute, args, parser)


if __name__ == "__main__":
    sys.exit(main())
