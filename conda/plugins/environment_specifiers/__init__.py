# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Register the built-in environment specifier hook implementations."""

from . import environment_yml, explicit, requirements_txt

plugins = [requirements_txt, environment_yml, explicit]
"""The list of environment specifier plugins for easier registration with pluggy."""
