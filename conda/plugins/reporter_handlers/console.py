# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
Defines a "console" reporter handler

This reporter handler provides the default output for conda.
"""

from __future__ import annotations

from .. import CondaReporterHandler, hookimpl
from ..types import ReporterHandlerBase


class ConsoleReporterHandler(ReporterHandlerBase):
    """
    Default implementation for JSON reporting in conda
    """

    def string_view(self, data: str, **kwargs) -> str:
        return data

    def detail_view(self, data: dict[str, str | int | bool], **kwargs) -> str:
        table_str = ""
        longest_header = max(map(len, data.keys()))

        for header, value in data.items():
            table_str += f"{header:<{longest_header}} : {value}\n"

        return table_str


@hookimpl
def conda_reporter_handlers():
    """
    Reporter handler for console

    This is the default reporter handler that returns what is displayed by default in conda
    """
    yield CondaReporterHandler(
        name="console",
        description="Default implementation for console reporting in conda",
        handler=ConsoleReporterHandler(),
    )
