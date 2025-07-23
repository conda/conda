# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Built-in conda environment exporter plugins."""

from . import explicit, requirements, standard

#: The list of environment exporter plugins for easier registration with pluggy
plugins = [explicit, requirements, standard]
