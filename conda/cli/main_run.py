# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import json
import os
from os.path import abspath, join

import sys

from ..base.context import context
from ..common.compat import encode_environment, on_win, ensure_binary
from .common import is_valid_prefix


def execute_win(args, parser):
    from logging import getLogger
    from ..utils import wrap_subprocess_call
    from ..gateways.subprocess import subprocess_call
    from ..gateways.disk.delete import rm_rf

    log = getLogger(__name__)

    call = args.executable_call
    cwd = args.cwd or os.getcwd()
    prefix = context.target_prefix or os.getenv("CONDA_PREFIX") or context.root_prefix
    is_valid_prefix(prefix)

    script_caller, command_args = wrap_subprocess_call(on_win, context.root_prefix, prefix,
                                                       args.dev, args.debug_wrapper_scripts, call)
    env = encode_environment(os.environ.copy())

    response = subprocess_call(command_args, env=env, path=cwd, raise_on_error=False)
    if response.rc != 0:
        log.error("Subprocess for 'conda run {}' command failed.  (See above for error)"
                  .format(call))
    if script_caller is not None:
        if 'CONDA_TEST_SAVE_TEMPS' not in os.environ:
            rm_rf(script_caller)
        else:
            log.warning('CONDA_TEST_SAVE_TEMPS :: retaining main_run script_caller {}'.format(
                script_caller))
    if response.stdout:
        print(response.stdout, file=sys.stdout)
    if response.stderr:
        print(response.stderr, file=sys.stderr)
    return response


def execute(args, parser):
    if on_win:
        return execute_win(args, parser)

    from .conda_argparse import _exec

    if args.cwd:
        os.chdir(args.cwd)

    env_vars = get_activated_env_vars()

    if context.verbosity >= 2:
        print(json.dumps(
            env_vars, sort_keys=True, indent=2, separators=(',', ': '), ensure_ascii=False
        ), file=sys.stderr)
    _exec(args.executable_call, env_vars)


def get_activated_env_vars():
    env_location = context.target_prefix
    if on_win:
        env_var_map = _get_activated_env_vars_win(env_location)
    else:
        env_var_map = _get_activated_env_vars_unix(env_location)
    env_var_map = {str(k): str(v) for k, v in env_var_map.items()}
    return env_var_map


def _get_activated_env_vars_win(env_location):
    from tempfile import NamedTemporaryFile
    try:
        conda_bat = os.environ["CONDA_BAT"]
    except KeyError:
        conda_bat = abspath(join(sys.prefix, 'condabin', 'conda.bat'))

    temp_path = None
    try:
        with NamedTemporaryFile('w+b', suffix='.bat', delete=False) as tf:
            temp_path = tf.name
            tf.write(ensure_binary(
                "@%CONDA_PYTHON_EXE% -c \"import os, json; print(json.dumps(dict(os.environ)))\""
            ))
        # TODO: refactor into single function along with code in conda.core.link.run_script
        inner_builder = (
            "@SET PROMPT= ",
            "&&",
            "@SET CONDA_CHANGEPS1=false",
            "&&",
            "@CALL {0} activate \"{1}\"".format(conda_bat, env_location),
            "&&",
            "\"{0}\"".format(tf.name),
        )
        cmd = "{0} /C \"{1}\"".format(os.getenv('COMSPEC', 'cmd.exe'), " ".join(inner_builder))
        stdout = _check_output(cmd)
    finally:
        if temp_path:
            from ..gateways.disk.delete import rm_rf
            rm_rf(temp_path)

    env_var_map = json.loads(stdout)
    return env_var_map


def _get_activated_env_vars_unix(env_location):
    try:
        conda_exe = os.environ["CONDA_EXE"]
    except KeyError:
        conda_exe = abspath(join(sys.prefix, 'bin', 'conda'))
    if conda_exe[-6:] == "python" or conda_exe[-10:] == "python.exe":
        # We have `CONDA_EXE` set to just python in some activation integration tests.
        # In that case we're assuming that the conda module is somewhere on sys.path.
        conda_exe += "\" \"-m\" \"conda"

    inner_builder = (
        "eval \"$(\"{0}\" \"shell.posix\" \"hook\")\"".format(conda_exe),
        "&&",
        "conda activate \"{0}\"".format(env_location),
        "&&",
        "\"$CONDA_PYTHON_EXE\" -c \"import os, json; print(json.dumps(dict(os.environ)))\"",
    )
    cmd = ("sh", "-c", " ".join(inner_builder))
    env_var_map = json.loads(_check_output(cmd))
    return env_var_map


def _check_output(cmd):
    import subprocess
    if context.verbosity >= 2:
        print(cmd, file=sys.stderr)
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = p.communicate()
    rc = p.returncode
    assert rc == 0 and not stderr, (rc, stderr)
    return stdout
