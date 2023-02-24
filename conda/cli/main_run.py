# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause


import os

from ..base.context import context
from ..utils import wrap_exec_call
from ..common.compat import encode_environment
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

    # run script, replacing conda python process
    os.execvpe(
        file=call_args[0],
        args=call_args,
        env=encode_environment(os.environ),
    )
