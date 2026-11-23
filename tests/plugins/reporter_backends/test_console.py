# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from contextlib import nullcontext
from errno import EPIPE
from io import StringIO
from pathlib import Path
from types import SimpleNamespace

import pytest

from conda.base.context import reset_context
from conda.exceptions import CondaError
from conda.plugins.reporter_backends.console import (
    ConsoleReporterRenderer,
    QuietProgressBar,
    QuietSpinner,
    Spinner,
    TQDMProgressBar,
)
from conda.plugins.reporter_backends.events import (
    DetailViewEvent,
    EnvsListEvent,
    FetchSectionEndEvent,
    FetchSectionStartEvent,
    FetchTaskEndEvent,
    FetchTaskProgressEvent,
    FetchTaskStartEvent,
    RenderDataEvent,
    SpinnerEndEvent,
    SpinnerStartEvent,
)


def test_console_reporter_renderer(monkeypatch):
    """
    Tests the ``ConsoleReporterRenderer`` class
    """
    # Pretend we are in a TTY so that progress_bar returns TQDMProgressBar
    monkeypatch.setattr("conda.plugins.reporter_backends.console.is_tty", lambda: True)
    monkeypatch.setattr(
        "conda.plugins.reporter_backends.console.term_dumb", lambda: False
    )

    test_data = {"one": "value_one", "two": "value_two", "three": "value_three"}
    test_str = "a string value"
    expected_table_str = (
        "\n   one : value_one\n   two : value_two\n three : value_three\n\n"
    )
    console_reporter_renderer = ConsoleReporterRenderer()

    with pytest.deprecated_call():
        assert console_reporter_renderer.detail_view(test_data) == expected_table_str
    with pytest.deprecated_call():
        assert console_reporter_renderer.render(test_str) == f"{test_str}\n"

    with pytest.deprecated_call():
        progress_bar = console_reporter_renderer.progress_bar(
            description="Test progress bar description",
            io_context_manager=nullcontext(),
        )

    assert isinstance(progress_bar, TQDMProgressBar)

    with pytest.deprecated_call():
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

    with pytest.deprecated_call():
        output = console_reporter_renderer.envs_list(["/tmp/envs"])

    assert f"envs                     {Path('/tmp/envs')}" in output


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


def test_progress_bar_quiet_context_returns_quiet_bar(monkeypatch):
    """Verify progress_bar() returns QuietProgressBar when context.quiet is True."""
    monkeypatch.setattr("conda.plugins.reporter_backends.console.is_tty", lambda: True)
    monkeypatch.setattr(
        "conda.plugins.reporter_backends.console.term_dumb", lambda: False
    )
    monkeypatch.setattr(
        "conda.plugins.reporter_backends.console.context", SimpleNamespace(quiet=True)
    )
    renderer = ConsoleReporterRenderer()
    with pytest.deprecated_call():
        bar = renderer.progress_bar("test")
    assert isinstance(bar, QuietProgressBar)


def test_progress_bar_non_tty_returns_quiet_bar(monkeypatch):
    """Verify progress_bar() returns QuietProgressBar when not in a TTY."""
    monkeypatch.setattr("conda.plugins.reporter_backends.console.is_tty", lambda: False)
    monkeypatch.setattr(
        "conda.plugins.reporter_backends.console.term_dumb", lambda: False
    )
    monkeypatch.setattr(
        "conda.plugins.reporter_backends.console.context", SimpleNamespace(quiet=False)
    )
    renderer = ConsoleReporterRenderer()
    with pytest.deprecated_call():
        bar = renderer.progress_bar("test")
    assert isinstance(bar, QuietProgressBar)


def test_progress_bar_term_dumb_returns_quiet_bar(monkeypatch):
    """Verify progress_bar() returns QuietProgressBar when terminal is dumb."""
    monkeypatch.setattr("conda.plugins.reporter_backends.console.is_tty", lambda: True)
    monkeypatch.setattr(
        "conda.plugins.reporter_backends.console.term_dumb", lambda: True
    )
    monkeypatch.setattr(
        "conda.plugins.reporter_backends.console.context", SimpleNamespace(quiet=False)
    )
    renderer = ConsoleReporterRenderer()
    with pytest.deprecated_call():
        bar = renderer.progress_bar("test")
    assert isinstance(bar, QuietProgressBar)


