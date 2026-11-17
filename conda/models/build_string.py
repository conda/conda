# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Sortable conda build string data model.

Derived from reference implementation provided by Travis Hathaway in conda/conda#16849.
Analyzes conda build strings to support ordering by build number, variant suffix,
and string tie-breaker, adhering to CEP 26 conventions.
"""

from __future__ import annotations

import re
from functools import lru_cache
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any

# CEP 26: build strings MUST match this and MUST NOT exceed 64 characters.
_CEP26_RE = re.compile(r"^[a-zA-Z0-9_.+]+$")
_CEP26_MAX_LEN = 64

# A token counts as a build number only if it is wholly ASCII digits.
_NUMBER_RE = re.compile(r"^[0-9]+$")


@lru_cache(maxsize=4096)
def _split(value: str) -> tuple[int | None, str]:
    """Return ``(build_number, tail)`` for ``value``.

    ``build_number`` is the last all-digit ``_`` token, or ``None``.
    ``tail`` is everything after that token (the variant suffix such as
    ``cuda`` or ``openblas``), or ``""``.

    One special case: ``python`` / ``cross-python_*`` PyPy builds are
    ``<build_number>_<pypy_abi>_pypy`` (``14_73_pypy``). The trailing ``73``
    is the PyPy ABI version, constant across builds, so the number is the
    token *before* it.

    Bounded cache: caches up to 4096 distinct build strings to accelerate
    sorting while preventing unbounded memory growth.

    Args:
        value: The build string to parse.

    Returns:
        A tuple of ``(build_number, tail)``.
    """
    tokens = value.split("_")
    if (
        len(tokens) >= 3
        and tokens[-1] == "pypy"
        and _NUMBER_RE.fullmatch(tokens[-2])
        and _NUMBER_RE.fullmatch(tokens[-3])
    ):
        return int(tokens[-3]), "_".join(tokens[-2:])
    for i in range(len(tokens) - 1, -1, -1):
        if _NUMBER_RE.fullmatch(tokens[i]):
            return int(tokens[i]), "_".join(tokens[i + 1 :])
    return None, ""


class BuildString(str):
    """A ``str`` that sorts conda build strings by build number.

    It is a ``str``: hashing, ``==`` against plain strings, slicing,
    formatting, and JSON serialization are unchanged. Ordering
    (``<``, ``<=``, ``>``, ``>=``) is overridden so ``sorted()``,
    ``max()``, and ``min()`` order by parsed build number, variant suffix,
    and raw string tie-breaker.

    Ordering key, most significant first:
    1. Strings without any numeric token sort before all numbered ones.
    2. The build number, compared as an ``int``.
    3. The variant suffix after the number (e.g. ``""`` < ``"cpu"`` < ``"cuda"``).
    4. The raw string, ensuring deterministic total ordering when builds tie.
    """

    __slots__ = ()

    @property
    def build_number(self) -> int | None:
        """The build number parsed from the string, or ``None``."""
        return _split(self)[0]

    @property
    def suffix(self) -> str:
        """Variant text following the build number (e.g. ``cuda``, ``openblas``)."""
        return _split(self)[1]

    @property
    def is_cep26_valid(self) -> bool:
        """Whether the string satisfies CEP 26 (charset and <= 64 chars)."""
        return len(self) <= _CEP26_MAX_LEN and _CEP26_RE.fullmatch(self) is not None

    @property
    def sort_key(self) -> tuple[int, int, str, str]:
        """Total-order key; usable as ``key=`` for plain strings too."""
        number, tail = _split(self)
        if number is None:
            return (0, 0, "", str(self))
        return (1, number, tail, str(self))

    @classmethod
    def key(cls, value: str) -> tuple[int, int, str, str]:
        """Convenience function for ``sorted(strings, key=BuildString.key)``."""
        return cls(value).sort_key

    def _other_key(self, other: Any) -> tuple[int, int, str, str] | None:
        if isinstance(other, BuildString):
            return other.sort_key
        if isinstance(other, str):
            return BuildString(other).sort_key
        return None

    def __lt__(self, other: Any) -> bool:
        okey = self._other_key(other)
        if okey is None:
            return NotImplemented
        return self.sort_key < okey

    def __le__(self, other: Any) -> bool:
        okey = self._other_key(other)
        if okey is None:
            return NotImplemented
        return self.sort_key <= okey

    def __gt__(self, other: Any) -> bool:
        okey = self._other_key(other)
        if okey is None:
            return NotImplemented
        return self.sort_key > okey

    def __ge__(self, other: Any) -> bool:
        okey = self._other_key(other)
        if okey is None:
            return NotImplemented
        return self.sort_key >= okey

    __hash__ = str.__hash__
