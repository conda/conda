# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from collections.abc import Callable
from typing import NamedTuple

from ....history import History


class HealthCheckStatus(NamedTuple):
    message: str
    error: bool


class HealthCheck(NamedTuple):
    title: str
    description: str
    name: str
    check_function: Callable[..., HealthCheckStatus]


def get_current_packages():
    pass


def find_missing_packages():
    pass


def format_error_message():
    pass


def check_for_missing_files_from_packages(prefix: str) -> HealthCheckStatus:
    """
    Checks to see if all files listed by conda list exist
    """
    history = History(prefix)
    current_packages = get_current_packages(history)
    missing_packages = find_missing_packages(current_packages)

    if len(missing_packages) > 0:
        error_message = format_error_message(missing_packages)
        return HealthCheckStatus(message=error_message, error=True)

    return HealthCheckStatus(message="Status Okay!", error=False)
