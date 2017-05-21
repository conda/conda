# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from functools import partial
import logging
from logging import DEBUG, ERROR, Filter, Formatter, INFO, StreamHandler, WARN, getLogger
import re
import sys

from .. import CondaError
from .._vendor.auxlib.decorators import memoize
from ..common.io import attach_stderr_handler

log = getLogger(__name__)
TRACE = 5  # TRACE LOG LEVEL
VERBOSITY_LEVELS = (WARN, INFO, DEBUG, TRACE)


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


# Don't use initialize_logging/initialize_root_logger/set_conda_log_level in
# cli.python_api! There we want the user to have control over their logging,
# e.g., using their own levels, handlers, formatters and propagation settings.

@memoize
def initialize_logging():
    # root gets level ERROR; 'conda' gets level WARN and propagates to root.
    initialize_root_logger()
    set_conda_log_level()
    initialize_std_loggers()


@memoize
def initialize_std_loggers():
    # Set up special loggers 'stdout'/'stderr' which output directly to the corresponding
    # sys streams, filter token urls and don't propagate.
    # TODO: To avoid clashes with user loggers when cli.python_api is used, these loggers
    #       should most likely be renamed to 'conda.stdout'/'conda.stderr' in the future!
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


def set_conda_log_level(level=WARN):
    conda_logger = getLogger('conda')
    conda_logger.setLevel(level)
    conda_logger.propagate = True  # let root logger's handler format/output message


def set_all_logger_level(level=DEBUG):
    formatter = Formatter("%(message)s\n") if level >= INFO else None
    attach_stderr_handler(level, formatter=formatter)
    set_conda_log_level(level)  # only set level and use root's handler/formatter
    # 'requests' logger gets its own handler, to ouput messages in long format regardless of level
    attach_stderr_handler(level, 'requests')


def set_verbosity(verbosity_level):
    try:
        set_all_logger_level(VERBOSITY_LEVELS[verbosity_level])
    except IndexError:
        raise CondaError("Invalid verbosity level: %(verbosity_level)s",
                         verbosity_level=verbosity_level)
    log.debug("verbosity set to %s", verbosity_level)


def trace(self, message, *args, **kwargs):
    if self.isEnabledFor(TRACE):
        self._log(TRACE, message, args, **kwargs)


logging.addLevelName(TRACE, "TRACE")
logging.Logger.trace = trace
