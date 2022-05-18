# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import pytest

from conda.apps.notices import api
from conda.apps.notices.constants import NOTICES_DECORATOR_CONFIG_ERROR

from .conftest import add_resp_to_mock, notices_decorator_assert_message_in_stdout


@pytest.mark.parametrize("status_code", (200, 404, 500))
def test_display_notices_happy_path(
    status_code, capsys, notices_cache_dir, notices_mock_http_session_get
):
    """
    Happy path for displaying notices. We test two error codes to make sure we get
    display that we assume
    """
    messages = ("Test One", "Test Two")
    add_resp_to_mock(notices_mock_http_session_get, status_code, messages)

    api.display_notices()
    captured = capsys.readouterr()

    assert captured.err == ""

    for mesg in messages:
        if status_code < 300:
            assert mesg in captured.out
        else:
            assert mesg not in captured.out


def test_notices_decorator(capsys, notices_cache_dir, notices_mock_http_session_get):
    """
    Create a dummy function to wrap with our notices decorator
    """
    messages = ("Test One", "Test Two")
    add_resp_to_mock(notices_mock_http_session_get, 200, messages)
    dummy_mesg = "Dummy mesg"

    @api.notices
    def dummy(args, parser):
        print(dummy_mesg)

    notices_decorator_assert_message_in_stdout(
        capsys=capsys, messages=messages, dummy_mesg=dummy_mesg, dummy_func=dummy
    )


def test__conda_user_story__only_see_once(
    capsys, notices_cache_dir, notices_mock_http_session_get
):
    """
    As a conda user, I only want to see a channel notice once while running
    commands like, 'install', 'update', or 'create'.
    """
    messages = ("Test One", "Test Two")
    dummy_mesg = "Dummy Mesg"
    add_resp_to_mock(notices_mock_http_session_get, 200, messages)

    @api.notices
    def dummy(args, parser):
        print(dummy_mesg)

    notices_decorator_assert_message_in_stdout(
        capsys=capsys, messages=messages, dummy_mesg=dummy_mesg, dummy_func=dummy
    )

    notices_decorator_assert_message_in_stdout(
        capsys=capsys, messages=messages, dummy_mesg=dummy_mesg, dummy_func=dummy, not_in=True
    )


def test__conda_user_story__disable_notices(
    capsys, notices_cache_dir, notices_mock_http_session_get, disable_channel_notices
):
    """
    As a conda user, if I disable channel notifications in my .condarc file,
    I do not want to see notifications while running commands like,  "install",
    "update" or "create".
    """
    messages = ("Test One", "Test Two")
    dummy_mesg = "Dummy Mesg"
    add_resp_to_mock(notices_mock_http_session_get, 200, messages)

    @api.notices
    def dummy(args, parser):
        print(dummy_mesg)

    notices_decorator_assert_message_in_stdout(
        capsys=capsys, messages=messages, dummy_mesg=dummy_mesg, dummy_func=dummy, not_in=True
    )


def test__conda_user_story__no_ansi_colors(
    capsys, notices_cache_dir, notices_mock_http_session_get
):
    """
    As a conda user, when I use the '--no-ansi-colors' flag, I do not want
    to see colored output in my terminal.
    """


def test__channel_owner_story__correct_message_order(
    capsys, notices_cache_dir, notices_mock_http_session_get
):
    """
    As a channel owner, I want to make sure my users see the most urgent
    messages first.  (could be done by ordering in the notices.json).
    """


def test__developer_story__useful_error_message(
    capsys, notices_cache_dir, notices_mock_http_session_get
):
    """
    As a developer, if I improperly use the "notices" decorator, I want
    to see a helpful error message.
    """

    @api.notices
    def dummy():
        print("Dummy Test")

    dummy()

    captured = capsys.readouterr()

    assert NOTICES_DECORATOR_CONFIG_ERROR in captured.err
