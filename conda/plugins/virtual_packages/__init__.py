# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from . import archspec, cuda, linux, osx, windows


plugins = [archspec, cuda, linux, osx, windows]
