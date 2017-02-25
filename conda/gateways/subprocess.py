# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from collections import namedtuple
from logging import getLogger
import os
from os.path import abspath
from shlex import split as shlex_split
from subprocess import CalledProcessError, PIPE, Popen
import sys

from .logging import TRACE
from .. import ACTIVE_SUBPROCESSES
from .._vendor.auxlib.ish import dals
from ..common.compat import ensure_binary, ensure_text_type, iteritems, on_win, string_types

log = getLogger(__name__)
Response = namedtuple('Response', ('stdout', 'stderr', 'rc'))


def _split_on_unix(command):
    # I guess windows doesn't like shlex.split
    return command if on_win else shlex_split(command)


def _format_output(command_str, path, rc, stdout, stderr):
    return dals("""
    $ %s
    ==> cwd: %s <==
    ==> exit code: %d <==
    ==> stdout <==
    %s
    ==> stderr <==
    %s
    """) % (command_str, path, rc, stdout, stderr)


def subprocess_call(command, env=None, path=None, stdin=None, raise_on_error=True):
    """This utility function should be preferred for all conda subprocessing.
    It handles multiple tricky details.
    """
    env = {str(k): str(v) for k, v in iteritems(env if env else os.environ)}
    path = sys.prefix if path is None else abspath(path)
    command_str = command if isinstance(command, string_types) else ' '.join(command)
    command_arg = _split_on_unix(command) if isinstance(command, string_types) else command
    log.debug("executing>> %s", command_str)
    p = Popen(command_arg, cwd=path, stdin=PIPE, stdout=PIPE, stderr=PIPE, env=env)
    ACTIVE_SUBPROCESSES.add(p)
    stdin = ensure_binary(stdin) if isinstance(stdin, string_types) else None
    stdout, stderr = p.communicate(input=stdin)
    rc = p.returncode
    ACTIVE_SUBPROCESSES.remove(p)
    if raise_on_error and rc != 0:
        log.info(_format_output(command_str, path, rc, stdout, stderr))
        raise CalledProcessError(rc, command,
                                 output=_format_output(command_str, path, rc, stdout, stderr))
    if log.isEnabledFor(TRACE):
        log.trace(_format_output(command_str, path, rc, stdout, stderr))

    return Response(ensure_text_type(stdout), ensure_text_type(stderr), int(rc))
