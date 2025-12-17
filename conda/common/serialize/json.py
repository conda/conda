# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""JSON serialization utilities for conda."""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, overload

from frozendict import frozendict

# detect the best json library to use
from requests.compat import json

if TYPE_CHECKING:
    from io import IO
    from typing import Any

    from ..path import PathType


class CondaJSONEncoder(json.JSONEncoder):
    def default(self, obj: Any) -> Any:
        # immutable types

        if isinstance(obj, frozendict):
            return dict(obj)

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


@overload
def write(obj: Any, *, fp: IO[str], **kwargs) -> None: ...


@overload
def write(obj: Any, *, path: PathType, **kwargs) -> None: ...


@overload
def write(obj: Any, **kwargs) -> str: ...


def write(
    obj: Any, *, fp: IO[str] | None = None, path: PathType | None = None, **kwargs
) -> None | str:
    if fp and path:
        raise ValueError("At most one of fp or path must be provided")

    kwargs.setdefault("cls", CondaJSONEncoder)
    kwargs.setdefault("indent", 2)

    if fp is not None:
        json.dump(obj, fp, **kwargs)
        return None
    else:
        text = json.dumps(obj, **kwargs)
        if path is not None:
            Path(path).write_text(text)
            return None
        else:
            return text


def dump(obj: Any, fp: IO[str], **kwargs) -> None:
    write(obj, fp=fp, **kwargs)


def dumps(obj: Any, **kwargs) -> str:
    return write(obj, **kwargs)


@overload
def read(*, text: str, **kwargs) -> Any: ...


@overload
def read(*, fp: IO[str], **kwargs) -> Any: ...


@overload
def read(*, path: PathType, **kwargs) -> Any: ...


def read(
    *,
    text: str | None = None,
    fp: IO[str] | None = None,
    path: PathType | None = None,
    **kwargs,
) -> Any:
    if (text, fp, path).count(None) != 2:
        raise ValueError("Exactly one of text, fp or path must be provided")

    if fp is not None:
        return json.load(fp, **kwargs)
    elif path is not None:
        return json.loads(Path(path).read_text(), **kwargs)
    else:
        return json.loads(text, **kwargs)


def load(fp: IO[str], **kwargs) -> Any:
    return read(fp=fp, **kwargs)


def loads(s: str, **kwargs) -> Any:
    return read(text=s, **kwargs)


JSONDecodeError = json.JSONDecodeError
