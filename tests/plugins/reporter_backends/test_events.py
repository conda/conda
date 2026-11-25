# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from dataclasses import FrozenInstanceError, dataclass

import pytest

from conda.plugins.reporter_backends.events import Event


@dataclass(frozen=True)
class SampleEvent(Event):
    value: int = 0


def test_event_is_frozen():
    event = SampleEvent(value=1)
    with pytest.raises(FrozenInstanceError):
        event.value = 2  # type: ignore[misc]
