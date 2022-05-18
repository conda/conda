# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

import datetime
import uuid
import json
from pathlib import Path
from typing import Literal, TypedDict, Optional, Sequence

import mock
import pytest

from conda.auxlib.ish import dals
from conda.base.constants import NOTICES_CACHE_SUBDIR
from conda.base.context import reset_context, context
from conda.common.configuration import YamlRawParameter
from conda.common.compat import odict
from conda.common.serialize import yaml_round_trip_load
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


def add_resp_to_mock(
    mock_session: mock.MagicMock, status_code: int, messages: Sequence[str]
) -> None:
    """Adds any number of MockResponse to MagicMock object as side_effects"""
    side_effect = []

    for mesg in messages:
        side_effect.append(MockResponse(status_code, get_test_notices(mesg=mesg)))

    mock_session.side_effect = side_effect


def create_notice_cache_files(
    cache_dir: Path,
    cache_files: Sequence[str],
    messages: Sequence[str],
    created_at: Optional[datetime.datetime] = None,
) -> None:
    """Creates the cache files that we use in tests"""
    for mesg, file in zip(messages, cache_files):
        cache_key = cache_dir.joinpath(file)
        notice = get_test_notices(mesg=mesg, created_at=created_at)
        with open(cache_key, "w") as fp:
            json.dump(notice, fp)


class DummyObject:
    no_ansi_colors = True


def notices_decorator_assert_message_in_stdout(
    capsys, messages, dummy_mesg, dummy_func, not_in=False
):
    """
    Tests a run of the notices decorator where we expect to see the messages
    print to stdout.
    """
    dummy_func(DummyObject, None)
    captured = capsys.readouterr()

    assert captured.err == ""
    assert dummy_mesg in captured.out

    for mesg in messages:
        if not_in:
            assert mesg not in captured.out
        else:
            assert mesg in captured.out


class MockResponse:
    def __init__(self, status_code, json_data):
        self.status_code = status_code
        self.json_data = json_data

    def json(self):
        return self.json_data


@pytest.fixture(scope="function")
def notices_cache_dir(tmpdir):
    """
    Fixture that creates the notices cache dir while also mocking
    out a call to user_cache_dir.
    """
    with mock.patch("conda.apps.notices.cache.user_cache_dir") as user_cache_dir:
        user_cache_dir.return_value = tmpdir
        cache_dir = Path(tmpdir).joinpath(NOTICES_CACHE_SUBDIR)
        cache_dir.mkdir(parents=True, exist_ok=True)

        yield cache_dir


@pytest.fixture(scope="function")
def notices_mock_http_session_get():
    with mock.patch("conda.gateways.connection.session.CondaSession.get") as session_get:
        yield session_get


@pytest.fixture(scope="function")
def conda_notices_args_n_parser():
    parser = conda_argparse.generate_parser()
    args = parser.parse_args(["notices"])

    return args, parser


@pytest.fixture(scope="function")
def disable_channel_notices():
    """
    Fixture that will set "context.disable_channel_notices" to True and then set
    it back to its original value.

    This is also a good example of how to override values in the context object.
    """
    yaml_str = dals(
        """
    disable_channel_notices: true
    """
    )
    reset_context(())
    rd = odict(
        testdata=YamlRawParameter.make_raw_parameters("testdata", yaml_round_trip_load(yaml_str))
    )
    context._set_raw_data(rd)

    yield

    reset_context()
