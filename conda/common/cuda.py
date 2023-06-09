# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from ..deprecations import deprecated
from ..plugins.virtual_packages import cuda


@deprecated(
    "23.3",
    "23.9",
    addendum="Use `conda.plugins.virtual_packages.cuda.cuda_version` instead.",
)
def cuda_detect():
    return cuda.cuda_version()
