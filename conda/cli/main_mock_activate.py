# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Mock CLI implementation for `conda activate`.

A mock implementation of the activate shell command for better UX.
"""
from .. import CondaError


def execute(args, parser):
    raise CondaError("Run 'conda init' before 'conda activate'")
