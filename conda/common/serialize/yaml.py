# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""YAML serialization utilities for conda."""

from __future__ import annotations

from contextlib import suppress
from enum import Enum
from functools import cache
from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING, overload

import ruamel.yaml

if TYPE_CHECKING:
    from io import IO
    from typing import Any

    from ..path import PathType
    from . import CacheKey


class CondaYAMLRepresenter(ruamel.yaml.representer.RoundTripRepresenter):
    def default(self, data: Any) -> Any:
        # Python types
        if isinstance(data, Enum):
            return self.represent_str(data.value)
        elif isinstance(data, Path):
            return self.represent_str(str(data))

        # auxlib entity types
        for attr in ("dump", "__json__", "to_json", "as_json"):
            if method := getattr(data, attr, None):
                return self.represent_data(method())

        # mirror JSON behavior
        raise TypeError(
            f"Object of type {data.__class__.__name__} is not YAML serializable"
        )


CondaYAMLRepresenter.add_representer(None, CondaYAMLRepresenter.default)


@cache
def _yaml() -> ruamel.yaml.YAML:
    parser = ruamel.yaml.YAML(typ="rt")
    parser.Representer = CondaYAMLRepresenter
    parser.indent(mapping=2, offset=2, sequence=4)
    parser.default_flow_style = False
    parser.sort_base_mapping_type_on_output = False
    return parser


@overload
def write(obj: Any, *, fp: IO[str]) -> None: ...


@overload
def write(obj: Any, *, path: PathType) -> None: ...


@overload
def write(obj: Any) -> str: ...


def write(
    obj: Any,
    *,
    fp: IO[str] | None = None,
    path: PathType | None = None,
) -> None | str:
    # validate arguments
    if sum(value is None for value in (fp, path)) < 1:
        raise ValueError("At most one of fp or path must be provided")

    # dump to file, stream, or return text
    if fp is not None:
        _yaml().dump(obj, fp)
        return None
    else:
        stream = StringIO()
        _yaml().dump(obj, stream)
        text = stream.getvalue()
        if path is not None:
            Path(path).write_text(text)
            return None
        else:
            return text


def dump(obj: Any, fp: IO[str]) -> None:
    return write(obj, fp=fp)


def dumps(obj: Any) -> str:
    return write(obj)


_YAML_CACHE: dict[CacheKey, Any] = {}


@overload
def read(*, text: str) -> Any: ...


@overload
def read(*, fp: IO[str]) -> Any: ...


@overload
def read(*, path: PathType) -> Any: ...


def read(
    *,
    text: str | None = None,
    fp: IO[str] | None = None,
    path: PathType | None = None,
    try_cache: bool = False,
) -> Any:
    # generate cache key & validate arguments
    key: CacheKey = (text, fp, path)  # type: ignore[assignment]
    if sum(value is None for value in key) != 2:
        raise ValueError("Exactly one of text, fp, or path must be provided")

    # try cache if requested
    if try_cache:
        with suppress(KeyError):
            return _YAML_CACHE[key]

    # parse data from text, file, or path and cache result
    if fp is not None:
        text = fp.read()
    elif path is not None:
        text = Path(path).read_text()
    _YAML_CACHE[key] = result = _yaml().load(text)
    return result


def load(fp: IO[str]) -> Any:
    return read(fp=fp)


def loads(s: str) -> Any:
    return read(text=s)


YAMLError = ruamel.yaml.YAMLError
