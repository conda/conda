# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
conda._ng — private namespace for the next-generation conda backend.

This package is intentionally private (leading underscore).  Public access is
gated behind the ``experimental`` context setting:

    CONDA_EXPERIMENTAL=ng conda install ...

or via the convenience entry point:

    python -m conda.ng install ...

Nothing in this package is part of conda's stable public API.  Expect
breaking changes across minor releases while the ``ng`` flag remains
experimental.
"""
