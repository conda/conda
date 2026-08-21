# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from datetime import datetime, timedelta, timezone

import pytest

from conda.notices.cache import is_notice_response_cache_expired
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
    expires_at = datetime.now(timezone.utc) + timedelta(days=1)
    response = ChannelNoticeResponse(
        "https://conda.example.com/notices.json",
        "test",
        {"notices": [{field: expires_at.isoformat()}]},
    )

    assert response.notices[0].expired_at == expires_at
    assert not is_notice_response_cache_expired(response)
