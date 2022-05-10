# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import json
import os
import datetime
import uuid
from unittest import mock
from typing import TypedDict, Literal, Optional

import pytest

from conda.cli import main_notices as notices
from conda.cli import conda_argparse

NoticeLevel = Literal["info", "warning", "critical"]


class Notice(TypedDict):
    id: str
    message: str
    level: NoticeLevel
    created_at: datetime.datetime
    expiry: int
    interval: int


DEFAULT_NOTICE_MESG = "Here is an example message that will be displayed to users"


def get_test_notices(
    num_mesg: Optional[int] = 1,
    level: Optional[NoticeLevel] = "info",
    mesg: Optional[str] = DEFAULT_NOTICE_MESG,
    created_at: Optional[datetime.datetime] = None,
    expiry: Optional[int] = 604_800,
    interval: Optional[int] = 604_800,
) -> dict:
    created_at = created_at or datetime.datetime.now(datetime.timezone.utc)

    return {
        "notices": list(
            {
                "id": str(uuid.uuid4()),
                "message": mesg,
                "level": level,
                "created_at": created_at.isoformat(),
                "expiry": expiry,
                "interval": interval,
            }
            for _ in range(num_mesg)
        )
    }


class MockResponse:
    def __init__(self, status_code, json_data):
        self.status_code = status_code
        self.json_data = json_data

    def json(self):
        return self.json_data


@pytest.fixture(scope="function")
def args_n_parser():
    parser = conda_argparse.generate_parser()
    args = parser.parse_args(["notices"])

    return args, parser


@pytest.mark.parametrize("status_code", (200, 404))
def test_main_notices(status_code, fs, capsys, args_n_parser):
    """
    Test the full working path through the code. We vary the test based on the status code
    we get back from the server.

    We have the "defaults" channel set and are expecting to receive messages
    from both of these channels.
    """
    args, parser = args_n_parser

    mesg_one = "Test One"
    mesg_two = "Test Two"

    notices_one = get_test_notices(mesg=mesg_one)
    notices_two = get_test_notices(mesg=mesg_two)

    with mock.patch("conda.gateways.connection.session.CondaSession.get") as session_get:
        session_get.side_effect = [
            MockResponse(status_code, notices_one),  # /pkgs/main
            MockResponse(status_code, notices_two),  # /pkgs/r
        ]
        notices.execute(args, parser)

    captured = capsys.readouterr()

    assert captured.err == ""
    assert "Retrieving" in captured.out

    if status_code < 300:
        assert mesg_one in captured.out
        assert mesg_two in captured.out
    else:
        assert mesg_one not in captured.out
        assert mesg_two not in captured.out


def test_main_notices_reads_from_cache(fs, capsys, args_n_parser):
    """
    Test the full working path through the code when reading from cache instead of making
    an HTTP request.

    We have the "defaults" channel set and are expecting to receive messages
    from both of these channels.
    """
    args, parser = args_n_parser

    cache_dir = "./cache/"
    cache_filename_one = "defaults-pkgs-r-notices.json"
    cache_key_one = os.path.join(cache_dir, cache_filename_one)

    cache_filename_two = "defaults-pkgs-main-notices.json"
    cache_key_two = os.path.join(cache_dir, cache_filename_two)

    mesg_one = "Test One"
    mesg_two = "Test Two"

    notices_one = get_test_notices(mesg=mesg_one)
    notices_two = get_test_notices(mesg=mesg_two)

    with mock.patch("conda.notices.user_cache_dir") as user_cache_dir:
        user_cache_dir.return_value = cache_dir
        fs.create_file(cache_key_one, contents=json.dumps(notices_one))
        fs.create_file(cache_key_two, contents=json.dumps(notices_two))

        notices.execute(args, parser)

    captured = capsys.readouterr()

    assert captured.err == ""
    assert "Retrieving" in captured.out
    assert mesg_one in captured.out
    assert mesg_two in captured.out


def test_main_notices_reads_from_expired_cache(fs, capsys, args_n_parser):
    """
    Test the full working path through the code when reading from cache instead of making
    an HTTP request.

    We have the "defaults" channel set and are expecting to receive messages
    from both of these channels.
    """
    args, parser = args_n_parser

    cache_dir = "./cache/"
    cache_filename_one = "defaults-pkgs-r-notices.json"
    cache_key_one = os.path.join(cache_dir, cache_filename_one)

    cache_filename_two = "defaults-pkgs-main-notices.json"
    cache_key_two = os.path.join(cache_dir, cache_filename_two)

    mesg_one = "Test One"
    mesg_two = "Test Two"

    created_at = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=14)

    notices_one = get_test_notices(created_at=created_at, mesg=mesg_one)
    notices_two = get_test_notices(created_at=created_at, mesg=mesg_two)

    mock_http_mesg = "Slightly different message, not from cache"

    with mock.patch("conda.notices.user_cache_dir") as user_cache_dir:
        user_cache_dir.return_value = cache_dir
        fs.create_file(cache_key_one, contents=json.dumps(notices_one))
        fs.create_file(cache_key_two, contents=json.dumps(notices_two))

        with mock.patch("conda.gateways.connection.session.CondaSession.get") as session_get:
            notices_one["notices"][0]["message"] = mock_http_mesg

            session_get.side_effect = [
                MockResponse(200, notices_one),  # /pkgs/main
                MockResponse(200, notices_two),  # /pkgs/r
            ]
            notices.execute(args, parser)

    captured = capsys.readouterr()

    assert captured.err == ""
    assert "Retrieving" in captured.out
    assert mock_http_mesg in captured.out


def test_main_notices_help(capsys):
    """Test to make sure help documentation has appropriate sections in it"""
    parser = conda_argparse.generate_parser()

    try:
        args = parser.parse_args(["notices", "--help"])
        notices.execute(args, parser)
    except SystemExit:
        pass

    captured = capsys.readouterr()

    assert captured.err == ""
    assert conda_argparse.NOTICES_HELP in captured.out
    assert conda_argparse.NOTICES_DESCRIPTION in captured.out
