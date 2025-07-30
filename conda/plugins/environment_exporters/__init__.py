# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Built-in conda environment exporter plugins."""

from . import environment_yml, explicit, specs

#: The list of environment exporter plugins for easier registration with pluggy
plugins = [environment_yml, explicit, specs]
