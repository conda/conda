# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import re
import sys
from functools import partial
from logging import DEBUG, ERROR, Filter, Formatter, INFO, StreamHandler, WARN, getLogger, Logger

from ..common.io import attach_stderr_handler

log = getLogger(__name__)


class TokenURLFilter(Filter):
    TOKEN_URL_PATTERN = re.compile(
        r'(|https?://)'  # \1  scheme
        r'(|\s'  # \2  space, or
        r'|(?:(?:\d{1,3}\.){3}\d{1,3})'  # ipv4, or
        r'|(?:'  # domain name
        r'(?:[a-zA-Z0-9-]{1,20}\.){0,10}'  # non-tld
        r'(?:[a-zA-Z]{2}[a-zA-Z0-9-]{0,18})'  # tld
        r'))'  # end domain name
        r'(|:\d{1,5})?'  # \3  port
        r'/t/[a-z0-9A-Z-]+/'  # token
    )
    TOKEN_REPLACE = partial(TOKEN_URL_PATTERN.sub, r'\1\2\3/t/<TOKEN>/')

    def filter(self, record):
        record.msg = self.TOKEN_REPLACE(record.msg)
        return True


def initialize_logging():
    initialize_root_logger()
    initialize_conda_logger()

    formatter = Formatter("%(message)s\n")

    stdout = getLogger('stdout')
    stdout.setLevel(INFO)
    stdouthandler = StreamHandler(sys.stdout)
    stdouthandler.setLevel(INFO)
    stdouthandler.setFormatter(formatter)
    stdout.addHandler(stdouthandler)
    stdout.addFilter(TokenURLFilter())
    stdout.propagate = False

    stderr = getLogger('stderr')
    stderr.setLevel(INFO)
    stderrhandler = StreamHandler(sys.stderr)
    stderrhandler.setLevel(INFO)
    stderrhandler.setFormatter(formatter)
    stderr.addHandler(stderrhandler)
    stderr.addFilter(TokenURLFilter())
    stderr.propagate = False


def initialize_root_logger(level=ERROR):
    attach_stderr_handler(level)


def initialize_conda_logger(level=WARN):
    attach_stderr_handler(level, 'conda')


def set_all_logger_level(level=DEBUG):
    attach_stderr_handler(level)
    attach_stderr_handler(level, 'conda')
    attach_stderr_handler(level, 'binstar')
    attach_stderr_handler(level, 'requests')
    attach_stderr_handler(level, 'requests.packages.urllib3')


def set_verbosity(verbosity_level):
    if verbosity_level == 0:
        return
    elif verbosity_level == 1:
        set_all_logger_level(INFO)
        return
    elif verbosity_level == 2:
        set_all_logger_level(DEBUG)
        return
    else:
        from conda import CondaError
        raise CondaError("Invalid verbosity level: %s", verbosity_level)
