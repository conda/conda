# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

import datetime
import uuid
from typing import TypedDict, Literal

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


def get_test_notice(
    created_at: datetime.datetime, info: NoticeLevel, expiry: int, interval: int
) -> Notice:
    return {
        "id": str(uuid.uuid4()),
        "message": "testing message testing testing testing",
        "level": info,
        "created_at": created_at,
        "expiry": expiry,
        "interval": interval,
    }


NOTIFICATIONS_EXAMPLE = {
    "notices": [
        {
            "id": "1cd1d8e5-d96c-42d1-9c29-e8120ad80823",
            "message": "Here is an example message that will be displayed to users",
            "level": "info",
            "created_at": "2022-04-26T11:50:34+00:00",
            "expiry": 604800,
            "interval": 604800,
        }
    ]
}


def test_main_notices_happy_path_no_args(capsys):
    """Test the full working path through the code"""
    parser = conda_argparse.generate_parser()
    args = parser.parse_args(["notices"])

    notices.execute(args, parser)

    captured = capsys.readouterr()

    assert captured.err == ""
    assert captured.out == ""


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
