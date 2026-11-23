# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from contextlib import nullcontext
from io import StringIO
from typing import TYPE_CHECKING

import pytest

from conda.base.context import context, reset_context
from conda.exceptions import CondaSystemExit, DryRunExit
from conda.plugins.reporter_backends.console import (
    ConsoleReporterRenderer,
    TQDMProgressBar,
)
from conda.plugins.reporter_backends.events import (
    DetailViewEvent,
    Event,
    RenderDataEvent,
)
from conda.plugins.reporter_backends.json import JSONReporterRenderer
from conda.plugins.types import ReporterRendererBase
from conda.reporters import (
    CondaReporter,
    confirm_yn,
    get_progress_bar,
    get_progress_bar_context_manager,
    get_reporter,
    render,
    reset_reporter,
)

if TYPE_CHECKING:
    from pytest import CaptureFixture, MonkeyPatch


def test_render(capsys: CaptureFixture):
    """
    Ensure basic coverage of the :func:`~conda.reporters.render` function.
    """
    # Test simple rendering of object
    render("test-string")

    stdout, stderr = capsys.readouterr()
    assert stdout == "test-string\n"
    assert not stderr

    # Test rendering of object with a style
    render(["test-string"], style="envs_list")

    stdout, stderr = capsys.readouterr()
    assert "conda environments" in stdout
    assert "test-string" in stdout
    assert not stderr

    # Test error when style cannot be found
    with pytest.raises(
        AttributeError,
        match="'non_existent_view' is not a valid reporter backend style",
    ):
        render({"test": "data"}, style="non_existent_view")


def test_get_progress_bar(monkeypatch):
    """
    Ensure basic coverage of the :func:`~conda.reporters.get_progress_bar~` function
    """
    monkeypatch.setattr("conda.plugins.reporter_backends.console.is_tty", lambda: True)
    monkeypatch.setattr(
        "conda.plugins.reporter_backends.console.term_dumb", lambda: False
    )
    progress_bar_manager = get_progress_bar("test")

    assert isinstance(progress_bar_manager, TQDMProgressBar)


def test_get_progress_bar_context_managers():
    """
    Ensure basic coverage of the
    :func:`~conda.reporters.get_progress_bar_context_manager~` function
    """
    progress_bar_context_manager = get_progress_bar_context_manager()

    assert isinstance(progress_bar_context_manager, nullcontext)


def test_confirm_yn_dry_run_exit(monkeypatch: MonkeyPatch):
    with pytest.raises(DryRunExit):
        monkeypatch.setenv("CONDA_DRY_RUN", "true")
        reset_context()

        confirm_yn()


def test_confirm_yn_always_yes(monkeypatch: MonkeyPatch):
    monkeypatch.setenv("CONDA_ALWAYS_YES", "true")
    monkeypatch.setenv("CONDA_DRY_RUN", "false")
    reset_context()
    assert context.always_yes
    assert not context.dry_run

    confirm_yn()


def test_confirm_yn_yes(monkeypatch: MonkeyPatch, capsys: CaptureFixture):
    monkeypatch.setattr("sys.stdin", StringIO("blah\ny\n"))

    monkeypatch.setenv("CONDA_ALWAYS_YES", "false")
    monkeypatch.setenv("CONDA_DRY_RUN", "false")
    reset_context()
    assert not context.always_yes
    assert not context.dry_run

    assert confirm_yn()

    stdout, stderr = capsys.readouterr()
    assert "Invalid choice" in stdout


def test_confirm_yn_no(monkeypatch: MonkeyPatch):
    monkeypatch.setattr("sys.stdin", StringIO("n\n"))

    with pytest.raises(CondaSystemExit):
        monkeypatch.setenv("CONDA_ALWAYS_YES", "false")
        monkeypatch.setenv("CONDA_DRY_RUN", "false")
        reset_context()

        assert not context.always_yes
        assert not context.dry_run

        confirm_yn()


class _LogFileRenderer(ReporterRendererBase):
    """Stand-in renderer that writes every event to a log file."""

    detail_view = envs_list = progress_bar = spinner = prompt = None  # type: ignore[assignment]

    def __init__(self, path):
        self.path = path

    def handle(self, event: Event) -> None:
        with self.path.open("a") as fh:
            fh.write(f"{type(event).__name__}\n")


