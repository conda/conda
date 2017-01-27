# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from collections import namedtuple
from logging import getLogger
import os
from os.path import abspath
from shlex import split as shlex_split
from subprocess import CalledProcessError, PIPE, Popen
import sys

from .compat import ensure_binary, ensure_text_type, iteritems, on_win, string_types, isiterable

log = getLogger(__name__)
Response = namedtuple('Response', ('stdout', 'stderr', 'rc'))


def _split_on_unix(command):
    # I guess windows doesn't like shlex.split
    return command if on_win else shlex_split(command)


def subprocess_call(command, env=None, path=None, stdin=None, raise_on_error=True):
    env = {str(k): str(v) for k, v in iteritems(iteritems(env) if env else os.environ)}
    path = sys.prefix if path is None else abspath(path)
    p = Popen(_split_on_unix(command) if isinstance(command, string_types) else command,
              cwd=path, stdin=PIPE, stdout=PIPE, stderr=PIPE, env=env)
    stdin = ensure_binary(stdin) if isinstance(stdin, string_types) else None
    stdout, stderr = p.communicate(input=stdin)
    rc = p.returncode
    log.debug("{0} $  {1}\n"
              "  stdout: {2}\n"
              "  stderr: {3}\n"
              "  rc: {4}"
              .format(path, ' '.join(command) if isiterable(command) else command,
                      stdout, stderr, rc))
    if raise_on_error and rc != 0:
        raise CalledProcessError(rc, command, "stdout: {0}\nstderr: {1}".format(stdout, stderr))
    return Response(ensure_text_type(stdout), ensure_text_type(stderr), int(rc))
