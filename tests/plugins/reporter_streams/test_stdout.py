# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from pytest import CaptureFixture

from conda.plugins.reporter_streams.stdout import stdout_io


def test_stdout_render(capsys: CaptureFixture):
    """
    Tests the StdoutHandler OutputHandler class
    """
    test_str = "a string value"

    with stdout_io() as io:
        io.write(test_str)
        stdout, _ = capsys.readouterr()

    assert stdout == test_str
