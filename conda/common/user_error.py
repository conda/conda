# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (C) 2026 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Structured user-facing error details.

Plugin authors and core code can attach :class:`UserFacingErrorDetails` to
:class:`conda.CondaError` so terminal and JSON output share the same logical content.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UserErrorHint:
    """A single actionable hint with an optional stable machine-readable code."""

    text: str
    hint_code: str | None = None


@dataclass(frozen=True)
class UserFacingErrorDetails:
    """Summary, optional cause, and ordered hints for solution-oriented errors."""

    summary: str
    cause: str | None = None
    hints: tuple[UserErrorHint, ...] = ()


def format_user_facing_error(details: UserFacingErrorDetails) -> str:
    """Format structured error details for plain-text terminal output."""
    lines = [details.summary.rstrip()]
    if details.cause:
        lines.append("")
        lines.append(details.cause.rstrip())
    if details.hints:
        lines.append("")
        lines.append("Next steps:")
        for i, hint in enumerate(details.hints, 1):
            lines.append(f"  {i}. {hint.text.rstrip()}")
    return "\n".join(lines) + "\n"


def user_facing_details_to_json(details: UserFacingErrorDetails) -> dict[str, object]:
    """Serialize :class:`UserFacingErrorDetails` for :meth:`CondaError.dump_map`."""
    return {
        "summary": details.summary,
        "cause": details.cause,
        "hints": [{"text": h.text, "hint_code": h.hint_code} for h in details.hints],
        "hint_codes": [h.hint_code for h in details.hints if h.hint_code],
    }
