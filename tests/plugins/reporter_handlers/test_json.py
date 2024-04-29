# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import json

from conda.plugins.reporter_handlers.json import JSONReporterHandler


def test_json_handler():
    """
    Tests the JSONReporterHandler ReporterHandler class
    """
    test_data = {"one": "value_one", "two": "value_two", "three": "value_three"}
    test_str = "a string value"
    json_handler_object = JSONReporterHandler()

    assert json_handler_object.detail_view(test_data) == json.dumps(test_data)
    assert json_handler_object.string_view(test_str) == json.dumps(test_str)
