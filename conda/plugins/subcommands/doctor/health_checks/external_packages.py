# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Health check: Report packages not installed by conda"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .....base.constants import OK_MARK, X_MARK
from .....core.prefix_data import PrefixData
from .... import hookimpl
from ....types import CondaHealthCheck

if TYPE_CHECKING:
    from collections.abc import Iterable


def find_external_packages(prefix: str) -> list[PrefixData]:
    prefix_data = PrefixData(prefix, interoperability=True)
    external_packages = prefix_data.get_python_packages()
    return external_packages


def print_external_packages(prefix: str, verbose: bool) -> None:
    external_packages = find_external_packages(prefix)
    if not external_packages:
        print(f"{OK_MARK} No external packages found.\n")
    else:
        print(f"{X_MARK} These packages are not installed by conda:\n")
        for package in external_packages:
            print(package.name)


@hookimpl
def conda_health_checks() -> Iterable[CondaHealthCheck]:
    yield CondaHealthCheck(
        name="external-packages",
        action=print_external_packages,
        summary="List packages not installed by conda.",
    )
