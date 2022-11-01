# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import warnings

from conda.plugins.virtual_packages import cuda


def cuda_detect():
    warnings.warn(
        "`conda.common.cuda.cuda_detect` is pending deprecation and "
        "will be removed in a future release. Please use "
        "`conda.plugins.virtual_packages.cuda.cuda_version` instead.",
        PendingDeprecationWarning,
    )
    return cuda.cuda_version()
