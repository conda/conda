# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import sys
from contextlib import contextmanager
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest

from conda.plugins import CondaReporterBackend, CondaReporterOutput
from conda.plugins.types import ReporterRendererBase
from conda.reporters import render

if TYPE_CHECKING:
    from pytest import CaptureFixture


class DummyReporterRenderer(ReporterRendererBase):
    def envs_list(self, data, **kwargs) -> str:
        return f"envs_list: {data}"

    def detail_view(self, data: dict[str, str | int | bool], **kwargs) -> str:
        return f"detail_view: {data}"


@contextmanager
def dummy_io():
    yield sys.stdout


def test_reporter_manager(capsys: CaptureFixture, mocker):
    """
    Ensure basic coverage of the :class:`~conda.common.io.ReporterManager` class.
    """
    # Setup
    reporter_backend = CondaReporterBackend(
        name="test-reporter-backend",
        description="test",
        renderer=DummyReporterRenderer,
    )
    reporter_output = CondaReporterOutput(
        name="test-reporter-output", description="test", stream=dummy_io
    )
    plugin_manager = SimpleNamespace(
        get_reporter_backend=lambda _: reporter_backend,
        get_reporter_output=lambda _: reporter_output,
    )
    reporters = (
        {"backend": "test-reporter-backend", "stream": "test-reporter-output"},
    )

    context = mocker.patch("conda.reporters.context")
    context.plugin_manager = plugin_manager
    context.reporters = reporters

    # Test simple rendering of object
    render("test-string")

    stdout, stderr = capsys.readouterr()
    assert stdout == "test-string"
    assert not stderr

    # Test rendering of object with a style
    render("test-string", style="envs_list")

    stdout, stderr = capsys.readouterr()
    assert stdout == "envs_list: test-string"
    assert not stderr

    # Test error when style cannot be found
    with pytest.raises(
        AttributeError,
        match="'non_existent_view' is not a valid reporter backend style",
    ):
        render({"test": "data"}, style="non_existent_view")
