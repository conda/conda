# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""CLI implementation for `conda install` — env-setup preview stub.

This module is part of the ``env-setup`` preview feature. It intercepts
``conda install`` when the preview is enabled and raises ``OperationNotAllowed``
until a functional implementation is available.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from conda.exceptions import OperationNotAllowed

if TYPE_CHECKING:
    from argparse import ArgumentParser, Namespace


def execute(args: Namespace, parser: ArgumentParser) -> int:
    raise OperationNotAllowed(
        "The 'env-setup' preview implementation of 'conda install' is not yet available."
    )
