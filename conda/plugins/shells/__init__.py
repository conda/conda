# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from . import shell_cli
from .csh_tcsh import csh_tcsh_shell
from .fish import fish_shell
from .posix import posix_os_exec_shell

#: The list of virtual package plugins for easier registration with pluggy
plugins = [shell_cli, posix_os_exec_shell, csh_tcsh_shell, fish_shell]
