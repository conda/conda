# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Register the built-in environment specifier hook implementations."""

from . import binstar, environment_yml, explicit, requirements_txt

#: The list of environment speficier plugins for easier registration with pluggy
plugins = [binstar, requirements_txt, environment_yml, explicit]
