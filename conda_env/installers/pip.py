# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import absolute_import

import os
import os.path as op
from conda.auxlib.compat import Utf8NamedTemporaryFile
from conda.gateways.connection.session import CONDA_SESSION_SCHEMES
from conda_env.pip_util import pip_subprocess, get_pip_installed_packages
from conda.common.io import Spinner
from conda.base.context import context
from logging import getLogger


log = getLogger(__name__)


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
    url_scheme = args.file.split("://", 1)[0]
    if url_scheme in CONDA_SESSION_SCHEMES:
        pip_workdir = None
    else:
        try:
            pip_workdir = op.dirname(op.abspath(args.file))
        except AttributeError:
            pip_workdir = None
    requirements = None
    try:
        # Generate the temporary requirements file
        requirements = Utf8NamedTemporaryFile(mode='w',
                                              prefix='condaenv.',
                                              suffix='.requirements.txt',
                                              dir=pip_workdir,
                                              delete=False)
        requirements.write('\n'.join(specs))
        requirements.close()
        # pip command line...
        pip_cmd = ['install', '-U', '-r', requirements.name]
        stdout, stderr = pip_subprocess(pip_cmd, prefix, cwd=pip_workdir)
    finally:
        # Win/Appveyor does not like it if we use context manager + delete=True.
        # So we delete the temporary file in a finally block.
        if requirements is not None and op.isfile(requirements.name):
            if 'CONDA_TEST_SAVE_TEMPS' not in os.environ:
                os.remove(requirements.name)
            else:
                log.warning('CONDA_TEST_SAVE_TEMPS :: retaining pip requirements.txt {}'
                            .format(requirements.name))
    return get_pip_installed_packages(stdout)


def install(*args, **kwargs):
    with Spinner("Installing pip dependencies",
                 not context.verbosity and not context.quiet,
                 context.json):
        return _pip_install_via_requirements(*args, **kwargs)
