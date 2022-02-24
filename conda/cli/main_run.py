# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from __future__ import absolute_import, division, print_function, unicode_literals

import logging
import os
import sys

from ..base.context import context
from ..utils import wrap_subprocess_call
from ..gateways.disk.delete import rm_rf
from ..common.compat import encode_environment
from ..gateways.subprocess import subprocess_call
from .common import validate_prefix
from ..common.path import get_path_dirs

log = logging.getLogger(__name__)


def execute(args, parser):
    # remove the base environment's bin/script directory from the PATH env var
    env = os.environ.copy()
    prefix = env.get("CONDA_ROOT")
    if prefix:
        path_dirs = tuple(get_path_dirs(prefix))
        old_path = env.get("PATH", "").split(os.pathsep)
        new_path = [item for item in old_path if item not in path_dirs]
        env["PATH"] = os.pathsep.join(new_path)

    # create run script
    script, command = wrap_subprocess_call(
        context.root_prefix,
        validate_prefix(context.target_prefix or os.getenv("CONDA_PREFIX") or context.root_prefix),
        args.dev,
        args.debug_wrapper_scripts,
        args.executable_call,
        path=env["PATH"],
        use_system_tmp_path=True,
    )
    # actually call the command
    response = subprocess_call(
        command,
        env=encode_environment(env),
        path=args.cwd,
        raise_on_error=False,
        capture_output=not args.no_capture_output,
        live_stream=args.live_stream,
    )
    if response.rc != 0:
        log.error(f"`conda run {' '.join(args.executable_call)}` failed. (See above for error)")

    # remove script
    if "CONDA_TEST_SAVE_TEMPS" not in os.environ:
        rm_rf(script)
    else:
        log.warning(f"CONDA_TEST_SAVE_TEMPS :: retaining main_run script {script}")

    if not args.live_stream:
        if response.stdout:
            print(response.stdout, file=sys.stdout)
        if response.stderr:
            print(response.stderr, file=sys.stderr)

    return response
