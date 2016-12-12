# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from logging import getLogger
import signal

from .._vendor.auxlib.decorators import memoize
from ..base.constants import INTERRUPT_SIGNALS
from ..exceptions import CondaSignalInterrupt

log = getLogger(__name__)


def conda_signal_handler(signum, frame):
    raise CondaSignalInterrupt(signum)


@memoize
def register_signals():
    for sig in INTERRUPT_SIGNALS:
        if hasattr(signal, sig):
            signal.signal(getattr(signal, sig), conda_signal_handler)
