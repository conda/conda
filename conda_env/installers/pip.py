# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import absolute_import

import os
import os.path as op
import subprocess
import tempfile
from conda.base.context import context
from conda.common.compat import on_win
from conda.utils import wrap_subprocess_call
from conda_env.pip_util import pip_args
from conda.exceptions import CondaValueError


def _pip_install_via_requirements(prefix, specs, args, *_, **kwargs):
    """
    Installs the pip dependencies in specs using a temporary pip requirements file.

    Args
    ----
    prefix: string
      The path to the python and pip executables.

    specs: iterable of strings
      Each element should be a valid pip dependency.
      See: https://pip.pypa.io/en/stable/user_guide/#requirements-files
           https://pip.pypa.io/en/stable/reference/pip_install/#requirements-file-format
    """
    try:
        pip_workdir = op.dirname(op.abspath(args.file))
    except AttributeError:
        pip_workdir = None
    requirements = None
    try:
        # Generate the temporary requirements file
        requirements = tempfile.NamedTemporaryFile(mode='w',
                                                   prefix='condaenv.',
                                                   suffix='.requirements.txt',
                                                   dir=pip_workdir,
                                                   delete=False)
        requirements.write('\n'.join(specs))
        requirements.close()
        # pip command line...
        args, pip_version = pip_args(prefix)
        if args is None:
            return
        script_caller = None
        pip_cmd = args + ['install', '-r', requirements.name]
        cmd = " ".join(pip_cmd)
        script_caller, command_args = wrap_subprocess_call(
            on_win, context.root_prefix, prefix, cmd
        )
        # ...run it
        process = subprocess.Popen(command_args,
                                   cwd=pip_workdir,
                                   universal_newlines=True)
        process.communicate()
        if process.returncode != 0:
            raise CondaValueError("pip returned an error")
    finally:
        # Win/Appveyor does not like it if we use context manager + delete=True.
        # So we delete the temporary file in a finally block.
        if requirements is not None and op.isfile(requirements.name):
            os.remove(requirements.name)
        if script_caller is not None:
            os.remove(script_caller)


# Conform to Installers API
install = _pip_install_via_requirements
