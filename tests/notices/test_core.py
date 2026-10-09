# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import pytest

from conda.base.context import reset_context
from conda.models.channel import Channel
from conda.notices import core as notices
from conda.notices.dispatch import NoticeBus
from conda.testing.notices.helpers import (
    DummyArgs,
    add_resp_to_mock,
    get_test_notices,
    notices_decorator_assert_message_in_stdout,
)


def _defaults_notice_urls():
    return notices.get_channel_name_and_urls([Channel("defaults")])


@pytest.mark.parametrize("status_code", (200, 404, 500))
def test_display_notices_happy_path(
    status_code,
    capsys,
    notices_cache_dir,
    notices_mock_fetch_get_session,
    monkeypatch,
):
    """Happy path for displaying notices via the bus."""
    monkeypatch.setenv("CONDA_CHANNELS", "defaults")
    reset_context()
    messages = ("Test One", "Test Two")
    messages_json = get_test_notices(messages)
    add_resp_to_mock(notices_mock_fetch_get_session, status_code, messages_json)

    NoticeBus.clear()
    notices.broadcast_channel_notices(_defaults_notice_urls(), force=True)
    bulletin = NoticeBus.consume()
    notices.show_notices(bulletin, always_show_viewed=True)
    captured = capsys.readouterr()

    assert captured.err == ""

    for message in messages:
        if status_code < 300:
            assert message in captured.out
        else:
            assert message not in captured.out

    # Second display should show the same notices again (always_show_viewed=True)
    NoticeBus.clear()
    notices.broadcast_channel_notices(_defaults_notice_urls(), force=True)
    bulletin = NoticeBus.consume()
    notices.show_notices(bulletin, always_show_viewed=True)
    captured = capsys.readouterr()

    assert captured.err == ""

    for message in messages:
        if status_code < 300:
            assert message in captured.out
        else:
            assert message not in captured.out


def test_notices_decorator(
    capsys, notices_cache_dir, notices_mock_fetch_get_session, monkeypatch
):
    """
    Exercise the ``do_call`` notices sandwich via ``run_notices_sandwich``.

    Channel notices are broadcast during the command (simulating ``RepodataFetch``).
    """
    monkeypatch.setenv("CONDA_CHANNELS", "defaults")
    reset_context()
    messages = ("Test One", "Test Two")
    messages_json = get_test_notices(messages)
    add_resp_to_mock(notices_mock_fetch_get_session, 200, messages_json)
    dummy_mesg = "Dummy mesg"

    def dummy(args, parser):
        notices.broadcast_channel_notices(_defaults_notice_urls(), force=True)
        print(dummy_mesg)

    dummy_args = DummyArgs(toves="slithy")
    notices.run_notices_sandwich(lambda: dummy(dummy_args, None))

    captured = capsys.readouterr()

    notices_decorator_assert_message_in_stdout(
        captured,
        messages=messages,
        dummy_mesg=dummy_mesg,
    )


def test__conda_user_story__only_see_once(
    capsys,
    notices_cache_dir,
    notices_mock_fetch_get_session,
    monkeypatch,
):
    """
    As a conda user, I only want to see a channel notice once while running
    commands like, 'install', 'update', or 'create'.
    """
    monkeypatch.setenv("CONDA_CHANNELS", "defaults")
    reset_context()
    messages = ("Test One",)
    dummy_mesg = "Dummy Mesg"
    messages_json = get_test_notices(messages)
    add_resp_to_mock(notices_mock_fetch_get_session, 200, messages_json)

    def dummy(args, parser):
        notices.broadcast_channel_notices(_defaults_notice_urls(), force=True)
        print(dummy_mesg)

    dummy_args = DummyArgs()
    notices.run_notices_sandwich(lambda: dummy(dummy_args, None))

    captured = capsys.readouterr()
    notices_decorator_assert_message_in_stdout(
        captured, messages=messages, dummy_mesg=dummy_mesg
    )

    # Second run: notices should not appear again (already viewed)
    notices.run_notices_sandwich(lambda: dummy(dummy_args, None))
    captured = capsys.readouterr()
    notices_decorator_assert_message_in_stdout(
        captured, messages=messages, dummy_mesg=dummy_mesg, not_in=True
    )


