# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from ..deprecations import deprecated

# Mark the entire module for deprecation. For more information see
# https://github.com/conda/conda-content-trust and #14797
deprecated.module(
    "25.9.0",  # deprecate_in version
    "26.3.0",  # remove_in version
    addendum="This module will be moved to conda-content-trust.",
)
