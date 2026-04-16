# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""YAML serialization utilities for conda."""

from __future__ import annotations

from functools import cache
from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING, overload

from ...deprecations import deprecated

if TYPE_CHECKING:
    from io import IO
    from typing import Any

    import ruamel.yaml

    from ..path import PathType


@cache
def _representer() -> type[ruamel.yaml.representer.RoundTripRepresenter]:
    import ruamel.yaml

    class CondaYAMLRepresenter(ruamel.yaml.representer.RoundTripRepresenter):
        def default(self, data: Any) -> Any:
            from enum import Enum

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
    return CondaYAMLRepresenter


@cache
def _yaml() -> ruamel.yaml.YAML:
    import ruamel.yaml

    parser = ruamel.yaml.YAML(typ="rt")
    parser.Representer = _representer()
    parser.indent(mapping=2, offset=2, sequence=4)
    parser.default_flow_style = False
    parser.sort_base_mapping_type_on_output = False
    return parser


@overload
def write(obj: Any) -> str: ...


@overload
def write(obj: Any, *, fp: IO[str]) -> None: ...


@overload
def write(obj: Any, *, path: PathType) -> None: ...


def write(
    obj: Any, *, fp: IO[str] | None = None, path: PathType | None = None
) -> None | str:
    if fp and path:
        raise ValueError("At most one of fp or path must be provided")

    if fp is not None:
        _yaml().dump(obj, fp)
        return None
    else:
        stream = StringIO()
        _yaml().dump(obj, stream=stream)
        text = stream.getvalue()
        if path is not None:
            Path(path).write_text(text)
            return None
        else:
            return text


def dump(obj: Any, fp: IO[str]) -> None:
    write(obj, fp=fp)


def dumps(obj: Any) -> str:
    return write(obj)


@overload
def read(*, text: str) -> Any: ...


@overload
def read(*, fp: IO[str]) -> Any: ...


@overload
def read(*, path: PathType) -> Any: ...


def read(
    *, text: str | None = None, fp: IO[str] | None = None, path: PathType | None = None
) -> Any:
    if (text, fp, path).count(None) != 2:
        raise ValueError("Exactly one of text, fp or path must be provided")

    if fp is not None:
        text = fp.read()
    elif path is not None:
        text = Path(path).read_text()
    return _yaml().load(text)


def load(fp: IO[str]) -> Any:
    return read(fp=fp)


def loads(s: str) -> Any:
    return read(text=s)


# ``YAMLError`` is re-exported lazily via PEP-562 so that merely importing
# this module does not pull in ``ruamel.yaml``. ``deprecated.constant``
# below installs its own module-level ``__getattr__`` and wires this one
# up as its fallback, so both names resolve correctly.
def __getattr__(name: str) -> Any:
    if name == "YAMLError":
        import ruamel.yaml

        return ruamel.yaml.YAMLError

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# ``CondaYAMLRepresenter`` used to be a module-level class. Keep it
# importable for external consumers but emit a deprecation warning on
# access. Passing ``factory=`` defers ``_representer()`` (which imports
# ``ruamel.yaml``) until the deprecated symbol is actually used.
deprecated.constant(
    "26.9",
    "27.3",
    "CondaYAMLRepresenter",
    factory=_representer,
    addendum=(
        "Use `conda.common.serialize.yaml.write`/`read` or subclass "
        "`ruamel.yaml.representer.RoundTripRepresenter` directly."
    ),
)
