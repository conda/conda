# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""JSON serialization utilities for conda."""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

# We must import frozendict before importing json to enable its monkeypatch over
# json.JSONEncoder. This makes sure that our CondaJSONEncoder inherits from
# frozendict's patched JSONEncoder, which natively supports serialising frozendicts.
# See https://github.com/Marco-Sulla/python-frozendict/blob/a9744d61f42e86fc10c9c3668425abc4d485a9ec/src/frozendict/monkeypatch.py
# and https://github.com/Marco-Sulla/python-frozendict/releases/tag/v2.3.6 for more.
from frozendict import frozendict  # noqa: F401

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
        for attr in ("dump", "__json__", "to_json", "as_json"):
            if method := getattr(obj, attr, None):
                return method()

        # default
        return super().default(obj)


def dump(*args, **kwargs):
    kwargs.setdefault("cls", CondaJSONEncoder)
    kwargs.setdefault("indent", 2)
    return json.dump(*args, **kwargs)


def dumps(*args, **kwargs):
    kwargs.setdefault("cls", CondaJSONEncoder)
    kwargs.setdefault("indent", 2)
    return json.dumps(*args, **kwargs)


load = json.load
loads = json.loads
JSONDecodeError = json.JSONDecodeError
