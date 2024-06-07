# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
Defines a JSON reporter backend

This reporter backend is used to provide JSON strings for output rendering. It is
essentially just a wrapper around ``conda.common.serialize.json_dump``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ...common.serialize import json_dump
from .. import CondaReporterBackend, hookimpl
from ..types import ReporterRendererBase

if TYPE_CHECKING:
    from typing import Any


class JSONReporterRenderer(ReporterRendererBase):
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
def conda_reporter_backends():
    """
    Reporter backend for JSON

    This is the default reporter backend that returns objects as JSON strings
    that can be passed to reporter streams .
    """
    yield CondaReporterBackend(
        name="json",
        description="Default implementation for JSON reporting in conda",
        renderer=JSONReporterRenderer,
    )
