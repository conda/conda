# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from argparse import ArgumentParser, Namespace


def execute(args: Namespace, parser: ArgumentParser) -> bool:
    parser.parse_args(["env", "config", "vars", "--help"])

    # return success
    return True
