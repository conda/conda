# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Register the built-in repodata_filters hook implementations."""

from . import exclude_newer

plugins = [exclude_newer]
"""The list of repodata filter plugins for easier registration with pluggy."""
