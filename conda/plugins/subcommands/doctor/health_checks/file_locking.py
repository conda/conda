# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Health check: File locking support."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .....base.constants import OK_MARK, X_MARK
from .....base.context import context
from .....gateways.disk.lock import locking_supported
from .... import hookimpl
from ....types import CondaHealthCheck

if TYPE_CHECKING:
    from collections.abc import Iterable


def file_locking_check(prefix: str, verbose: bool) -> None:
    """Health check action: Report if file locking is supported."""
    if locking_supported():
        if context.no_lock:
            print(
                f"{X_MARK} File locking is supported but currently disabled using the CONDA_NO_LOCK=1 setting.\n"
            )
        else:
            print(f"{OK_MARK} File locking is supported.\n")
    else:
        print(f"{X_MARK} File locking is not supported.\n")


@hookimpl
def conda_health_checks() -> Iterable[CondaHealthCheck]:
    """Register the file locking health check."""
    yield CondaHealthCheck(
        name="file-locking",
        action=file_locking_check,
        summary="Check if file locking is supported",
    )
