# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
Defines a JSON reporter backend

This reporter backend is used to provide JSON strings for output rendering. It is
essentially just a wrapper around ``conda.common.serialize.json.dumps``.
"""

from __future__ import annotations

import sys
from threading import RLock
from typing import TYPE_CHECKING

from ...base.constants import DEFAULT_JSON_REPORTER_BACKEND
from ...common.io import swallow_broken_pipe
from ...common.serialize import json
from .. import hookimpl
from ..types import (
    CondaReporterBackend,
    ProgressBarBase,
    ReporterRendererBase,
    SpinnerBase,
)

if TYPE_CHECKING:
    from typing import Any


class JSONProgressBar(ProgressBarBase):
    """
    Progress bar that outputs JSON to stdout
    """

    def __init__(
        self,
        description: str,
        enabled: bool = True,
        **kwargs,
    ):
        super().__init__(description)
        self.enabled = enabled

    def update_to(self, fraction) -> None:
        with self.get_lock():
            if self.enabled:
                sys.stdout.write(
                    f'{{"fetch":"{self.description}","finished":false,"maxval":1,"progress":{fraction:f}}}\n\0'
                )

    def refresh(self):
        pass

    @swallow_broken_pipe
    def close(self):
        with self.get_lock():
            if self.enabled:
                sys.stdout.write(
                    f'{{"fetch":"{self.description}","finished":true,"maxval":1,"progress":1}}\n\0'
                )
                sys.stdout.flush()

    @classmethod
    def get_lock(cls):
        """
        Used for our own sys.stdout.write/flush calls
        """
        if not hasattr(cls, "_lock"):
            cls._lock = RLock()
        return cls._lock


class JSONReporterRenderer(ReporterRendererBase):
    """
    Default implementation for JSON reporting in conda
    """

    def render(self, data: Any, **kwargs) -> str:
        return json.dumps(data)

    def detail_view(self, data: dict[str, str | int | bool], **kwargs) -> str:
        return json.dumps(data)

    def envs_list(self, data, **kwargs) -> str:
        return json.dumps({"envs": data})

    def progress_bar(
        self,
        description: str,
        **kwargs,
    ) -> ProgressBarBase:
        return JSONProgressBar(description, **kwargs)

    def spinner(self, message: str, fail_message: str = "failed\n") -> SpinnerBase:
        return JSONSpinner(message, fail_message)

    def prompt(
        self, message: str = "Proceed", choices=("yes", "no"), default: str = "yes"
    ) -> str:
        """
        For this class, we want this method to do nothing
        """


class JSONSpinner(SpinnerBase):
    """
    This class for a JSONSpinner does nothing because we do not want to include this output.
    """

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


@hookimpl(
    tryfirst=True
)  # make sure the default json reporter backend can't be overridden
def conda_reporter_backends():
    """
    Reporter backend for JSON

    This is the default reporter backend that returns objects as JSON strings.
    """
    yield CondaReporterBackend(
        name=DEFAULT_JSON_REPORTER_BACKEND,
        description="Default implementation for JSON reporting in conda",
        renderer=JSONReporterRenderer,
    )
