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


class StdStreamHandler(StreamHandler):
    """Log StreamHandler that always writes to the current sys stream."""

    terminator = '\n'

    def __init__(self, sys_stream):
        """
        Args:
            sys_stream: stream name, either "stdout" or "stderr" (attribute of module sys)
        """
        super(StdStreamHandler, self).__init__(getattr(sys, sys_stream))
        self.sys_stream = sys_stream
        del self.stream

    def __getattr__(self, attr):
        # always get current sys.stdout/sys.stderr, unless self.stream has been set explicitly
        if attr == 'stream':
            return getattr(sys, self.sys_stream)
        return super(StdStreamHandler, self).__getattribute__(attr)

    def emit(self, record):
        # in contrast to the Python 2.7 StreamHandler, this has no special Unicode handling;
        # however, this backports the Python >=3.2 terminator attribute and additionally makes it
        # further customizable by giving record an identically named attribute, e.g., via
        # logger.log(..., extra={"terminator": ""}) or LoggerAdapter(logger, {"terminator": ""}).
        try:
            msg = self.format(record)
            terminator = getattr(record, "terminator", self.terminator)
            stream = self.stream
            stream.write(msg)
            stream.write(terminator)
            self.flush()
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)


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
    # Set up special loggers 'conda.stdout'/'conda.stderr' which output directly to the
    # corresponding sys streams, filter token urls and don't propagate.
    formatter = Formatter("%(message)s")

    for stream in ('stdout', 'stderr'):
        logger = getLogger('conda.%s' % stream)
        logger.setLevel(INFO)
        handler = StdStreamHandler(stream)
        handler.setLevel(INFO)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.addFilter(TokenURLFilter())
        logger.propagate = False

        stdlog_logger = getLogger('conda.%slog' % stream)
        stdlog_logger.setLevel(DEBUG)
        stdlog_handler = StdStreamHandler(stream)
        stdlog_handler.terminator = ''
        stdlog_handler.setLevel(DEBUG)
        stdlog_handler.setFormatter(formatter)
        stdlog_logger.addHandler(stdlog_handler)
        stdlog_logger.propagate = False

    verbose_logger = getLogger('conda.stdout.verbose')
    verbose_logger.setLevel(INFO)
    verbose_handler = StdStreamHandler('stdout')
    verbose_handler.setLevel(INFO)
    verbose_handler.setFormatter(formatter)
    verbose_logger.addHandler(verbose_handler)
    verbose_logger.propagate = False


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
    # 'requests' loggers get their own handlers so that they always output messages in long format
    # regardless of the level.
    attach_stderr_handler(level, 'requests')
    attach_stderr_handler(level, 'requests.packages.urllib3')


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

# suppress DeprecationWarning for warn method
logging.Logger.warn = logging.Logger.warning
