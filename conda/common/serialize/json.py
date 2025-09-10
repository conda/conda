# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""JSON serialization utilities for conda."""

from __future__ import annotations

from contextlib import suppress
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, overload

# detect the best json library to use
from requests.compat import json

if TYPE_CHECKING:
    from io import IO
    from typing import Any

    from ..path import PathType
    from . import CacheKey


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


@overload
def write(obj: Any, *, fp: IO[str], **kwargs) -> None: ...


@overload
def write(obj: Any, *, path: PathType, **kwargs) -> None: ...


@overload
def write(obj: Any, **kwargs) -> str: ...


def write(
    obj: Any,
    *,
    fp: IO[str] | None = None,
    path: PathType | None = None,
    **kwargs,
) -> None | str:
    # validate arguments
    if sum(value is None for value in (fp, path)) < 1:
        raise ValueError("At most one of fp or path must be provided")

    # set default json.dump arguments
    kwargs.setdefault("cls", CondaJSONEncoder)
    kwargs.setdefault("indent", 2)

    # dump to file, stream, or return text
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
    return write(obj, fp=fp, **kwargs)


def dumps(obj: Any, **kwargs) -> str:
    return write(obj, **kwargs)


_JSON_CACHE: dict[CacheKey, Any] = {}


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
    try_cache: bool = False,
    **kwargs,
) -> Any:
    # generate cache key & validate arguments
    key: CacheKey = (text, fp, path)  # type: ignore[assignment]
    if sum(value is None for value in key) != 2:
        raise ValueError("Exactly one of text, fp, or path must be provided")

    # try cache if requested
    if try_cache:
        with suppress(KeyError):
            return _JSON_CACHE[key]

    # parse data from text, file, or path and cache result
    if fp is not None:
        text = fp.read()
    elif path is not None:
        text = Path(path).read_text()
    _JSON_CACHE[key] = result = json.loads(text, **kwargs)
    return result


def load(fp: IO[str], **kwargs) -> Any:
    return read(fp=fp, **kwargs)


def loads(s: str, **kwargs) -> Any:
    return read(text=s, **kwargs)


JSONDecodeError = json.JSONDecodeError
