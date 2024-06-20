# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import json

from conda.common.serialize import json_dump
from conda.plugins.reporter_backends.json import JSONReporterRenderer


def test_json_handler():
    """
    Tests the JSONReporterHandler ReporterHandler class
    """
    test_data = {"one": "value_one", "two": "value_two", "three": "value_three"}
    test_str = "a string value"
    json_handler_object = JSONReporterRenderer()

    assert json_handler_object.detail_view(test_data) == json_dump(test_data)
    assert json_handler_object.render(test_str) == json.dumps(test_str)
