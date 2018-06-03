# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import json
import os
from os.path import isfile, join
from subprocess import Popen
import sys

from ..base.context import context
from ..common.compat import on_win, iteritems
from ..gateways.subprocess import subprocess_call

# OLD conda-run help
"""
$ python -m conda run --help
usage: __main__.py run [-h] [-n ENVIRONMENT | -p PATH] [-q] [--json]
                       [--offline]
                       [COMMAND] [ARGUMENTS [ARGUMENTS ...]]

Launches an application installed with conda.

To include command line options in a command, separate the command from the
other options with --, like

    conda run -- ipython --matplotlib

Options:

positional arguments:
  COMMAND               Package to launch.
  ARGUMENTS             Additional arguments to application.

optional arguments:
  -h, --help            Show this help message and exit.
  -n ENVIRONMENT, --name ENVIRONMENT
                        Name of environment (in
                        /Users/kfranz/continuum/conda/devenv/envs).
  -p PATH, --prefix PATH
                        Full path to environment prefix (default:
                        /Users/kfranz/continuum/conda/devenv/envs/base).
  -q, --quiet           Do not display progress bar.
  --json                Report all output as json. Suitable for using conda
                        programmatically.
  --offline             Offline mode, don't connect to the Internet.

Examples:

    conda run ipython-notebook
"""

def get_activated_env_vars():
    env_location = context.target_prefix
    cmd_builder = []
    if on_win:
        conda_bat = os.environ["CONDA_BAT"]
        # TODO: currently requires shell=True with Popen; fix
        cmd_builder += [
            "CALL \"{0}\" activate \"{1}\"".format(conda_bat, env_location),
            "&&",
            "%CONDA_PYTHON_EXE% -c \"import os, json; print(json.dumps(dict(os.environ)))\"",
        ]
    else:
        conda_exe = os.environ["CONDA_EXE"]
        cmd_builder += [
            "sh -c \'"
            "eval \"$(\"{0}\" shell.posix hook)\"".format(conda_exe),
            "&&",
            "conda activate {0}".format(env_location),
            "&&",
            "\"$CONDA_PYTHON_EXE\" -c \"import os, json; print(json.dumps(dict(os.environ)))\"",
            "\'",
        ]

    cmd = " ".join(cmd_builder)

    result = subprocess_call(cmd)
    assert not result.stderr
    env_var_map = json.loads(result.stdout)
    env_var_map = {str(k): str(v) for k, v in iteritems(env_var_map)}
    return env_var_map


def find_executable(executable_name):
    if on_win:
        executable_path = _find_executable_win(executable_name)
    else:
        executable_path = _find_executable_unix(executable_name)
    if executable_path is None:
        raise ExecutableNotFound()
    return executable_path


def _find_executable_win(executable_name):
    from ..activate import _Activator
    pathext = os.environ["PATHEXT"].split(';')
    if executable_name.endswith(pathext):
        for path_dir in _Activator._get_path_dirs(context.target_prefix):
            executable_path = join(path_dir, executable_name)
            if isfile(executable_path):
                return executable_path
    else:
        for path_dir in _Activator._get_path_dirs(context.target_prefix):
            for ext in pathext:
                executable_path = join(path_dir, executable_name + ext)
                if isfile(executable_path):
                    return executable_path
    return None


def _find_executable_unix(executable_name):
    executable_path = join(context.target_prefix, 'bin', executable_name)
    if isfile(executable_path) and os.access(executable_path, os.X_OK):
        return executable_path
    return None


def _exec_win(executable_path, extra_args=(), env_vars=None):
    env_vars = os.environ.copy() if env_vars is None else env_vars
    args = [executable_path]
    args.extend(extra_args)
    p = Popen(args, env=env_vars)
    try:
        p.communicate()
    except KeyboardInterrupt:
        p.wait()
    finally:
        sys.exit(p.returncode)


def _exec_unix(executable_path, extra_args=(), env_vars=None):
    env_vars = os.environ.copy() if env_vars is None else env_vars
    args = [executable_path]
    args.extend(extra_args)
    os.execve(executable_path, args, env_vars)


def execute(args, parser):
    executable_path = find_executable(args.executable_name)
    env_vars = get_activated_env_vars()
    if on_win:
        _exec_win(executable_path, args.extra_args, env_vars)
    else:
        _exec_unix(executable_path, args.extra_args, env_vars)



