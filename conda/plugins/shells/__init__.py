# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from . import posix_os_exec, posix_os_exec_shell, posix_activate

#: The list of virtual package plugins for easier registration with pluggy
plugins = [posix_os_exec, posix_os_exec_shell, posix_activate]