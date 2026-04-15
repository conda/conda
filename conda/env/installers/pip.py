# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Pip-flavored installer."""

import os
import os.path as op
from logging import getLogger

from ...auxlib.compat import Utf8NamedTemporaryFile
from ...env.pip_util import get_pip_installed_packages, get_pip_workdir, pip_subprocess
from ...reporters import get_spinner

log = getLogger(__name__)


# NOTE: *_ absorbs env from callers. Required for interface consistency with
# other installers—do not remove; callers use the same pattern for all types.
def _pip_install_via_requirements(prefix, specs, args, *_, workdir=None, **kwargs):
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

    workdir: str | None, optional
      Working directory for resolving relative paths in specs (e.g. -e ./local_pkg).
      Caller should derive from the environment file path. None for URLs or when
      no file path is available.
    """

    if workdir is None:
        workdir = get_pip_workdir(args.file)

    requirements = None
    try:
        # Generate the temporary requirements file
        requirements = Utf8NamedTemporaryFile(
            mode="w",
            prefix="condaenv.",
            suffix=".requirements.txt",
            dir=workdir,
            delete=False,
        )
        requirements.write("\n".join(specs))
        requirements.close()
        # pip command line...
        # see https://pip.pypa.io/en/stable/cli/pip/#exists-action-option
        pip_cmd = ["install", "-U", "-r", requirements.name, "--exists-action=b"]
        stdout, stderr = pip_subprocess(pip_cmd, prefix, cwd=workdir)
    finally:
        # Win/Appveyor does not like it if we use context manager + delete=True.
        # So we delete the temporary file in a finally block.
        if requirements is not None and op.isfile(requirements.name):
            if "CONDA_TEST_SAVE_TEMPS" not in os.environ:
                os.remove(requirements.name)
            else:
                log.warning(
                    "CONDA_TEST_SAVE_TEMPS :: retaining pip requirements.txt %s",
                    requirements.name,
                )
    return get_pip_installed_packages(stdout)


def install(*args, **kwargs):
    with get_spinner("Installing pip dependencies"):
        return _pip_install_via_requirements(*args, **kwargs)
