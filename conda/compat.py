# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
# This module is only being maintained for conda-build compatibility
from __future__ import absolute_import, division, print_function, unicode_literals
import warnings as _warnings


# shim for conda-build
from .common.compat import *  # lgtm [py/polluting-import]
PY3 = PY3


if PY3:
    import configparser
else:
    import ConfigParser as configparser
configparser = configparser


from .gateways.disk.link import lchmod  # NOQA
lchmod = lchmod


print("WARNING: The conda.compat module is deprecated and will be removed in a future release.",
      file=sys.stderr)
