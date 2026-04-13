# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Map runner :class:`ProgressEvent` objects to ``conda.reporters`` output."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .types import (
    AwaitingConfirmation,
    SolveFinished,
    SolveStarted,
    TransactionFinished,
    TransactionStarted,
)

if TYPE_CHECKING:
    from .types import (
        ProgressEvent,
    )


def progress_to_reporter(event: ProgressEvent) -> None:
    """Emit optional console/JSON lines for install-like progress (best-effort)."""
    payload = _event_to_payload(event)
    if not payload:
        return

    try:
        from conda.reporters import emit_install_like_progress

        emit_install_like_progress(payload)
    except (AttributeError, TypeError, ValueError, OSError):
        return


def _event_to_payload(event: ProgressEvent) -> dict[str, object] | None:
    if isinstance(event, SolveStarted):
        return {"kind": "solve_started"}
    if isinstance(event, SolveFinished):
        return {
            "kind": "solve_finished",
            "record_count": event.record_count,
            "duration_seconds": event.duration_seconds,
            "duration_ms": event.duration_ms,
        }
    if isinstance(event, AwaitingConfirmation):
        return {"kind": "awaiting_confirmation", "prefix": str(event.prefix)}
    if isinstance(event, TransactionStarted):
        return {"kind": "transaction_started"}
    if isinstance(event, TransactionFinished):
        return {"kind": "transaction_finished"}
    return None
