# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Map solve lifecycle events to ``emit_install_like_progress`` (classic + rattler CLI parity)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from conda import plugins
from conda.plugins.types import (
    CondaSolveLifecycle,
    SolveLifecycleBegin,
    SolveLifecycleEndFailure,
    SolveLifecycleEndSuccess,
)

if TYPE_CHECKING:
    from collections.abc import Iterable

    from conda.plugins.types import (
        SolveLifecycleEvent,
    )


def _lifecycle_to_reporter(event: SolveLifecycleEvent) -> None:
    from conda.reporters import emit_install_like_progress

    if isinstance(event, SolveLifecycleBegin):
        emit_install_like_progress({"kind": "solve_started"})
        return
    if isinstance(event, SolveLifecycleEndSuccess):
        emit_install_like_progress(
            {
                "kind": "solve_finished",
                "record_count": event.record_count,
                "duration_seconds": event.duration_s,
                "duration_ms": event.duration_ms,
            }
        )
        return
    if isinstance(event, SolveLifecycleEndFailure):
        emit_install_like_progress(
            {
                "kind": "solve_failed",
                "error_type": event.error_type,
                "error_message": event.error_message,
            }
        )


class _BuiltinSolveLifecycleReporterBridge:
    @plugins.hookimpl
    def conda_solve_lifecycle(self) -> Iterable[CondaSolveLifecycle]:
        yield CondaSolveLifecycle(
            name="builtin-reporter-bridge",
            on_event=_lifecycle_to_reporter,
        )


builtin_solve_lifecycle_reporter_bridge = _BuiltinSolveLifecycleReporterBridge()
