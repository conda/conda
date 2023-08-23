# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from unittest.mock import patch

import requests

from conda.notices.cache import is_notice_response_cache_expired
from conda.notices.core import display_notices, retrieve_notices
from conda.testing.notices.helpers import add_resp_to_mock


def test_get_channel_notice_response_timeout_error(
    notices_cache_dir, notices_mock_fetch_get_session
):
    """Tests the timeout error case for the get_channel_notice_response function."""
    with patch("conda.notices.fetch.logger") as mock_logger:
        notices_mock_fetch_get_session().get.side_effect = requests.exceptions.Timeout

        channel_notice_set = retrieve_notices()
        display_notices(channel_notice_set)

        for mock_call in mock_logger.mock_calls:
            assert "Request timed out for channel" in str(mock_call)


def test_get_channel_notice_response_malformed_json(
    notices_cache_dir, notices_mock_fetch_get_session
):
    """Tests malformed json error case for the get_channel_notice_response function."""
    messages = ("hello", "hello 2")
    with patch("conda.notices.fetch.logger") as mock_logger:
        add_resp_to_mock(notices_mock_fetch_get_session, 200, messages, raise_exc=True)

        channel_notice_set = retrieve_notices()
        display_notices(channel_notice_set)

        expected_log_messages = (
            "Unable to parse JSON data",
            "Received 404 when trying to GET",
        )

        for expected, mock_call in zip(expected_log_messages, mock_logger.mock_calls):
            assert expected in str(mock_call)


def test_notice_response_cache_expired():
    """Channel notice is expired if expired_at is None."""

    class ExpiredAtNone:
        expired_at = None

    class Notices:
        notices = [ExpiredAtNone]

    assert is_notice_response_cache_expired(Notices)  # type: ignore
