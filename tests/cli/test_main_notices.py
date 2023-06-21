# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import datetime
import glob
import hashlib
import os
from unittest import mock

import pytest
from pytest import MonkeyPatch
from pytest_mock import MockerFixture

from conda.base.constants import NOTICES_DECORATOR_DISPLAY_INTERVAL
from conda.base.context import context, reset_context
from conda.cli import conda_argparse
from conda.cli import main_notices as notices
from conda.notices import fetch
from conda.testing import CondaCLIFixture
from conda.testing.helpers import run_inprocess_conda_command as run
from conda.testing.notices.helpers import (
    add_resp_to_mock,
    create_notice_cache_files,
    get_notice_cache_filenames,
    get_test_notices,
    offset_cache_file_mtime,
)


@pytest.fixture
def env_one(notices_cache_dir):
    env_name = "env-one"

    # Setup
    run(f"conda create -n {env_name} -y --offline")

    yield env_name

    # Teardown
    run(f"conda remove --all -y -n {env_name}", disallow_stderr=False)


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
    capsys,
    conda_notices_args_n_parser,
    notices_cache_dir,
    notices_mock_http_session_get,
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
    capsys,
    conda_notices_args_n_parser,
    notices_cache_dir,
    notices_mock_http_session_get,
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
    created_at = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(
        days=14
    )
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
        notices_mock_http_session_get,
        status_code=200,
        messages_json=messages_different_json,
    )

    notices.execute(args, parser)

    captured = capsys.readouterr()

    assert captured.err == ""
    assert "Retrieving" in captured.out

    for message in messages_different:
        assert message in captured.out


def test_main_notices_handles_bad_expired_at_field(
    capsys,
    conda_notices_args_n_parser,
    notices_cache_dir,
    notices_mock_http_session_get,
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


def test_cache_names_appear_as_expected(
    capsys,
    conda_notices_args_n_parser,
    notices_cache_dir,
    notices_mock_http_session_get,
):
    """This is a test to make sure the cache filenames appear as we expect them to."""
    with mock.patch(
        "conda.notices.core.get_channel_name_and_urls"
    ) as get_channel_name_and_urls:
        channel_url = "http://localhost/notices.json"
        get_channel_name_and_urls.return_value = ((channel_url, "channel_name"),)
        expected_cache_filename = (
            f"{hashlib.sha256(channel_url.encode()).hexdigest()}.json"
        )

        args, parser = conda_notices_args_n_parser
        messages = ("Test One", "Test Two")
        messages_json = get_test_notices(messages)
        add_resp_to_mock(notices_mock_http_session_get, 200, messages_json)

        notices.execute(args, parser)

        captured = capsys.readouterr()

        # Test to make sure everything looks normal for our notices output
        assert captured.err == ""
        assert "Retrieving" in captured.out

        for message in messages:
            assert message in captured.out

        # Test to make sure the cache files are showing up as we expect them to
        cache_files = glob.glob(f"{notices_cache_dir}/*.json")

        assert len(cache_files) == 1
        assert os.path.basename(cache_files[0]) == expected_cache_filename


def test_notices_appear_once_when_running_decorated_commands(
    tmpdir, env_one, notices_cache_dir
):
    """
    As a user, I want to make sure when I run commands like "install" and "update"
    that the channels are only appearing according to the specified interval in:
        conda.base.constants.NOTICES_DECORATOR_DISPLAY_INTERVAL

    This should only be once per 24 hours according to the current setting.

    To ensure this test runs appropriately, we rely on using a pass-thru mock
    of the `conda.notices.fetch.get_notice_responses` function. If this function
    was called and called correctly we can assume everything is working well.

    This test intentionally does not make any external network calls and never should.
    """
    offset_cache_file_mtime(NOTICES_DECORATOR_DISPLAY_INTERVAL + 100)

    with mock.patch(
        "conda.notices.fetch.get_notice_responses", wraps=fetch.get_notice_responses
    ) as fetch_mock:
        # First run of install; notices should be retrieved; it's okay that this function fails
        # to install anything.
        run(
            f"conda install -n {env_one} -c local --override-channels -y does_not_exist",
            disallow_stderr=False,
        )

        # make sure our fetch function was called correctly
        fetch_mock.assert_called_once()
        args, kwargs = fetch_mock.call_args

        # If we did this correctly, args should be an empty list because our local channel has not
        # been initialized. This causes no network traffic because there are no URLs to fetch which
        # is what we want.
        assert [
            [(url, name) for url, name in arg if name != "local"] for arg in args
        ] == [[]]

        # Reset our mock for another call to "conda install"
        fetch_mock.reset_mock()

        # Second run of install; notices should not be retrieved
        run(
            f"conda install -n {env_one} -c local --override-channels -y does_not_exist",
            disallow_stderr=False,
        )

        fetch_mock.assert_not_called()


def test_notices_work_with_s3_channel(notices_cache_dir, notices_mock_http_session_get):
    """As a user, I want notices to be correctly retrieved from channels with s3 URLs."""
    s3_channel = "s3://conda-org"
    messages = ("Test One", "Test Two")
    messages_json = get_test_notices(messages)
    add_resp_to_mock(notices_mock_http_session_get, 200, messages_json)

    run(f"conda notices -c {s3_channel} --override-channels")

    notices_mock_http_session_get.assert_called_once()
    args, kwargs = notices_mock_http_session_get.call_args

    arg_1, *_ = args
    assert arg_1 == "s3://conda-org/notices.json"


def test_notices_does_not_interrupt_command_on_failure(
    notices_cache_dir, notices_mock_http_session_get
):
    """
    As a user, when I run conda in an environment where notice cache files might not be readable or
    writable, I still want commands to run and not end up failing.
    """
    env_name = "testenv"
    error_message = "Can't touch this"

    with mock.patch("conda.notices.cache.open") as mock_open, mock.patch(
        "conda.notices.core.logger.error"
    ) as mock_logger:
        mock_open.side_effect = [PermissionError(error_message)]
        _, _, exit_code = run(
            f"conda create -n {env_name} -y -c local --override-channels"
        )

        assert exit_code is None

        assert mock_logger.call_args == mock.call(
            f"Unable to open cache file: {error_message}"
        )

    _, _, exit_code = run(f"conda env remove -n {env_name}")

    assert exit_code is None


def test_notices_cannot_read_cache_files(
    notices_cache_dir,
    notices_mock_http_session_get,
    conda_cli: CondaCLIFixture,
    mocker: MockerFixture,
):
    """
    As a user, when I run `conda notices` and the cache file cannot be read or written, I want
    to see an error message.
    """
    error_message = "Can't touch this"
    mock_open = mocker.patch(
        "builtins.open", side_effect=PermissionError(error_message)
    )

    with pytest.raises(PermissionError, match=error_message):
        conda_cli("notices", "--channel", "local", "--override-channels")
