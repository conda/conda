# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from contextlib import nullcontext
from errno import EPIPE
from io import StringIO
from pathlib import Path

import pytest

from conda.exceptions import CondaError
from conda.plugins.reporter_backends.console import (
    ConsoleReporterRenderer,
    QuietSpinner,
    Spinner,
    TQDMProgressBar,
)


def test_console_reporter_renderer():
    """
    Tests the ``ConsoleReporterRenderer`` class
    """
    test_data = {"one": "value_one", "two": "value_two", "three": "value_three"}
    test_str = "a string value"
    expected_table_str = (
        "\n   one : value_one\n   two : value_two\n three : value_three\n\n"
    )
    console_reporter_renderer = ConsoleReporterRenderer()

    assert console_reporter_renderer.detail_view(test_data) == expected_table_str
    assert console_reporter_renderer.render(test_str) == test_str

    progress_bar = console_reporter_renderer.progress_bar(
        description="Test progress bar description", io_context_manager=nullcontext()
    )

    assert isinstance(progress_bar, TQDMProgressBar)

    progress_bar_context_manager = (
        console_reporter_renderer.progress_bar_context_manager()
    )
    assert isinstance(progress_bar_context_manager, nullcontext)


def test_console_reporter_renderer_envs_list(mocker):
    """
    Test for the case where a ``context.envs_dirs`` directory equals the prefix
    """
    mock_context = mocker.patch("conda.core.prefix_data.context")
    mock_context.envs_dirs = ["/tmp"]
    console_reporter_renderer = ConsoleReporterRenderer()

    output = console_reporter_renderer.envs_list(["/tmp/envs"])

    assert f"envs                     {Path('/tmp/envs')}" in output


def test_console_reporter_renderer_envs_list_output_false():
    """
    Test for the case when output=False; it should return an empty string
    """
    console_reporter_renderer = ConsoleReporterRenderer()

    output = console_reporter_renderer.envs_list(["/tmp/envs"], output=False)

    assert output == ""


def test_tqdm_progress_bar_os_error(mocker):
    """
    Test for the case where an OSError is raised on tqdm object creation
    """
    tqdm_mock = mocker.patch.object(TQDMProgressBar, "_tqdm")
    tqdm_mock.side_effect = OSError("test")

    with pytest.raises(OSError):
        TQDMProgressBar("test", nullcontext())


def test_tqdm_progress_bar_os_error_with_epipe_errno(mocker):
    """
    Test for the case where an OSError is raised on tqdm object creation and the error
    contains an errno that equals EPIPE
    """
    os_error = OSError("test")
    os_error.errno = EPIPE
    tqdm_mock = mocker.patch.object(TQDMProgressBar, "_tqdm")
    tqdm_mock.side_effect = os_error

    progress_bar = TQDMProgressBar("test", nullcontext())

    assert not progress_bar.enabled


def test_tqdm_progress_bar_update_to_os_error(mocker):
    """
    Test for the case where an OSError is raised when update_to is called
    """
    tqdm_mock = mocker.patch.object(TQDMProgressBar, "_tqdm")
    tqdm_mock().update.side_effect = OSError("test")

    with pytest.raises(OSError):
        progress_bar = TQDMProgressBar("test", nullcontext())
        progress_bar.update_to(0.5)


def test_tqdm_progress_bar_update_to_os_error_with_errno_epipe(mocker):
    """
    Test for the case where an OSError is raised when update_to is called and the OSError
    errno is set to EPIPE
    """
    os_error = OSError("test")
    os_error.errno = EPIPE
    tqdm_mock = mocker.patch.object(TQDMProgressBar, "_tqdm")
    tqdm_mock().update.side_effect = os_error

    progress_bar = TQDMProgressBar("test", nullcontext())
    progress_bar.update_to(0.5)
    progress_bar.update_to(0.8)
    progress_bar.refresh()
    progress_bar.close()

    assert not progress_bar.enabled


def test_spinner(capsys):
    """
    Ensure that the ``Spinner`` works by producing the expected output.
    """
    with Spinner("Test message"):
        pass

    capture = capsys.readouterr()

    assert "Test message" in capture.out
    assert "done" in capture.out


def test_spinner_with_error(capsys):
    """
    Ensure that the ``Spinner`` works by producing the expected output
    when an exception is encountered.
    """
    try:
        with Spinner("Test message"):
            raise Exception("Test")
    except Exception as exc:
        assert str(exc) == "Test"

    capture = capsys.readouterr()

    assert "Test message" in capture.out
    assert "failed" in capture.out


def test_spinner_with_os_error_errno_epipe(mocker, capsys):
    """
    Ensure that the spinner stops when OSError of type EPIPE is encountered
    """
    os_error = OSError("test")
    os_error.errno = EPIPE
    tqdm_mock = mocker.patch("conda.plugins.reporter_backends.console.sleep")
    tqdm_mock().side_effect = os_error

    with Spinner("Test message"):
        pass

    capture = capsys.readouterr()

    assert "Test message" in capture.out


def test_quiet_spinner(capsys):
    """
    Ensure that the ``QuietSpinner`` works by producing the expected output.
    """
    with QuietSpinner("Test message"):
        pass

    capture = capsys.readouterr()

    assert capture.out == "Test message: ...working... done\n"


def test_quiet_spinner_with_error(capsys):
    """
    Ensure that the ``QuietSpinner`` works by producing the expected output
    when an exception is encountered.
    """
    try:
        with QuietSpinner("Test message"):
            raise Exception("Test")
    except Exception as exc:
        assert str(exc) == "Test"

    capture = capsys.readouterr()

    assert capture.out == "Test message: ...working... failed\n"


def test_prompt(monkeypatch):
    """
    Ensure basic coverage of the ``prompt`` method
    """
    reporter = ConsoleReporterRenderer()

    # Test "yes" option
    monkeypatch.setattr("sys.stdin", StringIO("y\n"))
    assert reporter.prompt() == "yes"

    # Test "no" option
    monkeypatch.setattr("sys.stdin", StringIO("n\n"))
    assert reporter.prompt() == "no"


def test_prompt_bad_option(monkeypatch, capsys):
    """
    Ensure message is printed when bad option is chosen
    """
    reporter = ConsoleReporterRenderer()

    # Test "yes" option
    monkeypatch.setattr("sys.stdin", StringIO("badoption\ny\n"))

    assert reporter.prompt() == "yes"

    capture = capsys.readouterr()

    assert "Invalid choice" in capture.out


def test_prompt_error_reading_stdin(mocker):
    """
    Ensure exception is raised when OSError is encountered
    """
    reporter = ConsoleReporterRenderer()
    mock_readline = mocker.patch(
        "conda.plugins.reporter_backends.console.sys.stdin.readline"
    )
    mock_readline.side_effect = OSError("Test")

    with pytest.raises(CondaError):
        reporter.prompt()
