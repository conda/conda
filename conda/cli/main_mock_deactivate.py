# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Mock CLI implementation for `conda deactivate`.

A mock implementation of the deactivate shell command for better UX.
"""


def execute(args, parser):
    print("ERROR: Run 'conda init' before 'conda deactivate'")
