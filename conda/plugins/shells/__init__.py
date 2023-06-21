# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from .posix import posix_os_exec_shell

#: The list of virtual package plugins for easier registration with pluggy
plugins = [posix_os_exec_shell]
