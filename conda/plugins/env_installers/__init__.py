# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Register the built-in env_installer hook implementations."""

from . import conda, pip

#: The list of env_installer plugins for easier registration with pluggy
plugins = [conda, pip]
