# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from typing import TYPE_CHECKING

from conda.models.channel import Channel
from conda.models.match_spec import MatchSpec
from conda.plugins.reporter_backends import plugins as reporter_backend_plugins
from conda.plugins.solve_lifecycle.reporter_bridge import _lifecycle_to_reporter
from conda.plugins.types import (
    SolveLifecycleBegin,
    SolveLifecycleEndFailure,
    SolveLifecycleEndSuccess,
)

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from conda.plugins.manager import CondaPluginManager


def test_lifecycle_bridge_begin_to_solve_started(mocker: MockerFixture):
    emit = mocker.patch("conda.reporters.emit_install_like_progress")
    _lifecycle_to_reporter(
        SolveLifecycleBegin(
            span_id="s1",
            prefix="/p",
            solver="classic",
            repodata_fn="repodata.json",
            command=None,
            specs_to_add_count=1,
            specs_to_remove_count=0,
        )
    )
    emit.assert_called_once_with({"kind": "solve_started"})


def test_lifecycle_bridge_end_success_to_solve_finished(mocker: MockerFixture):
    emit = mocker.patch("conda.reporters.emit_install_like_progress")
    _lifecycle_to_reporter(
        SolveLifecycleEndSuccess(
            span_id="s1",
            prefix="/p",
            solver="classic",
            repodata_fn="repodata.json",
            command=None,
            duration_s=1,
            duration_ms=2.5,
            unlink_count=0,
            link_count=3,
            record_count=3,
        )
    )
    emit.assert_called_once_with(
        {
            "kind": "solve_finished",
            "record_count": 3,
            "duration_seconds": 1,
            "duration_ms": 2.5,
        }
    )


def test_lifecycle_bridge_end_failure_to_solve_failed(mocker: MockerFixture):
    emit = mocker.patch("conda.reporters.emit_install_like_progress")
    _lifecycle_to_reporter(
        SolveLifecycleEndFailure(
            span_id="s1",
            prefix="/p",
            solver="classic",
            repodata_fn="repodata.json",
            command=None,
            duration_s=0,
            duration_ms=1.0,
            error_type="ValueError",
            error_message="bad spec",
        )
    )
    emit.assert_called_once_with(
        {
            "kind": "solve_failed",
            "error_type": "ValueError",
            "error_message": "bad spec",
        }
    )


def test_solve_lifecycle_bridge_once_per_solve_line(
    capsys,
    mocker: MockerFixture,
    plugin_manager: CondaPluginManager,
    tmp_path,
):
    """With built-in bridge loaded, solve_finished line is emitted once."""
    from conda.core.solve import Solver
    from conda.plugins import solve_lifecycle as solve_lifecycle_pkg

    plugin_manager.load_plugins(*reporter_backend_plugins)
    plugin_manager.load_plugins(*solve_lifecycle_pkg.plugins)
    mocker.patch.object(Solver, "solve_for_diff", return_value=((), ()))

    prefix = str(tmp_path / "env-bridge")
    solver = Solver(
        prefix,
        channels=[Channel("defaults")],
        subdirs=("linux-64",),
        specs_to_add=[MatchSpec("python")],
    )
    solver.solve_for_transaction()
    out = capsys.readouterr().out
    assert out.count("solving") == 1
    assert "packages" in out


def test_install_plan_table_console_contains_package_plan() -> None:
    from conda.plugins.reporter_backends.console import ConsoleReporterRenderer

    rows = [
        {
            "status": "+",
            "name": "python",
            "version": "3.12",
            "build": "0",
            "channel": "defaults",
            "subdir": "linux-64",
            "requested": "python 3.12",
            "style": "green bold",
        }
    ]
    out = ConsoleReporterRenderer().install_like_progress(
        {
            "kind": "install_plan_table",
            "rows": rows,
            "caption": "Legend: bold=requested",
            "prefix": "/tmp/p",
            "specs_to_add": ["python 3.12"],
            "specs_to_remove": [],
        }
    )
    assert "Package Plan" in out
    assert "python" in out


def test_transaction_prepare_tty_is_silent(monkeypatch) -> None:
    import sys

    from conda.plugins.reporter_backends.console import ConsoleReporterRenderer

    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    out = ConsoleReporterRenderer().install_like_progress(
        {"kind": "transaction_prepare"}
    )
    assert out == ""


def test_transaction_prepare_non_tty_emits(monkeypatch) -> None:
    import sys

    from conda.plugins.reporter_backends.console import ConsoleReporterRenderer

    monkeypatch.setattr(sys.stdout, "isatty", lambda: False)
    out = ConsoleReporterRenderer().install_like_progress(
        {"kind": "transaction_prepare"}
    )
    assert "preparing transaction" in out
