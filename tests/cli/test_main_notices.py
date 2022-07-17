# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import datetime

import pytest

from conda.base.context import context
from conda.cli import main_notices as notices
from conda.cli import conda_argparse
from conda.testing.notices.helpers import (
    add_resp_to_mock,
    create_notice_cache_files,
    get_test_notices,
    get_notice_cache_filenames,
)


@pytest.mark.parametrize("status_code", (200, 404))
def test_main_notices(
    status_code,
    capsys,
    conda_notices_args_n_parser,
    notices_cache_dir,
    notices_mock_http_session_get,
):
    """
    Test the full working path through the code. We vary the test based on the status code
    we get back from the server.

    We have the "defaults" channel set and are expecting to receive messages
    from both of these channels.
    """
    args, parser = conda_notices_args_n_parser
    messages = ("Test One", "Test Two")
    messages_json = get_test_notices(messages)
    add_resp_to_mock(notices_mock_http_session_get, status_code, messages_json)

    notices.execute(args, parser)

    captured = capsys.readouterr()

    assert captured.err == ""
    assert "Retrieving" in captured.out

    for message in messages:
        if status_code < 300:
            assert message in captured.out
        else:
            assert message not in captured.out


def test_main_notices_reads_from_cache(
    capsys, conda_notices_args_n_parser, notices_cache_dir, notices_mock_http_session_get
):
    """
    Test the full working path through the code when reading from cache instead of making
    an HTTP request.

    We have the "defaults" channel set and are expecting to receive messages
    from both of these channels.
    """
    args, parser = conda_notices_args_n_parser
    messages = ("Test One", "Test Two")
    cache_files = get_notice_cache_filenames(context)

    messages_json_seq = tuple(get_test_notices(messages) for _ in cache_files)
    create_notice_cache_files(notices_cache_dir, cache_files, messages_json_seq)

    notices.execute(args, parser)

    captured = capsys.readouterr()

    assert captured.err == ""
    assert "Retrieving" in captured.out

    for message in messages:
        assert message in captured.out


def test_main_notices_reads_from_expired_cache(
    capsys, conda_notices_args_n_parser, notices_cache_dir, notices_mock_http_session_get
):
    """
    Test the full working path through the code when reading from cache instead of making
    an HTTP request.

    We have the "defaults" channel set and are expecting to receive messages
    from both of these channels.
    """
    args, parser = conda_notices_args_n_parser

    messages = ("Test One", "Test Two")
    messages_different = ("With different value one", "With different value two")
    created_at = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=14)
    cache_files = get_notice_cache_filenames(context)

    # Cache first version of notices, with a cache date we know is expired
    messages_json_seq = tuple(
        get_test_notices(messages, created_at=created_at) for _ in cache_files
    )
    create_notice_cache_files(notices_cache_dir, cache_files, messages_json_seq)

    # Force a different response, so we know we actually made a mock HTTP call to get
    # different messages
    messages_different_json = get_test_notices(messages_different)
    add_resp_to_mock(
        notices_mock_http_session_get, status_code=200, messages_json=messages_different_json
    )

    notices.execute(args, parser)

    captured = capsys.readouterr()

    assert captured.err == ""
    assert "Retrieving" in captured.out

    for message in messages_different:
        assert message in captured.out


def test_main_notices_handles_bad_expired_at_field(
    capsys, conda_notices_args_n_parser, notices_cache_dir, notices_mock_http_session_get
):
    """
    This test ensures that an incorrectly defined `notices.json` file doesn't completely break
    our notices subcommand.
    """
    args, parser = conda_notices_args_n_parser

    message = "testing"
    level = "info"
    message_id = "1234"
    cache_file = "defaults-pkgs-main-notices.json"

    bad_notices_json = {
        "notices": [
            {
                "message": message,
                "created_at": datetime.datetime.now().isoformat(),
                "level": level,
                "id": message_id,
            }
        ]
    }
    add_resp_to_mock(
        notices_mock_http_session_get, status_code=200, messages_json=bad_notices_json
    )

    create_notice_cache_files(notices_cache_dir, [cache_file], [bad_notices_json])

    notices.execute(args, parser)

    captured = capsys.readouterr()

    assert captured.err == ""
    assert "Retrieving" in captured.out

    assert message in captured.out


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
