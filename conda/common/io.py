# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import logging
import sys
from contextlib import contextmanager
from logging import getLogger, StreamHandler, Formatter

from ..compat import StringIO

log = getLogger(__name__)

_FORMATTER = Formatter("%(levelname)s %(name)s:%(funcName)s(%(lineno)d):\n%(message)s")


@contextmanager
def captured():
    class CapturedText(object):
        pass
    sys.stdout = outfile = StringIO()
    sys.stderr = errfile = StringIO()
    c = CapturedText()
    try:
        yield c
    finally:
        c.stdout, c.stderr = outfile.getvalue(), errfile.getvalue()
        sys.stdout, sys.stderr = sys.__stdout__, sys.__stderr__


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
    _dsbld, _prpgt = logr.disabled, logr.propagate
    with _logger_lock():
        logr.disabled, logr.propagate = True, False
    try:
        yield
    finally:
        with _logger_lock():
            logr.disabled, logr.propagate = _dsbld, _prpgt


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
            logr.handlers, logr.level, logr.disabled, logr.propagate = _hndlrs, _lvl, _dsbld, _prpgt
