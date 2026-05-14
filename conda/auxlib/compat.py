"""Compatibility helpers for auxlib."""

import os
from collections import OrderedDict as odict  # noqa: F401
from collections.abc import Iterable
from shlex import split
from tempfile import _TemporaryFileWrapper
from typing import Any

from ..deprecations import deprecated


@deprecated("26.3", "26.9", addendum="Use `conda.common.compat.isiterable` instead.")
def isiterable(obj: Any) -> bool:
    """Return whether *obj* is iterable, excluding strings."""
    return not isinstance(obj, str) and isinstance(obj, Iterable)


# shlex.split() is a poor function to use for anything general purpose (like calling subprocess).
# It mishandles Unicode in Python 3 but all is not lost. We can escape it, then escape the escapes
# then call shlex.split() then un-escape that.
def shlex_split_unicode(to_split: str, posix: bool = True) -> list[str]:
    """Split a Unicode string with :func:`shlex.split`."""
    # shlex.split does its own un-escaping that we must counter.
    e_to_split = to_split.replace("\\", "\\\\")
    return split(e_to_split, posix=posix)


def Utf8NamedTemporaryFile(
    mode: str = "w+b",
    buffering: int = -1,
    newline: str | None = None,
    suffix: str | None = None,
    prefix: str | None = None,
    dir: str | os.PathLike[str] | None = None,
    delete: bool = True,
) -> _TemporaryFileWrapper:
    """Return a named temporary file that defaults to UTF-8 text encoding."""
    from tempfile import NamedTemporaryFile

    if "CONDA_TEST_SAVE_TEMPS" in os.environ:
        delete = False
    encoding = None
    if "b" not in mode:
        encoding = "utf-8"
    return NamedTemporaryFile(
        mode=mode,
        buffering=buffering,
        encoding=encoding,
        newline=newline,
        suffix=suffix,
        prefix=prefix,
        dir=dir,
        delete=delete,
    )