class _TelemetryRenderer(ReporterRendererBase):
    """Stand-in renderer that records events for a telemetry backend."""

    detail_view = envs_list = progress_bar = spinner = prompt = None  # type: ignore[assignment]

    def __init__(self):
        self.events: list[Event] = []

    def handle(self, event: Event) -> None:
        self.events.append(event)


class _BrokenRenderer(ReporterRendererBase):
    detail_view = envs_list = progress_bar = spinner = prompt = None  # type: ignore[assignment]

    def handle(self, event: Event) -> None:
        raise RuntimeError("boom")


def test_reporter_send_calls_renderer_handle(mocker):
    renderer = mocker.MagicMock()
    event = Event()

    CondaReporter(renderer).send(event)

    renderer.handle.assert_called_once_with(event)


def test_reporter_without_renderers_ignores_events():
    CondaReporter().send(Event())


def test_reporter_accepts_multiple_renderers_in_order(mocker):
    calls = mocker.MagicMock()
    first, second = calls.first, calls.second
    event = Event()

    reporter = CondaReporter(first, second)
    reporter.send(event)

    assert reporter.renderers == (first, second)
    assert calls.mock_calls == [
        mocker.call.first.handle(event),
        mocker.call.second.handle(event),
    ]


def test_reporter_add_renderer_receives_only_later_events(mocker):
    first, late = mocker.MagicMock(), mocker.MagicMock()
    reporter = CondaReporter(first)
    before, after = Event(), Event()

    reporter.send(before)
    reporter.add_renderer(late)
    reporter.send(after)

    assert reporter.renderers == (first, late)
    assert [c.args[0] for c in first.handle.call_args_list] == [before, after]
    late.handle.assert_called_once_with(after)


def test_reporter_renders_to_stdout_log_file_and_telemetry_at_once(capsys, tmp_path):
    log_file = tmp_path / "conda.log"
    telemetry = _TelemetryRenderer()
    reporter = CondaReporter(
        ConsoleReporterRenderer(), _LogFileRenderer(log_file), telemetry
    )
    event = RenderDataEvent(data="hello")

    reporter.send(event)

    assert capsys.readouterr().out == "hello\n"
    assert log_file.read_text() == "RenderDataEvent\n"
    assert telemetry.events == [event]


def test_reporter_failing_renderer_does_not_block_others(capsys, caplog):
    telemetry = _TelemetryRenderer()
    reporter = CondaReporter(_BrokenRenderer(), ConsoleReporterRenderer(), telemetry)
    event = RenderDataEvent(data="hello")

    reporter.send(event)

    assert capsys.readouterr().out == "hello\n"
    assert telemetry.events == [event]
    assert "_BrokenRenderer failed to handle RenderDataEvent" in caplog.text


@pytest.mark.parametrize(
    "renderer_type", [ConsoleReporterRenderer, JSONReporterRenderer]
)
def test_renderer_handle_ignores_unhandled_event(capsys, renderer_type):
    CondaReporter(renderer_type()).send(Event())

    assert not capsys.readouterr().out


def test_get_reporter_is_singleton():
    reset_reporter()
    reporter = get_reporter()

    assert isinstance(reporter, CondaReporter)
    assert get_reporter() is reporter

    reset_reporter()
    assert get_reporter() is not reporter


def test_reset_context_resets_reporter():
    reporter = get_reporter()
    reset_context()

    assert get_reporter() is not reporter


@pytest.mark.parametrize(
    "console,renderer_type",
    [("classic", ConsoleReporterRenderer), ("json", JSONReporterRenderer)],
)
def test_get_reporter_uses_configured_backend(
    monkeypatch: MonkeyPatch, console, renderer_type
):
    monkeypatch.setenv("CONDA_CONSOLE", console)
    reset_context()

    assert isinstance(get_reporter().renderers[0], renderer_type)


@pytest.mark.parametrize(
    "event,expected",
    [
        (RenderDataEvent(data="text"), "text\n"),
        (DetailViewEvent(data={"a": "b"}), "\n a : b\n\n"),
    ],
)
def test_reporter_send_renders_event_with_console_renderer(capsys, event, expected):
    CondaReporter(ConsoleReporterRenderer()).send(event)

    assert capsys.readouterr().out == expected
