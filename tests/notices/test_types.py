# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from conda.notices.types import UNDEFINED_MESSAGE_ID, ChannelNoticeResponse
from conda.testing.notices.helpers import get_test_notices


def test_channel_notice_response():
    """Tests a normal invocation of the ChannelNoticeResponse class."""
    messages = tuple(f"Test {idx}" for idx in range(1, 4, 1))
    expected_num_notices = len(messages)
    json_data = get_test_notices(messages)

    response = ChannelNoticeResponse("http://localhost", "local", json_data)

    notices = response.notices

    assert len(notices) == expected_num_notices


def test_channel_notice_response_date_parse_error():
    """
    Test a creation of the ChannelNoticeResponse object where we pass in bad values for
    "created_at" and "level" and make sure the appropriate defaults are there.
    """
    messages = tuple(f"Test {idx}" for idx in range(1, 4, 1))
    json_data = get_test_notices(messages)
    json_data["notices"][0]["created_at"] = "Not a valid datetime string"
    json_data["notices"][0]["level"] = "Not a valid level"

    response = ChannelNoticeResponse("http://localhost", "local", json_data)

    notices = response.notices

    assert notices[0].created_at is None
    assert notices[0].level.value == "info"


def test_channel_notice_response_integer_id():
    """
    Test to make sure that the integers get converted to strings when creating
    a channel notice response object.
    """
    json_data = {
        "notices": [
            {
                "id": 1,
                "message": "test",
                "level": "warning",
                "created_at": "2023-01-01 00:00:00",
                "updated_at": "2023-01-01 00:00:00",
            }
        ]
    }

    response = ChannelNoticeResponse("http://localhost", "local", json_data)

    assert isinstance(response.notices[0].id, str)


def test_channel_notice_undefined_id():
    """
    Test to make sure that when a message does not define an "id" it appears
    as the string value "undefined".
    """
    json_data = {
        "notices": [
            {
                "message": "test",
                "level": "warning",
                "created_at": "2023-01-01 00:00:00",
                "updated_at": "2023-01-01 00:00:00",
            }
        ]
    }

    response = ChannelNoticeResponse("http://localhost", "local", json_data)

    assert response.notices[0].id == UNDEFINED_MESSAGE_ID
