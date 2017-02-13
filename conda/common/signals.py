# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import signal

from .compat import iteritems


def get_signal_name(signum):
    """
    Examples:
        >>> from signal import SIGINT
        >>> get_signal_name(SIGINT)
        'SIGINT'

    """
    return next((k for k, v in iteritems(signal.__dict__)
                 if v == signum and k.startswith('SIG') and not k.startswith('SIG_')),
                None)
