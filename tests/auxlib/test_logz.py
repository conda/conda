# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import json
from datetime import timedelta

from conda.auxlib.logz import stringify


class _FakePreparedRequest:
    method = "GET"
    path_url = "/api/endpoint"
    url = "https://example.com/api/endpoint"
    headers = {}
    body = None


_FakePreparedRequest.__name__ = "PreparedRequest"
_FakePreparedRequest.__module__ = "requests.models"


class _FakeResponse:
    url = "https://example.com/api/endpoint"
    status_code = 200
    reason = "OK"
    elapsed = timedelta(milliseconds=110)
    request = _FakePreparedRequest()


_FakeResponse.__name__ = "Response"
_FakeResponse.__module__ = "requests.models"


def test_stringify_json_response_no_truncation():
    """Regression: json.loads/json.dumps in stringify must not raise NameError."""
    response = _FakeResponse()
    response.headers = {"Content-Type": "application/json"}
    response.text = '{"key": "value"}'
    # content_max_len > len(text) triggers the json.loads/json.dumps path
    result = stringify(response, content_max_len=1000)
    assert result is not None
    assert "key" in result


def test_stringify_json_response_truncation():
    """The text-truncation branch (len > content_max_len) skips json.loads and works."""
    response = _FakeResponse()
    response.headers = {"Content-Type": "application/json"}
    response.text = '{"key": "value"}'
    # content_max_len < len(text) takes the direct-truncation path (no json.loads)
    result = stringify(response, content_max_len=5)
    assert result is not None
    assert '{"key' in result


def test_stringify_no_content_max_len():
    """With content_max_len=0 (default), the response body is omitted entirely."""
    response = _FakeResponse()
    response.headers = {"Content-Type": "application/json"}
    response.text = '{"key": "value"}'
    result = stringify(response, content_max_len=0)
    assert result is not None
    assert "key" not in result
