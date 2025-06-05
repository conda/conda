# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Register the built-in environment specifier hook implementations."""

from . import binstar, environment_yml, requirements

#: The list of environment specifier plugins for easier registration with pluggy
plugins = [binstar, requirements, environment_yml]
