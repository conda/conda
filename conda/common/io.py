# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import sys
from contextlib import contextmanager
from logging import getLogger

from ..compat import StringIO

log = getLogger(__name__)


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
def disable_logger(logger_name):
    logger = getLogger(logger_name)
    enter_disabled, enter_propagate = logger.disabled, logger.propagate
    try:
        logger.disabled, logger.propagate = True, False
        yield
    finally:
        logger.disabled, logger.propagate = enter_disabled, enter_propagate
