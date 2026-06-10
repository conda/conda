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

from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING

from ..common.io import dashlist

if TYPE_CHECKING:
    from collections.abc import Iterable
    from typing import Any, NotRequired, TypedDict

    from .. import CondaError

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

    def __post_init__(self) -> None:
        if not self.summary and not self.cause and not self.hints:
            raise ValueError(
                "at least one of summary, cause, or hints must be provided"
            )

    @property
    def hint_codes(self) -> tuple[str, ...]:
        """Hint codes extracted from :attr:`hints` for JSON serialization."""
        return tuple(hint.hint_code for hint in self.hints)

    def __json__(self) -> dict[str, object]:
        """Serialize for :meth:`conda.CondaError.dump_map`."""
        result = asdict(self)
        result["hint_codes"] = self.hint_codes
        return {k: v for k, v in result.items() if v}

    @classmethod
    def coerce(cls, value: Any) -> ErrorGuidance | None:
        """Coerce a raw ``guidance`` value into :class:`ErrorGuidance` or ``None``.

        Accepts:
        * ``None`` → ``None``
        * ``ErrorGuidance`` → passthrough
        * ``dict`` → coerced (empty ``dict`` → ``None``)
        """
        if value is None:
            return None
        if isinstance(value, ErrorGuidance):
            return value
        if isinstance(value, dict):
            if not value:
                return None
            return cls(
                # reject unknown keys and coerce hints to GuidanceHint
                **{
                    **value,
                    "hints": tuple(GuidanceHint(**h) for h in value.get("hints") or ()),
                }
            )
        raise TypeError(
            f"guidance must be dict or ErrorGuidance, not {type(value).__name__}"
        )

    def format(self, exception: CondaError) -> str:
        """Format this guidance for terminal output.

        ``str(exception)`` is used as the headline unless ``summary`` is set.
        """
        message = str(exception)
        headline = self.summary.rstrip() if self.summary else message.rstrip()
        lines = [f"{exception.__class__.__name__}: {headline}"]
        if self.cause or self.hints:
            lines.append("")
        if self.cause:
            lines.append(f"Cause: {self.cause.rstrip()}")
        if self.hints:
            hint_items = [
                f"({hint.hint_code}) {hint.text}".rstrip() for hint in self.hints
            ]
            lines.append(f"Next steps:{dashlist(hint_items, indent=2)}")
        return "\n".join(lines)
