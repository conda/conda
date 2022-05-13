# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

# This is just here so that tests is a package, so that dotted relative
# imports work.
from __future__ import print_function
from conda.gateways.logging import initialize_logging
initialize_logging()

from conda.testing import (
    conda_check_versions_aligned,
    conda_ensure_sys_python_is_base_env_python,
    conda_move_to_front_of_PATH,
)

conda_ensure_sys_python_is_base_env_python()
conda_move_to_front_of_PATH()
conda_check_versions_aligned()
