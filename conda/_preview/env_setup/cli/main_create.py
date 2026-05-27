# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""CLI implementation for `conda create` — env-setup preview stub.

This module is part of the ``env-setup`` preview feature. It intercepts
``conda create`` when the preview is enabled and raises ``OperationNotAllowed``
until a functional implementation is available.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ....exceptions import OperationNotAllowed
from ....plugins import hookimpl
from ....plugins.types import CondaSubcommand

if TYPE_CHECKING:
    from argparse import Namespace
    from collections.abc import Iterable


def execute(args: Namespace) -> int:
    raise OperationNotAllowed(
        "The 'env-setup' preview implementation of 'conda create' is not yet available."
    )


@hookimpl
def conda_subcommands() -> Iterable[CondaSubcommand]:
    yield CondaSubcommand(
        name="create",
        summary="Create a new conda environment.",
        action=execute,
    )
