# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from conda import CondaError
from logging import WARN, getLogger, ERROR, DEBUG, Logger, INFO

from ..common.io import attach_stderr_handler

log = getLogger(__name__)


def initialize_logging():
    initialize_root_logger()
    initialize_conda_logger()


def initialize_root_logger(level=ERROR):
    attach_stderr_handler(level)


def initialize_conda_logger(level=WARN):
    attach_stderr_handler(level, 'conda')


def set_all_logger_level(level=DEBUG):
    initialize_root_logger(level)
    initialize_conda_logger(level)

    # enable all registered loggers
    for logger in Logger.manager.loggerDict:
        getLogger(logger).setLevel(level)
        log.debug("enabling %s", logger)


def set_verbosity(level):
    if level == 0:
        return
    elif level == 1:
        set_all_logger_level(INFO)
        return
    elif level == 2:
        set_all_logger_level(DEBUG)
        return
    else:
        raise CondaError("Invalid verbosity level: %s", level)
