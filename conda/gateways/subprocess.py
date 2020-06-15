# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import absolute_import, division, print_function, unicode_literals

from collections import namedtuple
from logging import getLogger
import os
from os.path import abspath
from conda._vendor.auxlib.compat import shlex_split_unicode
import sys
from subprocess import CalledProcessError, PIPE, Popen
from threading import Thread
from ..utils import wrap_subprocess_call

from .logging import TRACE
from .. import ACTIVE_SUBPROCESSES
from .._vendor.auxlib.ish import dals
from ..common.compat import (ensure_binary, string_types, StringIO, encode_arguments,
                             on_win, PY3, encode_environment, isiterable)
from ..gateways.disk.delete import rm_rf
from ..base.context import context

log = getLogger(__name__)
Response = namedtuple('Response', ('stdout', 'stderr', 'rc'))


def _format_output(command_str, cwd, rc, stdout, stderr):
    return dals("""
    $ %s
    ==> cwd: %s <==
    ==> exit code: %d <==
    ==> stdout <==
    %s
    ==> stderr <==
    %s
    """) % (command_str, cwd, rc, stdout, stderr)


def any_subprocess(args, prefix, env=None, cwd=None):
    script_caller, command_args = wrap_subprocess_call(
        on_win, context.root_prefix, prefix, context.dev, context.verbosity >= 2, args)
    process = Popen(command_args,
                    cwd=cwd or prefix,
                    universal_newlines=False,
                    stdout=PIPE, stderr=PIPE, env=env)
    stdout, stderr = process.communicate()
    if script_caller is not None:
        if 'CONDA_TEST_SAVE_TEMPS' not in os.environ:
            rm_rf(script_caller)
        else:
            log.warning('CONDA_TEST_SAVE_TEMPS :: retaining pip run_script {}'.format(
                script_caller))
    if hasattr(stdout, 'decode'):
        stdout = stdout.decode('utf-8', errors='replace')
    if hasattr(stderr, 'decode'):
        stderr = stderr.decode('utf-8', errors='replace')
    return stdout, stderr, process.returncode


def write_process_output_to_stream(p, source, target):
    out = StringIO()

    def start_streaming():
        while p.poll() is None:
            data = source.readline().decode('utf-8')
            target.write(data)
            target.flush()
            out.write(data)
            out.flush()

    th = Thread(target=start_streaming)
    if PY3:
        th.daemon = True
    th.start()
    return out


def subprocess_call(command, env=None, path=None, stdin=None, raise_on_error=True,
                    stdout=PIPE, stderr=PIPE):
    """This utility function should be preferred for all conda subprocessing.
    It handles multiple tricky details.
    """
    env = encode_environment(env if env else os.environ)
    cwd = sys.prefix if path is None else abspath(path)
    if not isiterable(command):
        command = shlex_split_unicode(command)
    command_str = command if isinstance(command, string_types) else ' '.join(command)
    log.debug("executing>> %s", command_str)
    stdin = ensure_binary(stdin) if isinstance(stdin, string_types) else stdin
    p = Popen(encode_arguments(command), cwd=cwd, stdin=stdin, stdout=PIPE,
              stderr=PIPE, env=env)
    ACTIVE_SUBPROCESSES.add(p)
    if stdout == PIPE:
        stdout, stderr = p.communicate()
        if hasattr(stdout, "decode"):
            stdout = stdout.decode('utf-8', errors='replace')
        if hasattr(stderr, "decode"):
            stderr = stderr.decode('utf-8', errors='replace')
    else:
        # If we're redirecting output, then do so and capture it into another stream.
        out_stream = write_process_output_to_stream(p, p.stdout, sys.stdout)
        err_stream = write_process_output_to_stream(p, p.stderr, sys.stderr)
        p.wait()
        stdout, stderr = out_stream.getvalue(), err_stream.getvalue()

    rc = p.returncode
    ACTIVE_SUBPROCESSES.remove(p)
    if (raise_on_error and rc != 0) or log.isEnabledFor(TRACE):
        formatted_output = _format_output(command_str, cwd, rc, stdout, stderr)
    if raise_on_error and rc != 0:
        log.info(formatted_output)
        raise CalledProcessError(rc, command,
                                 output=formatted_output)
    if log.isEnabledFor(TRACE):
        log.trace(formatted_output)

    return Response(stdout, stderr, int(rc))


def _subprocess_clean_env(env, clean_python=True, clean_conda=True):
    dels = []
    if clean_python:
        dels.extend(('PYTHONPATH', 'PYTHONHOME'))
    if clean_conda:
        dels.extend(('CONDA_ROOT', 'CONDA_PROMPT_MODIFIER',
                     'CONDA_EXE', 'CONDA_DEFAULT_ENV'))
    for key in dels:
        if key in env:
            del env[key]


def subprocess_call_with_clean_env(command, path=None, stdin=None, raise_on_error=True,
                                   clean_python=True, clean_conda=True):
    # Any of these env vars are likely to mess the whole thing up.
    # This has been seen to be the case with PYTHONPATH.
    env = os.environ.copy()
    _subprocess_clean_env(env, clean_python, clean_conda)
    # env['CONDA_DLL_SEARCH_MODIFICATION_ENABLE'] = '1'
    return subprocess_call(command, env=env, path=path, stdin=stdin, raise_on_error=raise_on_error)