def test__conda_user_story__disable_notices(
    capsys,
    notices_cache_dir,
    notices_mock_fetch_get_session,
    monkeypatch,
):
    """
    As a conda user, if I disable channel notifications in my .condarc file,
    I do not want to see notifications while running commands like,  "install",
    "update" or "create".
    """
    monkeypatch.setenv("CONDA_NUMBER_CHANNEL_NOTICES", "0")
    monkeypatch.setenv("CONDA_CHANNELS", "defaults")
    reset_context()
    messages = ("Test One", "Test Two")
    dummy_mesg = "Dummy Mesg"
    messages_json = get_test_notices(messages)
    add_resp_to_mock(notices_mock_fetch_get_session, 200, messages_json)

    def dummy(args, parser):
        print(dummy_mesg)

    dummy_args = DummyArgs()
    notices.run_notices_sandwich(lambda: dummy(dummy_args, None))
    captured = capsys.readouterr()

    notices_decorator_assert_message_in_stdout(
        captured, messages=messages, dummy_mesg=dummy_mesg, not_in=True
    )


def test__conda_user_story__more_notices_message(
    capsys,
    notices_cache_dir,
    notices_mock_fetch_get_session,
    monkeypatch,
):
    """
    As a conda user, I want to see a message telling me there are more notices
    if there are more to display.
    """
    monkeypatch.setenv("CONDA_CHANNELS", "defaults")
    reset_context()
    messages = tuple(f"Test {idx}" for idx in range(1, 11, 1))
    messages_json = get_test_notices(messages)
    add_resp_to_mock(notices_mock_fetch_get_session, 200, messages_json)

    def dummy(args, parser):
        notices.broadcast_channel_notices(_defaults_notice_urls(), force=True)

    notices.run_notices_sandwich(lambda: dummy(None, None))

    captured = capsys.readouterr()

    assert captured.err == ""
    assert "There are 5 more messages" in captured.out


def test_broadcast_channel_notices_respects_fetch_interval(
    notices_cache_dir,
    notices_mock_fetch_get_session,
    monkeypatch,
    mocker,
):
    """Channel notice fetches are skipped until the fetch interval elapses."""
    from conda.notices import fetch as notices_fetch

    monkeypatch.setenv("CONDA_CHANNELS", "defaults")
    reset_context()
    messages_json = get_test_notices(("Test One",))
    add_resp_to_mock(notices_mock_fetch_get_session, 200, messages_json)

    cache_file = notices_cache_dir / "notices.cache"
    cache_file.touch()

    fetch_mock = mocker.patch(
        "conda.notices.fetch.get_notice_responses",
        wraps=notices_fetch.get_notice_responses,
    )

    NoticeBus.clear()
    notices.broadcast_channel_notices(_defaults_notice_urls())
    fetch_mock.assert_not_called()

    notices.broadcast_channel_notices(_defaults_notice_urls(), force=True)
    fetch_mock.assert_called_once()


def test_broadcast_channel_notices_once_per_command(
    notices_cache_dir,
    notices_mock_fetch_get_session,
    monkeypatch,
    mocker,
):
    """Within one command, only the first non-force broadcast fetches."""
    from conda.base.constants import NOTICES_DECORATOR_DISPLAY_INTERVAL
    from conda.notices import fetch as notices_fetch
    from conda.testing.notices.helpers import offset_cache_file_mtime

    monkeypatch.setenv("CONDA_CHANNELS", "defaults")
    reset_context()
    messages_json = get_test_notices(("Test One",))
    add_resp_to_mock(notices_mock_fetch_get_session, 200, messages_json)
    offset_cache_file_mtime(NOTICES_DECORATOR_DISPLAY_INTERVAL + 100)

    fetch_mock = mocker.patch(
        "conda.notices.fetch.get_notice_responses",
        wraps=notices_fetch.get_notice_responses,
    )

    NoticeBus.clear()
    notices.broadcast_channel_notices(_defaults_notice_urls())
    notices.broadcast_channel_notices(_defaults_notice_urls())
    fetch_mock.assert_called_once()
