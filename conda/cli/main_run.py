# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import json
import os
from os.path import isfile, join
from subprocess import Popen
import sys
from tempfile import NamedTemporaryFile

from .. import CondaError
from ..base.context import context
from ..common.compat import ensure_binary, iteritems, on_win
from ..exceptions import CommandNotFoundError
from ..gateways.disk.delete import rm_rf
from ..gateways.subprocess import subprocess_call


class ExecutableNotFound(CondaError):

    def __init__(self, target_prefix, executable_name):
        message = ("The executable was not found in the target prefix.\n"
                   "  target prefix: %(target_prefix)s\n"
                   "  executable name: %(executable_name)s"
                   )
        super(ExecutableNotFound, self).__init__(message, target_prefix=target_prefix,
                                                 executable_name=executable_name)


def _get_activated_env_vars_win(env_location):
    try:
        conda_bat = os.environ["CONDA_BAT"]
    except KeyError:
        raise CommandNotFoundError("run")

    temp_path = None
    try:
        with NamedTemporaryFile('w+b', suffix='.bat', delete=False) as tf:
            temp_path = tf.name
            tf.write(ensure_binary(
                "@%CONDA_PYTHON_EXE% -c \"import os, json; print(json.dumps(dict(os.environ)))\""
            ))
        cmd_builder = [
            "cmd.exe /K \"",
            "@SET PROMPT= ",
            "&&",
            "@SET CONDA_CHANGEPS1=false"
            "&&",
            "@CALL {0} activate \"{1}\"".format(conda_bat, env_location),
            "&&",
            "\"{0}\"".format(tf.name),
            "\"",
        ]
        cmd = " ".join(cmd_builder)
        result = subprocess_call(cmd)
    finally:
        if temp_path:
            rm_rf(temp_path)

    assert not result.stderr, result.stderr
    env_var_map = json.loads(result.stdout)
    return env_var_map


def _get_activated_env_vars_unix(env_location):
    try:
        conda_exe = os.environ["CONDA_EXE"]
    except KeyError:
        raise CommandNotFoundError("run")

    cmd_builder = [
        "sh -c \'"
        "eval \"$(\"{0}\" shell.posix hook)\"".format(conda_exe),
        "&&",
        "conda activate \"{0}\"".format(env_location),
        "&&",
        "\"$CONDA_PYTHON_EXE\" -c \"import os, json; print(json.dumps(dict(os.environ)))\"",
        "\'",
    ]
    cmd = " ".join(cmd_builder)
    result = subprocess_call(cmd)
    assert not result.stderr, result.stderr
    env_var_map = json.loads(result.stdout)
    return env_var_map


def get_activated_env_vars():
    env_location = context.target_prefix
    if on_win:
        in_posix_like_shell = os.getenv('TEMP', os.getenv('TMP', '')).startswith('/')
        if in_posix_like_shell:
            env_var_map = _get_activated_env_vars_unix(env_location)
        else:
            env_var_map = _get_activated_env_vars_win(env_location)
    else:
        env_var_map = _get_activated_env_vars_unix(env_location)
    env_var_map = {str(k): str(v) for k, v in iteritems(env_var_map)}
    return env_var_map


def find_executable(executable_name):
    target_prefix = context.target_prefix
    if on_win:
        executable_path = _find_executable_win(target_prefix, executable_name)
    else:
        executable_path = _find_executable_unix(target_prefix, executable_name)
    if executable_path is None:
        raise ExecutableNotFound(target_prefix, executable_name)
    return executable_path


def _find_executable_win(target_prefix, executable_name):
    from ..activate import _Activator
    pathext = os.environ["PATHEXT"].split(';')
    if executable_name.endswith(pathext):
        for path_dir in _Activator._get_path_dirs(target_prefix):
            executable_path = join(path_dir, executable_name)
            if isfile(executable_path):
                return executable_path
    else:
        for path_dir in _Activator._get_path_dirs(target_prefix):
            for ext in pathext:
                executable_path = join(path_dir, executable_name + ext)
                if isfile(executable_path):
                    return executable_path
    return None


def _find_executable_unix(target_prefix, executable_name):
    executable_path = join(target_prefix, 'bin', executable_name)
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


if __name__ == "__main__":
    print(get_activated_env_vars())
