# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from dataclasses import FrozenInstanceError, dataclass

import pytest

from conda.plugins.reporter_backends.events import (
    DetailViewEvent,
    EnvsListEvent,
    Event,
    FetchSectionEndEvent,
    FetchSectionStartEvent,
    FetchTaskEndEvent,
    FetchTaskProgressEvent,
    FetchTaskStartEvent,
    RenderDataEvent,
    SpinnerEndEvent,
    SpinnerStartEvent,
)
from conda.plugins.types import ReporterRendererBase


@dataclass(frozen=True)
class SampleEvent(Event):
    value: int = 0


def test_event_is_frozen():
    event = SampleEvent(value=1)
    with pytest.raises(FrozenInstanceError):
        event.value = 2  # type: ignore[misc]


EVENT_CASES = [
    (RenderDataEvent, {"data": 1}),
    (DetailViewEvent, {"data": {"a": "b"}}),
    (EnvsListEvent, {"prefixes": ("/env",)}),
    (SpinnerStartEvent, {"message": "m"}),
    (SpinnerEndEvent, {"message": "m", "success": True}),
    (FetchSectionStartEvent, {}),
    (FetchTaskStartEvent, {"task_id": 1, "name": "n", "version": "1"}),
    (FetchTaskProgressEvent, {"task_id": 1, "fraction": 0.5}),
    (FetchTaskEndEvent, {"task_id": 1, "success": True}),
    (FetchSectionEndEvent, {"success": True}),
]


@pytest.mark.parametrize("event_type,kwargs", EVENT_CASES)
def test_event_types_are_frozen_events(event_type, kwargs):
    event = event_type(**kwargs)

    assert isinstance(event, Event)
    with pytest.raises(FrozenInstanceError):
        event.new_attribute = None  # type: ignore[attr-defined]


def test_event_defaults():
    assert RenderDataEvent(data=1).style is None
    assert not EnvsListEvent(prefixes=()).show_size
    assert SpinnerStartEvent(message="m").fail_message == "failed\n"
    assert FetchTaskStartEvent(task_id=1, name="n", version="1").size is None


@pytest.mark.parametrize("event_type,kwargs", EVENT_CASES)
def test_renderer_base_handle_defaults_to_noop(event_type, kwargs):
    class Renderer(ReporterRendererBase):
        detail_view = envs_list = progress_bar = spinner = prompt = None  # type: ignore[assignment]

    assert Renderer().handle(event_type(**kwargs)) is None
