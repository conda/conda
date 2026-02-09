# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import datetime
import glob
import hashlib
import json
import os
from typing import TYPE_CHECKING

import pytest

from conda.base.constants import NOTICES_DECORATOR_DISPLAY_INTERVAL
from conda.base.context import context, reset_context
from conda.cli import conda_argparse
from conda.cli import main_notices as notices
from conda.common.url import path_to_url
from conda.exceptions import CondaError, PackagesNotFoundError
from conda.notices import fetch
from conda.testing.notices.helpers import (
    add_resp_to_mock,
    create_notice_cache_files,
    get_notice_cache_filenames,
    get_test_notices,
    offset_cache_file_mtime,
)

if TYPE_CHECKING:
    from pytest import MonkeyPatch
    from pytest_mock import MockerFixture

    from conda.testing.fixtures import CondaCLIFixture, PathFactoryFixture


@pytest.fixture
def env_one(notices_cache_dir, conda_cli: CondaCLIFixture):
    env_name = "env-one"

    # Setup
    conda_cli("create", "--name", env_name, "--yes", "--offline")

    yield env_name

    # Teardown
    conda_cli("remove", "--name", env_name, "--yes", "--all")


@pytest.mark.parametrize("status_code", (200, 404))
def test_main_notices(
    status_code,
    capsys,
    conda_notices_args_n_parser,
    notices_cache_dir,
    notices_mock_fetch_get_session,
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
    add_resp_to_mock(notices_mock_fetch_get_session, status_code, messages_json)

    notices.execute(args, parser)

    captured = capsys.readouterr()

    assert captured.err == ""
    assert "Retrieving" in captured.out

    for message in messages:
        if status_code < 300:
            assert message in captured.out
        else:
            assert message not in captured.out


def test_main_notices_json(
    capsys,
    conda_notices_args_n_parser,
    notices_cache_dir,
    notices_mock_fetch_get_session,
    monkeypatch: MonkeyPatch,
    mocker: MockerFixture,
    status_code=200,
):
    channel_str = "test"
    mocker.patch(
        "conda.base.context.Context.channels",
        new_callable=mocker.PropertyMock,
        return_value=(channel_str,),
    )
    args, parser = conda_notices_args_n_parser
    messages = ("Test One", "Test Two")
    messages_json = get_test_notices(messages)
    json_list = messages_json.get("notices")

    for item in json_list:
        item.update({"channel_name": channel_str, "interval": "null"})

    messages_json = {"notices": json_list}
    add_resp_to_mock(notices_mock_fetch_get_session, 200, messages_json)

    monkeypatch.setenv("CONDA_JSON", "true")
    reset_context()
    assert context.json

    notices.execute(args, parser)

    captured = capsys.readouterr()
    json_data = json.loads(captured.out)
    assert messages_json.get("notices") == json_data


def test_main_notices_reads_from_cache(
    capsys,
    conda_notices_args_n_parser,
    notices_cache_dir,
    notices_mock_fetch_get_session,
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
    notices_mock_fetch_get_session,
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
        notices_mock_fetch_get_session,
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
    notices_mock_fetch_get_session,
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
        notices_mock_fetch_get_session,
        status_code=200,
        messages_json=bad_notices_json,
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
    assert "Retrieve latest channel notifications." in captured.out
    assert "maintainers have the option of setting messages" in captured.out


def test_cache_names_appear_as_expected(
    capsys,
    conda_notices_args_n_parser,
    notices_cache_dir,
    notices_mock_fetch_get_session,
    mocker: MockerFixture,
):
    """This is a test to make sure the cache filenames appear as we expect them to."""
    channel_url = "http://localhost/notices.json"
    mocker.patch(
        "conda.notices.core.get_channel_name_and_urls",
        return_value=[(channel_url, "channel_name")],
    )

    expected_cache_filename = f"{hashlib.sha256(channel_url.encode()).hexdigest()}.json"

    args, parser = conda_notices_args_n_parser
    messages = ("Test One", "Test Two")
    messages_json = get_test_notices(messages)
    add_resp_to_mock(notices_mock_fetch_get_session, 200, messages_json)

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
    tmpdir,
    notices_cache_dir,
    conda_cli: CondaCLIFixture,
    mocker: MockerFixture,
    test_recipes_channel,
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
    env_one = "notices_test"
    offset_cache_file_mtime(NOTICES_DECORATOR_DISPLAY_INTERVAL + 100)

    fetch_mock = mocker.patch(
        "conda.notices.fetch.get_notice_responses", wraps=fetch.get_notice_responses
    )

    # First run of install; notices should be retrieved; it's okay that this function fails
    # to install anything.
    conda_cli("create", "--name", env_one, "--yes", "--channel", test_recipes_channel)

    # make sure our fetch function was called correctly
    fetch_mock.assert_called_once()
    args, kwargs = fetch_mock.call_args

    # If we did this correctly, args should be an empty list because our local channel has not
    # been initialized. This causes no network traffic because there are no URLs to fetch which
    # is what we want.
    notices_path = test_recipes_channel / "notices.json"
    notices_url = path_to_url(str(notices_path))
    assert args == ([(notices_url, "test-recipes")],)

    # Reset our mock for another call to "conda install"
    fetch_mock.reset_mock()

    # Second run of install; notices should not be retrieved; also okay that this fails.
    conda_cli("remove", "--name", env_one, "--yes", "--all")

    fetch_mock.assert_not_called()


def test_notices_work_with_s3_channel(
    notices_cache_dir,
    notices_mock_fetch_get_session,
    conda_cli: CondaCLIFixture,
):
    """As a user, I want notices to be correctly retrieved from channels with s3 URLs."""
    s3_channel = "s3://conda-org"
    messages = ("Test One", "Test Two")
    messages_json = get_test_notices(messages)
    add_resp_to_mock(notices_mock_fetch_get_session, 200, messages_json)

    conda_cli("notices", "--channel", s3_channel, "--override-channels")

    notices_mock_fetch_get_session().get.assert_called_once()
    args, kwargs = notices_mock_fetch_get_session().get.call_args

    arg_1, *_ = args
    assert arg_1 == "s3://conda-org/notices.json"


def test_notices_does_not_interrupt_command_on_failure(
    notices_cache_dir,
    notices_mock_fetch_get_session,
    conda_cli: CondaCLIFixture,
    mocker: MockerFixture,
    path_factory: PathFactoryFixture,
    test_recipes_channel,
):
    """
    As a user, when I run conda in an environment where notice cache files might not be readable or
    writable, I still want commands to run and not end up failing.
    """
    error_message = "Can't touch this"

    mocker.patch("conda.notices.cache.open", side_effect=PermissionError(error_message))
    mock_logger = mocker.patch("conda.notices.core.logger.error")

    prefix = path_factory()

    _, _, exit_code = conda_cli(
        "create",
        f"--prefix={prefix}",
        "--yes",
        f"--channel={test_recipes_channel}",
    )

    assert exit_code == 0

    assert mock_logger.call_args == mocker.call(
        f"Unable to open cache file: {error_message}"
    )


def test_notices_cannot_read_cache_files(
    notices_cache_dir,
    conda_cli: CondaCLIFixture,
    mocker: MockerFixture,
    test_recipes_channel,
):
    """
    As a user, when I run `conda notices` and the cache file cannot be read or written, I want
    to see an error message.
    """
    error_message = "Can't touch this"

    mocker.patch("conda.notices.cache.open", side_effect=PermissionError(error_message))

    with pytest.raises(
        CondaError, match=f"Unable to retrieve notices: {error_message}"
    ):
        conda_cli("notices", "--channel", test_recipes_channel)


def test_notices_shown_after_previous_command_error(
    notices_cache_dir,
    notices_mock_fetch_get_session,
    conda_cli: CondaCLIFixture,
    test_recipes_channel,
):
    """
    As a user, when I run a command that generates an error (e.g. trying to install a package that
    cannot be found), when notices are available, I want the subsequent run of the command to
    show them.

    Regression test for: https://github.com/conda/conda/issues/14072
    """
    env_one = "notices-test"

    messages = ("Test One",)
    messages_json = get_test_notices(messages)
    add_resp_to_mock(notices_mock_fetch_get_session, 200, messages_json)

    with pytest.raises(PackagesNotFoundError):
        conda_cli(
            "create",
            f"--name={env_one}",
            f"--channel={test_recipes_channel}",
            "--override-channels",
            "--yes",
            "package-does-not-exist",
        )

    messages = ("Test One",)
    messages_json = get_test_notices(messages)
    add_resp_to_mock(notices_mock_fetch_get_session, 200, messages_json)

    out, err, exc = conda_cli(
        "create",
        f"--name={env_one}",
        f"--channel={test_recipes_channel}",
        "--override-channels",
        "--yes",
    )

    assert "Test One" in out
