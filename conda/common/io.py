# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import sys
from contextlib import contextmanager
from logging import getLogger

from ..compat import StringIO

log = getLogger(__name__)


@contextmanager
def captured():
    try:
        class CapturedText(object):
            pass
        sys.stdout = outfile = StringIO()
        sys.stderr = errfile = StringIO()
        c = CapturedText()
        yield c
        c.stdout, c.stderr = outfile.getvalue(), errfile.getvalue()
    finally:
        sys.stdout, sys.stderr = sys.__stdout__, sys.__stderr__

