# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from requests import Request, Response

from conda.auxlib.logz import stringify


def test_stringify_json_response():
    request = Request("GET", "https://example.com/api/endpoint").prepare()
    response = Response()
    response.request = request
    response.url = request.url
    response.status_code = 200
    response.reason = "OK"
    response.headers["Content-Type"] = "application/json"
    response._content = b'{"key": "value"}'

    result = stringify(response, content_max_len=1000)

    assert result is not None
    assert '{"key": "value"}' in result
