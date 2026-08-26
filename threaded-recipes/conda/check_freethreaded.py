# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import sys

assert getattr(
    sys, '_is_gil_enabled', lambda: True
)() is False, 'GIL is enabled -- not a free-threaded (cp314t) build'
