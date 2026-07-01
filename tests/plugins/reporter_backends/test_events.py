# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Tests for conda.plugins.reporter_backends.events and conda.reporters.CondaReporter."""

from __future__ import annotations

import threading
from unittest.mock import MagicMock

import pytest

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
from conda.reporters import CondaReporter, get_reporter, reset_reporter

# ---------------------------------------------------------------------------
# Event dataclass tests
# ---------------------------------------------------------------------------


def test_render_data_event_immutable():
    event = RenderDataEvent(data="hello", style=None)
    with pytest.raises((AttributeError, TypeError)):
        event.data = "changed"  # type: ignore[misc]


def test_render_data_event_defaults():
    event = RenderDataEvent(data=42)
    assert event.style is None


def test_detail_view_event():
    data = {"key": "value", "num": 1}
    event = DetailViewEvent(data=data)
    assert event.data is data


def test_envs_list_event_defaults():
    event = EnvsListEvent(prefixes=("/env1", "/env2"))
    assert not event.show_size
    assert event.prefixes == ("/env1", "/env2")


def test_spinner_start_event_defaults():
    event = SpinnerStartEvent(message="Solving...")
    assert event.fail_message == "failed\n"


def test_spinner_end_event():
    event = SpinnerEndEvent(message="Solving...", success=True)
    assert event.success


def test_fetch_section_start_event_immutable():
    event = FetchSectionStartEvent()
    assert event is not None


def test_fetch_task_start_event():
    event = FetchTaskStartEvent(task_id=1, name="numpy", version="1.26", size=5_000_000)
    assert event.task_id == 1
    assert event.size == 5_000_000


def test_fetch_task_progress_event():
    event = FetchTaskProgressEvent(task_id=1, fraction=0.5)
    assert event.fraction == 0.5


def test_fetch_task_end_event():
    event = FetchTaskEndEvent(task_id=1, success=False)
    assert not event.success


def test_fetch_section_end_event():
    event = FetchSectionEndEvent(success=True)
    assert event.success


def test_fetch_task_start_event_no_size():
    event = FetchTaskStartEvent(task_id=99, name="pkg", version="0.1", size=None)
    assert event.size is None


# ---------------------------------------------------------------------------
# CondaReporter dispatch tests
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_renderer():
    renderer = MagicMock()
    return renderer


@pytest.fixture
def reporter(mock_renderer):
    return CondaReporter(mock_renderer)


@pytest.mark.parametrize(
    "event,expected_method",
    [
        (RenderDataEvent(data="x"), "render_data"),
        (DetailViewEvent(data={"k": "v"}), "render_detail_view"),
        (EnvsListEvent(prefixes=()), "render_envs_list"),
        (SpinnerStartEvent(message="msg"), "render_spinner_start"),
        (SpinnerEndEvent(message="msg", success=True), "render_spinner_end"),
        (FetchSectionStartEvent(), "render_fetch_section_start"),
        (
            FetchTaskStartEvent(task_id=1, name="p", version="1", size=None),
            "render_fetch_task_start",
        ),
        (FetchTaskProgressEvent(task_id=1, fraction=0.5), "render_fetch_task_progress"),
        (FetchTaskEndEvent(task_id=1, success=True), "render_fetch_task_end"),
        (FetchSectionEndEvent(success=True), "render_fetch_section_end"),
    ],
)
def test_conda_reporter_dispatch(reporter, mock_renderer, event, expected_method):
    """Each event type is routed to the correct renderer method."""
    reporter.send(event)
    getattr(mock_renderer, expected_method).assert_called_once_with(event)


def test_conda_reporter_unknown_event_ignored(reporter, mock_renderer):
    """Unknown event types are silently ignored."""

    class UnknownEvent:
        pass

    reporter.send(UnknownEvent())  # type: ignore[arg-type]
    # No renderer method should have been called
    for method_name in CondaReporter._DISPATCH.values():
        getattr(mock_renderer, method_name).assert_not_called()


def test_conda_reporter_prompt_delegates(reporter, mock_renderer):
    mock_renderer.prompt.return_value = "yes"
    result = reporter.prompt("Continue?", ("yes", "no"), "yes")
    assert result == "yes"
    mock_renderer.prompt.assert_called_once_with("Continue?", ("yes", "no"), "yes")


# ---------------------------------------------------------------------------
# Thread safety tests
# ---------------------------------------------------------------------------


def test_conda_reporter_thread_safe_progress(mock_renderer):
    """FetchTaskProgressEvent dispatches are serialized across threads."""
    call_order: list[float] = []
    lock = threading.Lock()

    def recording_progress(event: FetchTaskProgressEvent):
        with lock:
            call_order.append(event.fraction)

    mock_renderer.render_fetch_task_progress.side_effect = recording_progress

    reporter = CondaReporter(mock_renderer)
    fractions = [i / 20 for i in range(20)]

    threads = [
        threading.Thread(
            target=reporter.send,
            args=(FetchTaskProgressEvent(task_id=1, fraction=f),),
        )
        for f in fractions
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(call_order) == 20, f"expected 20 calls, got {len(call_order)}"
    assert mock_renderer.render_fetch_task_progress.call_count == 20


# ---------------------------------------------------------------------------
# get_reporter / reset_reporter tests
# ---------------------------------------------------------------------------


def test_get_reporter_returns_singleton():
    reset_reporter()
    r1 = get_reporter()
    r2 = get_reporter()
    assert r1 is r2


def test_reset_reporter_clears_singleton():
    reset_reporter()
    r1 = get_reporter()
    reset_reporter()
    r2 = get_reporter()
    assert r1 is not r2
