# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from functools import wraps
import unittest

try:
    from unittest import mock
    skip_mock = False
except ImportError:
    try:
        import mock
        mock
        skip_mock = False
    except ImportError:
        skip_mock = True


def skip_if_no_mock(func):
    @wraps(func)
    @unittest.skipIf(skip_mock, 'install mock library to test')
    def inner(*args, **kwargs):
        return func(*args, **kwargs)
    return inner
