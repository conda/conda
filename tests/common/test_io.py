# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import sys
from contextlib import contextmanager
from io import StringIO
from logging import DEBUG, NOTSET, WARN, getLogger
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest

from conda.common.io import (
    CaptureTarget,
    ReporterManager,
    attach_stderr_handler,
    captured,
)
from conda.plugins import CondaOutputHandler, CondaReporterHandler
from conda.plugins.types import ReporterHandlerBase

if TYPE_CHECKING:
    from pytest import CaptureFixture


def test_captured():
    stdout_text = "stdout text"
    stderr_text = "stderr text"

    def print_captured(*args, **kwargs):
        with captured(*args, **kwargs) as c:
            print(stdout_text, end="")
            print(stderr_text, end="", file=sys.stderr)
        return c

    c = print_captured()
    assert c.stdout == stdout_text
    assert c.stderr == stderr_text

    c = print_captured(CaptureTarget.STRING, CaptureTarget.STRING)
    assert c.stdout == stdout_text
    assert c.stderr == stderr_text

    c = print_captured(stderr=CaptureTarget.STDOUT)
    assert c.stdout == stdout_text + stderr_text
    assert c.stderr is None

    caller_stdout = StringIO()
    caller_stderr = StringIO()
    c = print_captured(caller_stdout, caller_stderr)
    assert c.stdout is caller_stdout
    assert c.stderr is caller_stderr
    assert caller_stdout.getvalue() == stdout_text
    assert caller_stderr.getvalue() == stderr_text

    with captured() as outer_c:
        inner_c = print_captured(None, None)
    assert inner_c.stdout is None
    assert inner_c.stderr is None
    assert outer_c.stdout == stdout_text
    assert outer_c.stderr == stderr_text


def test_attach_stderr_handler():
    name = "abbacadabba"
    logr = getLogger(name)
    assert len(logr.handlers) == 0
    assert logr.level is NOTSET

    debug_message = "debug message 1329-485"

    with captured() as c:
        attach_stderr_handler(WARN, name)
        logr.warn("test message")
        logr.debug(debug_message)

    assert len(logr.handlers) == 1
    assert logr.handlers[0].name == "stderr"
    assert logr.handlers[0].level is WARN
    assert logr.level is NOTSET
    assert c.stdout == ""
    assert "test message" in c.stderr
    assert debug_message not in c.stderr

    # round two, with debug
    with captured() as c:
        attach_stderr_handler(DEBUG, name)
        logr.warn("test message")
        logr.debug(debug_message)
        logr.info("info message")

    assert len(logr.handlers) == 1
    assert logr.handlers[0].name == "stderr"
    assert logr.handlers[0].level is DEBUG
    assert logr.level is NOTSET
    assert c.stdout == ""
    assert "test message" in c.stderr
    assert debug_message in c.stderr


class DummyReporterHandler(ReporterHandlerBase):
    def envs_list(self, data, **kwargs) -> str:
        return f"envs_list: {data}"

    def detail_view(self, data: dict[str, str | int | bool], **kwargs) -> str:
        return f"detail_view: {data}"


@contextmanager
def dummy_io():
    yield sys.stdout


def test_reporter_manager(capsys: CaptureFixture):
    """
    Ensure basic coverage of the :class:`~conda.common.io.ReporterManager` class.
    """
    # Setup
    reporter_handler = CondaReporterHandler(
        name="test-reporter-handler", description="test", handler=DummyReporterHandler()
    )
    output_handler = CondaOutputHandler(
        name="test-output-handler", description="test", get_output_io=dummy_io
    )
    plugin_manager = SimpleNamespace(
        get_reporter_handler=lambda _: reporter_handler,
        get_output_handler=lambda _: output_handler,
    )
    reporters = ({"backend": "test-reporter-handler", "output": "test-output-handler"},)

    context = SimpleNamespace(plugin_manager=plugin_manager, reporters=reporters)
    reporter_manager = ReporterManager(context)

    # Test simple rendering of object
    reporter_manager.render("test-string")

    stdout, stderr = capsys.readouterr()
    assert stdout == "test-string"
    assert not stderr

    # Test rendering of object with a component
    reporter_manager.render("test-string", component="envs_list")

    stdout, stderr = capsys.readouterr()
    assert stdout == "envs_list: test-string"
    assert not stderr

    # Test error when component cannot be found
    with pytest.raises(
        AttributeError,
        match="'non_existent_view' is not a valid reporter handler component",
    ):
        reporter_manager.render({"test": "data"}, component="non_existent_view")
