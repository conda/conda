# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import datetime

import pytest

from conda.cli import main_notices as notices
from conda.cli import conda_argparse

from tests.notices.conftest import add_resp_to_mock, create_notice_cache_files


@pytest.fixture(scope="function")
def args_n_parser():
    parser = conda_argparse.generate_parser()
    args = parser.parse_args(["notices"])

    return args, parser


@pytest.mark.parametrize("status_code", (200, 404))
def test_main_notices(
    status_code, capsys, args_n_parser, notices_cache_dir, notices_mock_http_session_get
):
    """
    Test the full working path through the code. We vary the test based on the status code
    we get back from the server.

    We have the "defaults" channel set and are expecting to receive messages
    from both of these channels.
    """
    args, parser = args_n_parser
    messages = ("Test One", "Test Two")
    add_resp_to_mock(notices_mock_http_session_get, status_code, messages)

    notices.execute(args, parser)

    captured = capsys.readouterr()

    assert captured.err == ""
    assert "Retrieving" in captured.out

    for mesg in messages:
        if status_code < 300:
            assert mesg in captured.out
        else:
            assert mesg not in captured.out


def test_main_notices_reads_from_cache(capsys, args_n_parser, notices_cache_dir):
    """
    Test the full working path through the code when reading from cache instead of making
    an HTTP request.

    We have the "defaults" channel set and are expecting to receive messages
    from both of these channels.
    """
    args, parser = args_n_parser
    messages = ("Test One", "Test Two")
    cache_files = ("defaults-pkgs-r-notices.json", "defaults-pkgs-main-notices.json")

    create_notice_cache_files(notices_cache_dir, cache_files, messages)

    notices.execute(args, parser)

    captured = capsys.readouterr()

    assert captured.err == ""
    assert "Retrieving" in captured.out

    for mesg in messages:
        assert mesg in captured.out


def test_main_notices_reads_from_expired_cache(
    capsys, args_n_parser, notices_cache_dir, notices_mock_http_session_get
):
    """
    Test the full working path through the code when reading from cache instead of making
    an HTTP request.

    We have the "defaults" channel set and are expecting to receive messages
    from both of these channels.
    """
    args, parser = args_n_parser

    messages = ("Test One", "Test Two")
    messages_different = ("With different value one", "With different value two")
    cache_files = ("defaults-pkgs-r-notices.json", "defaults-pkgs-main-notices.json")
    created_at = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=14)

    # Cache first version of notices, with a cache date we know is expired
    create_notice_cache_files(notices_cache_dir, cache_files, messages, created_at=created_at)

    # Force a difference response, so we know we actually made a mock HTTP call to get
    # different messages
    add_resp_to_mock(notices_mock_http_session_get, status_code=200, messages=messages_different)

    notices.execute(args, parser)

    captured = capsys.readouterr()

    assert captured.err == ""
    assert "Retrieving" in captured.out

    for mesg in messages_different:
        assert mesg in captured.out


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