def test_progress_bar_tty_returns_tqdm_bar(monkeypatch):
    """Verify progress_bar() returns TQDMProgressBar in a normal TTY."""
    monkeypatch.setattr("conda.plugins.reporter_backends.console.is_tty", lambda: True)
    monkeypatch.setattr(
        "conda.plugins.reporter_backends.console.term_dumb", lambda: False
    )
    monkeypatch.setattr(
        "conda.plugins.reporter_backends.console.context", SimpleNamespace(quiet=False)
    )
    renderer = ConsoleReporterRenderer()
    with pytest.deprecated_call():
        bar = renderer.progress_bar("test")
    assert isinstance(bar, TQDMProgressBar)


def test_spinner_quiet_context_returns_quiet_spinner(monkeypatch):
    """Verify spinner() returns QuietSpinner when context.quiet is True."""
    monkeypatch.setattr("conda.plugins.reporter_backends.console.is_tty", lambda: True)
    monkeypatch.setattr(
        "conda.plugins.reporter_backends.console.term_dumb", lambda: False
    )
    monkeypatch.setattr(
        "conda.plugins.reporter_backends.console.context", SimpleNamespace(quiet=True)
    )
    renderer = ConsoleReporterRenderer()
    with pytest.deprecated_call():
        spinner = renderer.spinner("test")
    assert isinstance(spinner, QuietSpinner)


def test_spinner_non_tty_returns_quiet_spinner(monkeypatch):
    """Verify spinner() returns QuietSpinner when not in a TTY."""
    monkeypatch.setattr("conda.plugins.reporter_backends.console.is_tty", lambda: False)
    monkeypatch.setattr(
        "conda.plugins.reporter_backends.console.term_dumb", lambda: False
    )
    monkeypatch.setattr(
        "conda.plugins.reporter_backends.console.context", SimpleNamespace(quiet=False)
    )
    renderer = ConsoleReporterRenderer()
    with pytest.deprecated_call():
        spinner = renderer.spinner("test")
    assert isinstance(spinner, QuietSpinner)


def test_spinner_term_dumb_returns_quiet_spinner(monkeypatch):
    """Verify spinner() returns QuietSpinner when terminal is dumb."""
    monkeypatch.setattr("conda.plugins.reporter_backends.console.is_tty", lambda: True)
    monkeypatch.setattr(
        "conda.plugins.reporter_backends.console.term_dumb", lambda: True
    )
    monkeypatch.setattr(
        "conda.plugins.reporter_backends.console.context", SimpleNamespace(quiet=False)
    )
    renderer = ConsoleReporterRenderer()
    with pytest.deprecated_call():
        spinner = renderer.spinner("test")
    assert isinstance(spinner, QuietSpinner)


def test_spinner_tty_returns_animated_spinner(monkeypatch):
    """Verify spinner() returns Spinner in a normal TTY."""
    monkeypatch.setattr("conda.plugins.reporter_backends.console.is_tty", lambda: True)
    monkeypatch.setattr(
        "conda.plugins.reporter_backends.console.term_dumb", lambda: False
    )
    monkeypatch.setattr(
        "conda.plugins.reporter_backends.console.context", SimpleNamespace(quiet=False)
    )
    renderer = ConsoleReporterRenderer()
    with pytest.deprecated_call():
        spinner = renderer.spinner("test")
    assert isinstance(spinner, Spinner)


@pytest.mark.parametrize(
    "text,expected", [("hello", "hello\n"), ("hello\n", "hello\n")]
)
def test_handle_render_data_event(capsys, text, expected):
    ConsoleReporterRenderer().handle(RenderDataEvent(data=text))

    assert capsys.readouterr().out == expected


def test_handle_detail_view_event_matches_legacy(capsys):
    data = {"one": "value_one", "three": "value_three"}
    renderer = ConsoleReporterRenderer()

    renderer.handle(DetailViewEvent(data=data))

    with pytest.deprecated_call():
        assert capsys.readouterr().out == renderer.detail_view(data)


@pytest.mark.parametrize("show_size", [False, True])
def test_handle_envs_list_event_matches_legacy(mocker, capsys, show_size):
    mock_context = mocker.patch("conda.core.prefix_data.context")
    mock_context.envs_dirs = ["/tmp"]
    mocker.patch("conda.core.prefix_data.PrefixData.size", return_value=1024)
    renderer = ConsoleReporterRenderer()

    renderer.handle(EnvsListEvent(prefixes=("/tmp/envs",), show_size=show_size))

    with pytest.deprecated_call():
        expected = renderer.envs_list(["/tmp/envs"], show_size=show_size)
    assert capsys.readouterr().out == expected


