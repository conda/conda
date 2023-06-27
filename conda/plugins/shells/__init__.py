# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from . import shell_cli
from .posix import posix_os_exec_shell

#: The list of virtual package plugins for easier registration with pluggy
plugins = [shell_cli, posix_os_exec_shell]
