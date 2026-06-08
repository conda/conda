# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Structured error guidance for user-facing error messages.

Plugin authors and core code can attach :class:`ErrorGuidance` to
:class:`conda.CondaError` via the ``guidance`` keyword argument so that terminal
and JSON output share the same logical cause / hint structure.

Guidance enforcement
--------------------
This module lives in ``conda._private`` to signal that its API is not yet stable.
The public re-exports in ``conda.exceptions`` are the stable surface.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ..common.io import dashlist

if TYPE_CHECKING:
    from collections.abc import Iterable
    from typing import Any, NotRequired, TypedDict

    class GuidanceHintTypedDict(TypedDict):
        text: str
        hint_code: str

    class ErrorGuidanceTypedDict(TypedDict):
        summary: NotRequired[str | None]
        cause: NotRequired[str | None]
        hints: NotRequired[Iterable[GuidanceHintTypedDict]]


@dataclass(frozen=True)
class GuidanceHint:
    """A single actionable hint with a stable machine-readable code.

    ``hint_code`` is treated as a stable API identifier — ``--json`` consumers
    can rely on it not changing between releases. Use snake_case.
    """

    text: str
    hint_code: str


@dataclass(frozen=True)
class ErrorGuidance:
    """Structured guidance for solution-oriented error messages.

    When attached to a :class:`conda.CondaError`, the display layer renders the
    cause and hints alongside the exception's ``message``.

    .. attribute:: summary
       An optional short headline that overrides the exception's ``message``
       for user-facing output. When ``None``, the exception's ``message`` is
       used as the headline.

    .. attribute:: cause
       An explanation of what went wrong, distinct from the raw error text.

    .. attribute:: hints
       An ordered list of :class:`GuidanceHint` objects with actionable next
       steps. Hints are rendered in order.
    """

    summary: str | None = None
    cause: str | None = None
    hints: tuple[GuidanceHint, ...] = ()
    hint_codes: tuple[str, ...] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "hint_codes", tuple(h.hint_code for h in self.hints))


def format_guidance(guidance: ErrorGuidance, message: str) -> str:
    """Format :class:`ErrorGuidance` for terminal output.

    ``message`` is used as the headline unless ``guidance.summary`` is set.
    """
    lines = []
    lines.append(guidance.summary.rstrip() if guidance.summary else message.rstrip())
    if guidance.cause or guidance.hints:
        lines.append("")
    if guidance.cause:
        lines.append(f"Cause: {guidance.cause.rstrip()}")
    if guidance.hints:
        hint_items = [
            f"({hint.hint_code}) {hint.text}".rstrip() for hint in guidance.hints
        ]
        lines.append(f"Next steps:{dashlist(hint_items, indent=2)}")
    return "\n".join(lines)


def _coerce_guidance(value: Any) -> ErrorGuidance | None:
    """Coerce a raw ``guidance`` value into :class:`ErrorGuidance` or ``None``.

    Accepts:
    * ``None`` → ``None``
    * ``ErrorGuidance`` → passthrough
    * ``dict`` → coerced via :func:`_guidance_from_dict`
      (empty ``dict`` → ``None``)
    """
    if value is None:
        return None
    if isinstance(value, ErrorGuidance):
        return value
    if isinstance(value, dict):
        if not value:
            return None
        return _guidance_from_dict(value)
    raise TypeError(
        f"guidance must be dict or ErrorGuidance, not {type(value).__name__}"
    )


def _guidance_from_dict(value: dict[str, Any]) -> ErrorGuidance:
    """Coerce a plain dict into an :class:`ErrorGuidance` instance."""
    return ErrorGuidance(
        summary=value.get("summary"),
        cause=value.get("cause"),
        hints=tuple(GuidanceHint(**hint) for hint in value.get("hints") or ()),
    )
