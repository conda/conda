# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
Defines a JSON reporter handler

This reporter handler is used to provide JSON strings for output rendering. It is
essentially just a wrapper around ``json.dumps``.
"""

from __future__ import annotations

import json

from .. import CondaReporterHandler, hookimpl
from ..types import ReporterHandlerBase


class JSONReporterHandler(ReporterHandlerBase):
    """
    Default implementation for JSON reporting in conda
    """

    def string_view(self, data: str, **kwargs) -> str:
        return json.dumps(data, **kwargs)

    def detail_view(self, data: dict[str, str | int | bool], **kwargs) -> str:
        return json.dumps(data, **kwargs)


@hookimpl
def conda_reporter_handlers():
    """
    Reporter handler for JSON

    This is the default reporter handler that returns objects as JSON strings
    that can be passed to output handlers.
    """
    yield CondaReporterHandler(
        name="json",
        description="Default implementation for JSON reporting in conda",
        handler=JSONReporterHandler(),
    )
