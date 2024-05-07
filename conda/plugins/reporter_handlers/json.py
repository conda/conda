# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
Defines a JSON reporter handler

This reporter handler is used to provide JSON strings for output rendering. It is
essentially just a wrapper around ``json.dumps``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any

from ...common.serialize import json_dump
from .. import CondaReporterHandler, hookimpl
from ..types import ReporterHandlerBase


class JSONReporterHandler(ReporterHandlerBase):
    """
    Default implementation for JSON reporting in conda
    """

    def render(self, data: Any, **kwargs) -> str:
        return json_dump(data)

    def detail_view(self, data: dict[str, str | int | bool], **kwargs) -> str:
        return json_dump(data)

    def envs_list(self, data, **kwargs) -> str:
        return json_dump({"envs": data})


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