@pytest.mark.parametrize(
    "tty,expected_cls",
    [(True, Spinner), (False, QuietSpinner)],
)
def test_handle_spinner_events(monkeypatch, mocker, tty, expected_cls):
    monkeypatch.setattr("conda.plugins.reporter_backends.console.is_tty", lambda: tty)
    monkeypatch.setattr(
        "conda.plugins.reporter_backends.console.term_dumb", lambda: False
    )
    enter = mocker.patch.object(expected_cls, "__enter__")
    exit_ = mocker.patch.object(expected_cls, "__exit__")
    renderer = ConsoleReporterRenderer()

    renderer.handle(SpinnerStartEvent(message="msg"))
    assert isinstance(renderer._spinners["msg"], expected_cls)
    enter.assert_called_once()

    renderer.handle(SpinnerEndEvent(message="msg", success=False))
    exit_.assert_called_once_with(Exception, None, None)
    assert not renderer._spinners


def test_handle_spinner_end_without_start_is_ignored():
    ConsoleReporterRenderer().handle(
        SpinnerEndEvent(message="never-started", success=True)
    )


def test_handle_spinner_success_exits_cleanly(monkeypatch, capsys):
    monkeypatch.setattr("conda.plugins.reporter_backends.console.is_tty", lambda: False)
    renderer = ConsoleReporterRenderer()

    renderer.handle(SpinnerStartEvent(message="Solving"))
    renderer.handle(SpinnerEndEvent(message="Solving", success=True))

    assert capsys.readouterr().out == "Solving: ...working... done\n"


@pytest.mark.parametrize(
    "tty,expected_cls",
    [(True, TQDMProgressBar), (False, QuietProgressBar)],
)
def test_handle_fetch_events(monkeypatch, mocker, tty, expected_cls):
    monkeypatch.setattr("conda.plugins.reporter_backends.console.is_tty", lambda: tty)
    monkeypatch.setattr(
        "conda.plugins.reporter_backends.console.term_dumb", lambda: False
    )
    mocker.patch.object(TQDMProgressBar, "_tqdm")
    renderer = ConsoleReporterRenderer()

    renderer.handle(FetchSectionStartEvent())
    renderer.handle(
        FetchTaskStartEvent(task_id=1, name="numpy", version="1.0", size=2048)
    )
    bar = renderer._fetch_bars[1]
    assert isinstance(bar, expected_cls)
    assert "numpy-1.0" in bar.description
    assert "2 KB" in bar.description

    update_to = mocker.spy(bar, "update_to")
    renderer.handle(FetchTaskProgressEvent(task_id=1, fraction=0.5))
    update_to.assert_called_once_with(0.5)

    renderer.handle(FetchTaskEndEvent(task_id=1, success=True))
    assert update_to.call_args.args == (1,)

    renderer.handle(FetchSectionEndEvent(success=True))
    assert not renderer._fetch_bars


def test_handle_fetch_task_end_failure_does_not_finish_bar(mocker):
    renderer = ConsoleReporterRenderer()
    renderer.handle(FetchTaskStartEvent(task_id=1, name="n", version="1"))
    update_to = mocker.spy(renderer._fetch_bars[1], "update_to")

    renderer.handle(FetchTaskEndEvent(task_id=1, success=False))

    update_to.assert_not_called()


def test_handle_fetch_events_for_unknown_task_are_ignored():
    renderer = ConsoleReporterRenderer()

    renderer.handle(FetchTaskProgressEvent(task_id=9, fraction=1))
    renderer.handle(FetchTaskEndEvent(task_id=9, success=True))


@pytest.mark.parametrize(
    "tty,expected_start,expected_end",
    [
        (True, "\nDownloading and Extracting Packages:\n", "\r\n"),
        (False, "\nDownloading and Extracting Packages: ...working...", " done\n"),
    ],
)
def test_handle_fetch_section_messages(
    monkeypatch, capsys, tty, expected_start, expected_end
):
    monkeypatch.setattr("conda.plugins.reporter_backends.console.is_tty", lambda: tty)
    monkeypatch.setattr(
        "conda.plugins.reporter_backends.console.term_dumb", lambda: False
    )
    renderer = ConsoleReporterRenderer()

    renderer.handle(FetchSectionStartEvent())
    start = capsys.readouterr().out
    renderer.handle(FetchSectionEndEvent(success=True))
    end = capsys.readouterr().out

    assert start == expected_start
    assert end == expected_end


def test_handle_fetch_section_is_silent_when_quiet(monkeypatch, capsys):
    monkeypatch.setenv("CONDA_QUIET", "true")
    reset_context()
    renderer = ConsoleReporterRenderer()

    renderer.handle(FetchSectionStartEvent())
    renderer.handle(FetchSectionEndEvent(success=True))

    assert capsys.readouterr().out == ""
