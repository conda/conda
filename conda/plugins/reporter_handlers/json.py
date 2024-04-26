# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
Defines a JSON reporter handler

This reporter handler is used to provide JSON strings for output rendering. It is
essentially just a wrapper around ``json.dumps``.
"""

import json

from .. import CondaReporterHandler, hookimpl
from ..types import DetailRecord, ReporterHandlerBase


class JSONReporterHandler(ReporterHandlerBase):
    """
    Default implementation for JSON reporting in conda
    """

    def string_view(self, data: str, **kwargs) -> str:
        return json.dumps(data, **kwargs)

    def detail_view(self, data: DetailRecord, **kwargs) -> str:
        return json.dumps(data, **kwargs)


@hookimpl
def conda_reporter_handlers():
    """
    Reporter handler for JSON

    This is the default reporter handler that returns objects as JSON strings
    that can be passed to output handlers.
    """
    return CondaReporterHandler(
        name="json",
        description="Default implementation for JSON reporting in conda",
        handler=JSONReporterHandler(),
    )
