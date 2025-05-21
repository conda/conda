# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""JSON serialization utilities for conda."""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

# detect the best json library to use
from requests.compat import json

if TYPE_CHECKING:
    from typing import Any


class CondaJSONEncoder(json.JSONEncoder):
    def default(self, obj: Any) -> Any:
        # Python types
        if isinstance(obj, Enum):
            return obj.value
        elif isinstance(obj, Path):
            return str(obj)

        # auxlib entity types
        if hasattr(obj, "dump"):
            return obj.dump()
        elif hasattr(obj, "__json__"):
            return obj.__json__()
        elif hasattr(obj, "to_json"):
            return obj.to_json()
        elif hasattr(obj, "as_json"):
            return obj.as_json()

        # default
        return super().default(obj)


def dump(*args, **kwargs):
    if kwargs.get("cls") is None:
        kwargs["cls"] = CondaJSONEncoder
    if kwargs.get("indent") is None:
        kwargs["indent"] = 2
    return json.dump(*args, **kwargs)


def dumps(*args, **kwargs):
    if kwargs.get("cls") is None:
        kwargs["cls"] = CondaJSONEncoder
    if kwargs.get("indent") is None:
        kwargs["indent"] = 2
    return json.dumps(*args, **kwargs)


load = json.load
loads = json.loads
JSONDecodeError = json.JSONDecodeError
