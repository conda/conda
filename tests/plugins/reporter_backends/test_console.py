# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from conda.plugins.reporter_backends.console import ConsoleReporterRenderer


def test_console_reporter_renderer():
    """
    Tests the ``ConsoleReporterRenderer`` class
    """
    test_data = {"one": "value_one", "two": "value_two", "three": "value_three"}
    test_str = "a string value"
    expected_table_str = (
        "\n   one : value_one\n   two : value_two\n three : value_three\n\n"
    )
    console_handler_object = ConsoleReporterRenderer()

    assert console_handler_object.detail_view(test_data) == expected_table_str
    assert console_handler_object.render(test_str) == test_str
