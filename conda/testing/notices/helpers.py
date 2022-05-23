# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

import datetime
import uuid
import json
from itertools import chain
from pathlib import Path
from typing import TypedDict, Optional, Sequence

import mock


class Notice(TypedDict):
    id: str
    message: str
    level: str
    created_at: datetime.datetime
    expiry: int
    interval: int


DEFAULT_NOTICE_MESG = "Here is an example message that will be displayed to users"


def get_test_notices(
    messages: Sequence[str],
    level: Optional[str] = "info",
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
            for mesg in messages
        )
    }


def add_resp_to_mock(
    mock_session: mock.MagicMock,
    status_code: int,
    messages: Sequence[str],
    raise_exc: bool = False,
) -> None:
    """Adds any number of MockResponse to MagicMock object as side_effects"""

    def forever_404():
        while True:
            yield MockResponse(404, {})

    def one_200():
        yield MockResponse(status_code, get_test_notices(messages), raise_exc=raise_exc)

    chn = chain(one_200(), forever_404())
    mock_session.side_effect = tuple(next(chn) for _ in range(100))


def create_notice_cache_files(
    cache_dir: Path,
    cache_files: Sequence[str],
    messages: Sequence[str],
    created_at: Optional[datetime.datetime] = None,
) -> None:
    """Creates the cache files that we use in tests"""
    for mesg, file in zip(messages, cache_files):
        cache_key = cache_dir.joinpath(file)
        notice = get_test_notices((mesg,), created_at=created_at)
        with open(cache_key, "w") as fp:
            json.dump(notice, fp)


class DummyArgs:
    """
    Dummy object that sets all kwargs as object properties
    """

    def __init__(self, **kwargs):
        self.no_ansi_colors = True

        for key, val in kwargs.items():
            setattr(self, key, val)


def notices_decorator_assert_message_in_stdout(
    captured, messages: Sequence[str], dummy_mesg: Optional[str] = None, not_in: bool = False
):
    """
    Tests a run of notices decorator where we expect to see the messages
    print to stdout.
    """
    assert captured.err == ""
    assert dummy_mesg in captured.out

    for mesg in messages:
        if not_in:
            assert mesg not in captured.out
        else:
            assert mesg in captured.out


class MockResponse:
    def __init__(self, status_code, json_data, raise_exc=False):
        self.status_code = status_code
        self.json_data = json_data
        self.raise_exc = raise_exc

    def json(self):
        if self.raise_exc:
            raise ValueError("Error")
        return self.json_data
