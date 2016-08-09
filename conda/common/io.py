# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import logging
import sys
from contextlib import contextmanager
from logging import CRITICAL, Formatter, NOTSET, StreamHandler, WARN, getLogger

from .._vendor.auxlib.logz import NullHandler
from ..compat import StringIO

log = getLogger(__name__)

_FORMATTER = Formatter("%(levelname)s %(name)s:%(funcName)s(%(lineno)d): %(message)s")


@contextmanager
def captured():
    class CapturedText(object):
        pass
    saved_stdout, saved_stderr = sys.stdout, sys.stderr
    sys.stdout = outfile = StringIO()
    sys.stderr = errfile = StringIO()
    c = CapturedText()
    log.info("overtaking stderr and stdout")
    try:
        yield c
    finally:
        c.stdout, c.stderr = outfile.getvalue(), errfile.getvalue()
        sys.stdout, sys.stderr = saved_stdout, saved_stderr
        log.info("stderr and stdout yielded back")


@contextmanager
def argv(args_list):
    saved_args = sys.argv
    sys.argv = args_list
    try:
        yield
    finally:
        sys.argv = saved_args


@contextmanager
def _logger_lock():
    logging._acquireLock()
    try:
        yield
    finally:
        logging._releaseLock()


@contextmanager
def disable_logger(logger_name):
    logr = getLogger(logger_name)
    _hndlrs, _lvl, _dsbld, _prpgt = logr.handlers, logr.level, logr.disabled, logr.propagate
    with _logger_lock():
        logr.addHandler(NullHandler())
        logr.setLevel(CRITICAL + 1)
        logr.disabled, logr.propagate = True, False
    try:
        yield
    finally:
        with _logger_lock():
            logr.handlers, logr.level, logr.disabled = _hndlrs, _lvl, _dsbld
            logr.propagate = _prpgt


@contextmanager
def stderr_log_level(level, logger_name=None):
    logr = getLogger(logger_name)
    _hndlrs, _lvl, _dsbld, _prpgt = logr.handlers, logr.level, logr.disabled, logr.propagate
    handler = StreamHandler(sys.stderr)
    handler.name = 'stderr'
    handler.setLevel(level)
    handler.setFormatter(_FORMATTER)
    with _logger_lock():
        logr.setLevel(level)
        logr.handlers, logr.disabled, logr.propagate = [], False, False
        logr.addHandler(handler)
        logr.setLevel(level)
    try:
        yield
    finally:
        with _logger_lock():
            logr.handlers, logr.level, logr.disabled = _hndlrs, _lvl, _dsbld
            logr.propagate = _prpgt


def attach_stderr_handler(level=WARN, logger_name=None, propagate=False):
    # get old stderr logger
    logr = getLogger(logger_name)
    old_stderr_handler = next((handler for handler in logr.handlers if handler.name == 'stderr'),
                              None)

    # create new stderr logger
    new_stderr_handler = StreamHandler(sys.stderr)
    new_stderr_handler.name = 'stderr'
    new_stderr_handler.setLevel(NOTSET)
    new_stderr_handler.setFormatter(_FORMATTER)

    # do the switch
    with _logger_lock():
        if old_stderr_handler:
            logr.removeHandler(old_stderr_handler)
        logr.addHandler(new_stderr_handler)
        logr.setLevel(level)
        logr.propagate = propagate
