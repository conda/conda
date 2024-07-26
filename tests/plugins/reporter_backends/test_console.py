# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from contextlib import nullcontext

from conda.plugins.reporter_backends.console import (
    ConsoleReporterRenderer,
    TQDMProgressBar,
)


def test_console_reporter_renderer():
    """
    Tests the ``ConsoleReporterRenderer`` class
    """
    test_data = {"one": "value_one", "two": "value_two", "three": "value_three"}
    test_str = "a string value"
    expected_table_str = (
        "\n   one : value_one\n   two : value_two\n three : value_three\n\n"
    )
    console_reporter_renderer = ConsoleReporterRenderer()

    assert console_reporter_renderer.detail_view(test_data) == expected_table_str
    assert console_reporter_renderer.render(test_str) == test_str

    progress_bar = console_reporter_renderer.progress_bar(
        description="Test progress bar description", io_context_manager=nullcontext()
    )

    assert isinstance(progress_bar, TQDMProgressBar)

    progress_bar_context_manager = (
        console_reporter_renderer.progress_bar_context_manager(None)
    )
    assert isinstance(progress_bar_context_manager, nullcontext)
