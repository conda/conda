# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Pip-flavored installer."""

import os
import os.path as op
from logging import getLogger

from ...auxlib.compat import Utf8NamedTemporaryFile
from ...common.path import expand, is_path, paths_equal
from ...common.url import is_url
from ...env.pip_util import get_pip_installed_packages, get_pip_workdir, pip_subprocess
from ...reporters import get_spinner

log = getLogger(__name__)


def install(prefix, specs, args, *_, workdir=None, requirements_sources=None, **kwargs):
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

    requirements_sources: list[tuple[list[str], str | None]] | None, optional
      Pip requirements grouped by source file workdir. When present, conda writes
      one temporary requirements file and passes it to one pip subprocess so pip
      resolves all specs together.
    """

    with get_spinner("Installing pip dependencies"):
        if requirements_sources:
            source_workdirs = {
                expand(source_workdir)
                for _, source_workdir in requirements_sources
                if source_workdir
            }
            if workdir is None and len(source_workdirs) == 1:
                workdir = source_workdirs.pop()

            pip_specs = []
            for source_specs, source_workdir in requirements_sources:
                normalize_paths = source_workdir and not (
                    workdir and paths_equal(source_workdir, workdir)
                )
                for spec in source_specs:
                    if not normalize_paths:
                        pip_specs.append(spec)
                        continue

                    for option in ("--editable", "--requirement", "--constraint"):
                        option_prefix = f"{option}="
                        if spec.startswith(option_prefix):
                            path = spec.removeprefix(option_prefix)
                            if (
                                not is_url(path)
                                and not op.isabs(path)
                                and (option != "--editable" or is_path(path))
                            ):
                                path = expand(op.join(source_workdir, path))
                            spec = f"{option_prefix}{path}"
                            break
                    else:
                        option, separator, path = spec.partition(" ")
                        if separator and option in {"-e", "--editable"}:
                            if (
                                not is_url(path)
                                and not op.isabs(path)
                                and is_path(path)
                            ):
                                path = expand(op.join(source_workdir, path))
                            spec = f"{option} {path}"
                        elif separator and option in {
                            "-r",
                            "--requirement",
                            "-c",
                            "--constraint",
                        }:
                            if not is_url(path) and not op.isabs(path):
                                path = expand(op.join(source_workdir, path))
                            spec = f"{option} {path}"
                        elif not is_url(spec) and not op.isabs(spec) and is_path(spec):
                            spec = expand(op.join(source_workdir, spec))
                    pip_specs.append(spec)
            specs = pip_specs
        elif workdir is None:
            workdir = get_pip_workdir(args.file)

        requirements = None
        try:
            with Utf8NamedTemporaryFile(
                mode="w",
                prefix="condaenv.",
                suffix=".requirements.txt",
                dir=workdir,
                delete=False,
            ) as requirements:
                requirements.write("\n".join(specs))
            # pip command line...
            # see https://pip.pypa.io/en/stable/cli/pip/#exists-action-option
            pip_cmd = ["install", "-U", "-r", requirements.name, "--exists-action=b"]
            stdout, stderr = pip_subprocess(pip_cmd, prefix, cwd=workdir)
        finally:
            # Win/Appveyor does not like delete=True here, so remove it explicitly.
            if requirements is not None and op.isfile(requirements.name):
                if "CONDA_TEST_SAVE_TEMPS" not in os.environ:
                    os.remove(requirements.name)
                else:
                    log.warning(
                        "CONDA_TEST_SAVE_TEMPS :: retaining pip requirements.txt %s",
                        requirements.name,
                    )
        return get_pip_installed_packages(stdout)
