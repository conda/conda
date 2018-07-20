# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import json
import os
from os.path import abspath, join
import sys
from tempfile import NamedTemporaryFile

from ..base.context import context
from ..common.compat import ensure_binary, iteritems, on_win
from ..gateways.disk.delete import rm_rf
from ..gateways.subprocess import subprocess_call


def get_activated_env_vars():
    env_location = context.target_prefix
    if on_win:
        env_var_map = _get_activated_env_vars_win(env_location)
    else:
        env_var_map = _get_activated_env_vars_unix(env_location)
    env_var_map = {str(k): str(v) for k, v in iteritems(env_var_map)}
    return env_var_map


def _get_activated_env_vars_win(env_location):
    try:
        conda_bat = os.environ["CONDA_BAT"]
    except KeyError:
        conda_bat = abspath(join(sys.prefix, 'condacmd', 'conda.bat'))

    temp_path = None
    try:
        with NamedTemporaryFile('w+b', suffix='.bat', delete=False) as tf:
            temp_path = tf.name
            tf.write(ensure_binary(
                "@%CONDA_PYTHON_EXE% -c \"import os, json; print(json.dumps(dict(os.environ)))\""
            ))
        # TODO: refactor into single function along with code in conda.core.link.run_script
        cmd_builder = [
            "%s" % os.getenv('COMSPEC', 'cmd.exe'),
            "/C \"",
            "@SET PROMPT= ",
            "&&",
            "@SET CONDA_CHANGEPS1=false",
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
        conda_exe = abspath(join(sys.prefix, 'bin', 'conda'))

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


def execute(args, parser):
    from .conda_argparse import _exec
    env_vars = get_activated_env_vars()
    _exec(args.executable_call, env_vars)
