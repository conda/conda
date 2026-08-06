# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Structured error guidance for user-facing error messages.

``ErrorGuidance`` can be attached to ``conda.CondaError`` via the ``guidance`` keyword
so that terminal and `--json` output share the same logical cause / hint structure.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from typing import TYPE_CHECKING

from .. import CondaError
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
    """A single actionable hint with a stable ``hint_code``."""

    text: str
    """Human-readable description of the action to take."""
    hint_code: str
    """Stable machine-readable identifier. Use snake_case."""


@dataclass(frozen=True)
class ErrorGuidance:
    """Structured guidance for solution-oriented error messages.

    When attached to a ``CondaError``, the display layer renders the cause
    and hints alongside the exception's ``message``.
    """

    summary: str | None = None
    """Optional headline overriding ``message`` for user-facing output."""
    cause: str | None = None
    """Explanation of what went wrong, distinct from the raw error text."""
    hints: tuple[GuidanceHint, ...] = ()
    """Ordered list of actionable next steps. Rendered in order."""

    def __post_init__(self) -> None:
        if not self.summary and not self.cause and not self.hints:
            raise ValueError(
                "at least one of summary, cause, or hints must be provided"
            )

    @property
    def hint_codes(self) -> tuple[str, ...]:
        """Hint codes extracted from ``hints`` for JSON serialization."""
        return tuple(hint.hint_code for hint in self.hints)

    def __json__(self) -> dict[str, object]:
        """Serialize for ``CondaError.dump_map``."""
        result = asdict(self)
        result["hint_codes"] = self.hint_codes
        return {k: v for k, v in result.items() if v}

    @classmethod
    def from_hints(cls, hints: Iterable[GuidanceHint]) -> ErrorGuidance | None:
        """Create guidance from hints, deduplicating by ``hint_code``."""
        merged_hints = []
        seen_hint_codes = set()
        for hint in hints:
            if hint.hint_code in seen_hint_codes:
                continue
            seen_hint_codes.add(hint.hint_code)
            merged_hints.append(hint)
        if not merged_hints:
            return None
        return cls(hints=tuple(merged_hints))

    def with_hints(self, hints: Iterable[GuidanceHint]) -> ErrorGuidance:
        """Return this guidance with additional hints appended.

        Existing hints keep priority when ``hint_code`` values collide.
        """
        hints = tuple(hints)
        if not hints:
            return self
        guidance = self.from_hints((*self.hints, *hints))
        if guidance is None or guidance.hints == self.hints:
            return self
        return replace(self, hints=guidance.hints)

    @classmethod
    def coerce(cls, value: Any) -> ErrorGuidance | None:
        """Coerce *value* to ``ErrorGuidance`` or ``None``.

        Args:
            value: ``None`` returns ``None``, ``ErrorGuidance`` passes
                through, a ``dict`` is coerced (empty ``dict`` returns
                ``None``).

        Returns:
            ``None`` or an ``ErrorGuidance`` instance.
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

        Args:
            exception: ``str(exception)`` is used as the headline unless
                ``summary`` is set.

        Returns:
            Formatted string including the exception class name, cause,
            and actionable hints.
        """
        if not isinstance(exception, CondaError):
            raise ValueError(f"expected CondaError, got {type(exception).__name__}")
        headline = (self.summary or str(exception)).rstrip()
        lines = [f"{exception.__class__.__name__}: {headline}"]
        if self.cause or self.hints:
            lines.append("")
        if self.cause:
            lines.append(f"Cause: {self.cause.rstrip()}")
        if self.hints:
            hints = (f"({hint.hint_code}) {hint.text}".rstrip() for hint in self.hints)
            lines.append(f"Next steps:{dashlist(hints, indent=2)}")
        return "\n".join(lines)
