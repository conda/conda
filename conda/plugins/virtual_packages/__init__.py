# SPDX-FileCopyrightText: © 2012 Continuum Analytics, Inc. <http://continuum.io>
# SPDX-FileCopyrightText: © 2017 Anaconda, Inc. <https://www.anaconda.com>
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from . import archspec, cuda, linux, osx, windows

#: The list of virtual package plugins for easier registration with pluggy
plugins = [archspec, cuda, linux, osx, windows]
