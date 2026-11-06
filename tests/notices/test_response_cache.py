# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

import os
import time
from datetime import UTC, datetime, timedelta

import pytest

from conda.base.constants import NOTICES_DECORATOR_DISPLAY_INTERVAL_NS
from conda.notices.cache import (
    get_notice_response_from_cache,
    is_notice_response_cache_expired,
    write_notice_response_to_cache,
)
from conda.notices.types import ChannelNoticeResponse


def test_empty_notice_response_cache_expired():
    response = ChannelNoticeResponse(
        "https://conda.example.com/notices.json",
        "test",
        {"notices": []},
    )

    assert is_notice_response_cache_expired(response)


@pytest.mark.parametrize("field", ("expires_at", "expired_at"))
def test_notice_response_expiration_field(field):
    expires_at = datetime.now(UTC) + timedelta(days=1)
    response = ChannelNoticeResponse(
        "https://conda.example.com/notices.json",
        "test",
        {"notices": [{field: expires_at.isoformat()}]},
    )

    assert response.notices[0].expired_at == expires_at
    assert not is_notice_response_cache_expired(response)


def test_notice_response_cache_max_age(notices_cache_dir, mocker):
    url = "https://conda.example.com/notices.json"
    expires_at = datetime.now(UTC) + timedelta(days=90)
    response = ChannelNoticeResponse(
        url,
        "test",
        {"notices": [{"expires_at": expires_at.isoformat()}]},
    )
    write_notice_response_to_cache(response, notices_cache_dir)
    cache_time_ns = response.get_cache_key(url, notices_cache_dir).stat().st_mtime_ns
    now = mocker.patch("conda.notices.cache.time.time_ns")

    now.return_value = cache_time_ns + NOTICES_DECORATOR_DISPLAY_INTERVAL_NS - 1
    assert get_notice_response_from_cache(url, "test", notices_cache_dir) == response

    now.return_value = cache_time_ns + NOTICES_DECORATOR_DISPLAY_INTERVAL_NS
    assert get_notice_response_from_cache(url, "test", notices_cache_dir) is None


def test_notice_response_cache_refreshes_identical_response(notices_cache_dir):
    url = "https://conda.example.com/notices.json"
    expires_at = datetime.now(UTC) + timedelta(days=90)
    response = ChannelNoticeResponse(
        url,
        "test",
        {"notices": [{"expires_at": expires_at.isoformat()}]},
    )
    write_notice_response_to_cache(response, notices_cache_dir)
    cache_key = response.get_cache_key(url, notices_cache_dir)
    expired = time.time_ns() - NOTICES_DECORATOR_DISPLAY_INTERVAL_NS - 1_000_000_000
    os.utime(cache_key, ns=(expired, expired))
    assert get_notice_response_from_cache(url, "test", notices_cache_dir) is None

    write_notice_response_to_cache(response, notices_cache_dir)

    assert get_notice_response_from_cache(url, "test", notices_cache_dir) == response


def test_notice_response_cache_preserves_previous_response_on_serialization_error(
    notices_cache_dir,
):
    response = ChannelNoticeResponse(
        "https://conda.example.com/notices.json", "test", {"notices": []}
    )
    write_notice_response_to_cache(response, notices_cache_dir)
    cache_key = response.get_cache_key(response.url, notices_cache_dir)
    original = cache_key.read_bytes()
    invalid_response = response._replace(json_data={"notices": [object()]})

    with pytest.raises(TypeError):
        write_notice_response_to_cache(invalid_response, notices_cache_dir)

    assert cache_key.read_bytes() == original


def test_notice_response_cache_preserves_previous_response_on_replace_error(
    notices_cache_dir, mocker
):
    response = ChannelNoticeResponse(
        "https://conda.example.com/notices.json", "test", {"notices": []}
    )
    write_notice_response_to_cache(response, notices_cache_dir)
    cache_key = response.get_cache_key(response.url, notices_cache_dir)
    original = cache_key.read_bytes()
    updated_response = response._replace(json_data={"notices": [{"id": "new"}]})
    mocker.patch("os.replace", side_effect=PermissionError("cache replacement denied"))

    with pytest.raises(PermissionError, match="cache replacement denied"):
        write_notice_response_to_cache(updated_response, notices_cache_dir)

    assert cache_key.read_bytes() == original
