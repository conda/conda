# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import sys

PY3 = sys.version_info[0] == 3


def u(some_str):
    if PY3:
        return some_str
    else:
        return unicode(some_str)


def b(some_str, encoding="utf-8"):
    try:
        return bytes(some_str, encoding=encoding)
    except TypeError:
        return some_str
