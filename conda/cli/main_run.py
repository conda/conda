# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause


import os

from ..base.context import context
from ..utils import wrap_exec_call, on_win
from .common import validate_prefix


def execute(args, parser):

    # create run script
    _, call_args = wrap_exec_call(
        context.root_prefix,
        validate_prefix(context.target_prefix or os.getenv("CONDA_PREFIX") or context.root_prefix),
        args.dev,
        args.debug_wrapper_scripts,
        args.executable_call,
    )

    if args.cwd:
        os.chdir(args.cwd)

    if on_win:
        # fork process - os.exec* does not work as expected in Windows
        return os.spawnv(
            os.P_WAIT,
            call_args[0],
            call_args,
        )
    else:
        # exec process, replacing conda python process completely
        os.execvp(
            file=call_args[0],
            args=call_args,
        )
