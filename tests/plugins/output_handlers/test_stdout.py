# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from pytest import CaptureFixture

from conda.plugins.output_handlers.stdout import StdoutRenderer


def test_stdout_render(capsys: CaptureFixture):
    """
    Tests the StdoutHandler OutputHandler class
    """
    test_str = "a string value"
    stdout_renderer = StdoutRenderer()
    stdout_renderer(test_str)
    stdout, _ = capsys.readouterr()

    assert stdout == test_str
