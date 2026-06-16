# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from contextlib import nullcontext
from errno import EPIPE
from io import StringIO
from pathlib import Path
from types import SimpleNamespace

import pytest

from conda.exceptions import CondaError
from conda.plugins.reporter_backends.console import (
    ConsoleReporterRenderer,
    QuietProgressBar,
    QuietSpinner,
    Spinner,
    TQDMProgressBar,
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

    assert console_reporter_renderer.detail_view(test_data) == expected_table_str
    assert console_reporter_renderer.render(test_str) == f"{test_str}\n"

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
    spinner = renderer.spinner("test")
    assert isinstance(spinner, Spinner)


# ---------------------------------------------------------------------------
# render_* event method tests
# ---------------------------------------------------------------------------


from unittest.mock import MagicMock, patch

from conda.plugins.reporter_backends.console import (
    _QuietProgressBar,
    _TQDMProgressBar,
)
from conda.plugins.reporter_backends.events import (
    DetailViewEvent,
    FetchSectionEndEvent,
    FetchSectionStartEvent,
    FetchTaskEndEvent,
    FetchTaskProgressEvent,
    FetchTaskStartEvent,
    RenderDataEvent,
    SpinnerEndEvent,
    SpinnerStartEvent,
)


def _tty_context(monkeypatch, *, tty: bool, quiet: bool = False, dumb: bool = False):
    monkeypatch.setattr("conda.plugins.reporter_backends.console.is_tty", lambda: tty)
    monkeypatch.setattr(
        "conda.plugins.reporter_backends.console.term_dumb", lambda: dumb
    )
    monkeypatch.setattr(
        "conda.plugins.reporter_backends.console.context",
        SimpleNamespace(quiet=quiet, verbose=False, json=False, active_prefix=None),
    )


def test_render_data(capsys, monkeypatch):
    _tty_context(monkeypatch, tty=True)
    renderer = ConsoleReporterRenderer()
    renderer.render_data(RenderDataEvent(data="hello"))
    out, _ = capsys.readouterr()
    assert out == "hello\n"


def test_render_data_already_has_newline(capsys, monkeypatch):
    _tty_context(monkeypatch, tty=True)
    renderer = ConsoleReporterRenderer()
    renderer.render_data(RenderDataEvent(data="hello\n"))
    out, _ = capsys.readouterr()
    assert out == "hello\n"


def test_render_detail_view(capsys, monkeypatch):
    _tty_context(monkeypatch, tty=True)
    renderer = ConsoleReporterRenderer()
    renderer.render_detail_view(DetailViewEvent(data={"key": "val"}))
    out, _ = capsys.readouterr()
    assert "key" in out
    assert "val" in out


def test_render_spinner_start_end_quiet(capsys, monkeypatch):
    _tty_context(monkeypatch, tty=False)
    renderer = ConsoleReporterRenderer()
    renderer.render_spinner_start(SpinnerStartEvent(message="Working"))
    renderer.render_spinner_end(SpinnerEndEvent(message="Working", success=True))
    out, _ = capsys.readouterr()
    assert "Working" in out
    assert "done" in out


def test_render_spinner_end_failure_quiet(capsys, monkeypatch):
    _tty_context(monkeypatch, tty=False)
    renderer = ConsoleReporterRenderer()
    renderer.render_spinner_start(
        SpinnerStartEvent(message="Op", fail_message="oops\n")
    )
    renderer.render_spinner_end(SpinnerEndEvent(message="Op", success=False))
    out, _ = capsys.readouterr()
    assert "oops" in out


def test_render_fetch_section_start_no_tty(capsys, monkeypatch):
    _tty_context(monkeypatch, tty=False)
    renderer = ConsoleReporterRenderer()
    renderer.render_fetch_section_start(FetchSectionStartEvent())
    out, _ = capsys.readouterr()
    assert "Downloading" in out
    assert "working" in out


def test_render_fetch_section_start_tty(capsys, monkeypatch):
    _tty_context(monkeypatch, tty=True)
    renderer = ConsoleReporterRenderer()
    renderer.render_fetch_section_start(FetchSectionStartEvent())
    out, _ = capsys.readouterr()
    assert "Downloading" in out


def test_render_fetch_section_start_quiet(capsys, monkeypatch):
    _tty_context(monkeypatch, tty=True, quiet=True)
    renderer = ConsoleReporterRenderer()
    renderer.render_fetch_section_start(FetchSectionStartEvent())
    out, _ = capsys.readouterr()
    assert out == ""


def test_render_fetch_task_start_creates_bar_tty(monkeypatch):
    _tty_context(monkeypatch, tty=True)
    renderer = ConsoleReporterRenderer()
    event = FetchTaskStartEvent(task_id=1, name="numpy", version="1.26", size=None)
    with patch.object(_TQDMProgressBar, "_tqdm"):
        renderer.render_fetch_task_start(event)
    assert 1 in renderer._fetch_bars


def test_render_fetch_task_start_creates_quiet_bar_no_tty(monkeypatch):
    _tty_context(monkeypatch, tty=False)
    renderer = ConsoleReporterRenderer()
    event = FetchTaskStartEvent(task_id=2, name="scipy", version="1.0", size=100)
    renderer.render_fetch_task_start(event)
    assert isinstance(renderer._fetch_bars[2], _QuietProgressBar)


def test_render_fetch_task_progress(monkeypatch):
    _tty_context(monkeypatch, tty=False)
    renderer = ConsoleReporterRenderer()
    renderer._fetch_bars[5] = MagicMock()
    renderer.render_fetch_task_progress(FetchTaskProgressEvent(task_id=5, fraction=0.4))
    renderer._fetch_bars[5].update_to.assert_called_once_with(0.4)


def test_render_fetch_task_end(monkeypatch):
    _tty_context(monkeypatch, tty=False)
    renderer = ConsoleReporterRenderer()
    renderer._fetch_bars[3] = MagicMock()
    renderer.render_fetch_task_end(FetchTaskEndEvent(task_id=3, success=True))
    renderer._fetch_bars[3].finish.assert_called_once()
    renderer._fetch_bars[3].refresh.assert_called_once()


def test_render_fetch_section_end_closes_bars(monkeypatch, capsys):
    _tty_context(monkeypatch, tty=False)
    renderer = ConsoleReporterRenderer()
    bar1 = MagicMock()
    bar2 = MagicMock()
    renderer._fetch_bars = {1: bar1, 2: bar2}
    renderer.render_fetch_section_end(FetchSectionEndEvent(success=True))
    bar1.close.assert_called_once()
    bar2.close.assert_called_once()
    assert renderer._fetch_bars == {}


def test_render_fetch_task_progress_unknown_task_noop(monkeypatch):
    _tty_context(monkeypatch, tty=False)
    renderer = ConsoleReporterRenderer()
    # Should not raise when task_id is not registered
    renderer.render_fetch_task_progress(
        FetchTaskProgressEvent(task_id=999, fraction=0.5)
    )
