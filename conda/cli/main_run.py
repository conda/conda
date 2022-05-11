# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from __future__ import absolute_import, division, print_function, unicode_literals

from logging import getLogger
import os
import sys

from ..base.context import context
from ..utils import wrap_subprocess_call
from ..gateways.disk.delete import rm_rf
from ..common.compat import encode_environment
from ..gateways.subprocess import subprocess_call
from .common import validate_prefix


def execute(args, parser):
    # create run script
    script, command = wrap_subprocess_call(
        context.root_prefix,
        validate_prefix(context.target_prefix or os.getenv("CONDA_PREFIX") or context.root_prefix),
        args.dev,
        args.debug_wrapper_scripts,
        args.executable_call,
        use_system_tmp_path=True,
    )

    # run script
    response = subprocess_call(
        command,
        env=encode_environment(os.environ.copy()),
        path=args.cwd,
        raise_on_error=False,
        capture_output=not args.no_capture_output,
        live_stream=args.live_stream,
    )
    if response.rc != 0:
        log = getLogger(__name__)
        log.error(f"`conda run {' '.join(args.executable_call)}` failed. (See above for error)")

    # remove script
    if "CONDA_TEST_SAVE_TEMPS" not in os.environ:
        rm_rf(script)
    else:
        log = getLogger(__name__)
        log.warning(f"CONDA_TEST_SAVE_TEMPS :: retaining main_run script {script}")

    if not args.live_stream:
        if response.stdout:
            print(response.stdout, file=sys.stdout)
        if response.stderr:
            print(response.stderr, file=sys.stderr)

    return response
