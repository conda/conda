# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from conda import plugins
from conda.models.channel import Channel
from conda.models.match_spec import MatchSpec
from conda.plugins.types import (
    SolveLifecycleBegin,
    SolveLifecycleEndFailure,
    SolveLifecycleEndSuccess,
)

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

    from conda.plugins.manager import CondaPluginManager


class SolveLifecyclePlugin:
    def __init__(self) -> None:
        self.events: list = []

    def on_event(self, event) -> None:
        self.events.append(event)

    @plugins.hookimpl
    def conda_solve_lifecycle(self):
        yield plugins.types.CondaSolveLifecycle(
            name="test-solve-lifecycle",
            on_event=self.on_event,
        )


@pytest.fixture
def solve_lifecycle_plugin(
    plugin_manager_with_reporter_backends: CondaPluginManager,
) -> SolveLifecyclePlugin:
    plugin = SolveLifecyclePlugin()
    plugin_manager_with_reporter_backends.register(plugin)
    return plugin


def test_solve_lifecycle_success_order(
    solve_lifecycle_plugin: SolveLifecyclePlugin,
    tmp_path,
    mocker: MockerFixture,
):
    from conda.core.solve import Solver

    prefix = str(tmp_path / "env")
    solver = Solver(
        prefix,
        channels=[Channel("defaults")],
        subdirs=("linux-64",),
        specs_to_add=[MatchSpec("python")],
    )
    mocker.patch.object(
        Solver,
        "solve_for_diff",
        return_value=((), ()),
    )

    solver.solve_for_transaction()

    ev = solve_lifecycle_plugin.events
    assert len(ev) == 2
    assert isinstance(ev[0], SolveLifecycleBegin)
    assert isinstance(ev[1], SolveLifecycleEndSuccess)
    assert ev[0].span_id == ev[1].span_id
    assert ev[0].prefix == prefix
    assert ev[1].unlink_count == 0
    assert ev[1].link_count == 0
    assert ev[1].record_count == 0


def test_solve_lifecycle_failure_emits_end_failure(
    solve_lifecycle_plugin: SolveLifecyclePlugin,
    tmp_path,
    mocker: MockerFixture,
):
    from conda.core.solve import Solver

    prefix = str(tmp_path / "env2")
    solver = Solver(
        prefix,
        channels=[Channel("defaults")],
        subdirs=("linux-64",),
        specs_to_add=[MatchSpec("python")],
    )
    mocker.patch.object(
        Solver,
        "solve_for_diff",
        side_effect=ValueError("solve boom"),
    )

    with pytest.raises(ValueError, match="solve boom"):
        solver.solve_for_transaction()

    ev = solve_lifecycle_plugin.events
    assert len(ev) == 2
    assert isinstance(ev[0], SolveLifecycleBegin)
    assert isinstance(ev[1], SolveLifecycleEndFailure)
    assert ev[0].span_id == ev[1].span_id
    assert ev[1].error_type == "ValueError"
    assert "solve boom" in ev[1].error_message
