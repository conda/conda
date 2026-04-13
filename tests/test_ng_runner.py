# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from __future__ import annotations

import pytest

pytest.importorskip("rattler")

from rattler import MatchSpec

from conda._ng.runner import (
    RattlerRunner,
    SolveFinished,
    SolveStarted,
    build_create_request,
    build_install_request,
    invocation_from_install_like,
    merge_specs_for_solve,
    shared_cli_create_supported,
    shared_cli_engine,
    shared_cli_install_supported,
)
from conda._ng.runner.rattler_runner import _emit


def test_emit_install_like_progress_solve_finished(capsys) -> None:
    from conda.reporters import emit_install_like_progress

    emit_install_like_progress(
        {
            "kind": "solve_finished",
            "record_count": 2,
            "duration_seconds": 0,
            "duration_ms": 5.0,
        }
    )
    out = capsys.readouterr().out
    assert "solving" in out
    assert "2 packages" in out


def test_merge_specs_for_solve_user_spec_wins_over_history_same_name() -> None:
    history = [MatchSpec("numpy 1.*")]
    specs = [MatchSpec("numpy 2.*")]
    merged = merge_specs_for_solve(history, specs)
    assert len(merged) == 1
    assert "2" in str(merged[0])


def test_merge_specs_for_solve_union_distinct_names() -> None:
    merged = merge_specs_for_solve(
        [MatchSpec("python 3.11")],
        [MatchSpec("pip")],
    )
    names = {m.name.normalized for m in merged}
    assert names == {"python", "pip"}


def test_build_create_request_fields() -> None:
    spec = MatchSpec("python")
    req = build_create_request(
        specs=(spec,),
        channels=("conda-forge",),
        platform="linux-64",
        target_prefix="/tmp/prefix-create-test",
        virtual_packages=None,
        dry_run=True,
        report=False,
    )
    assert req.specs == (spec,)
    assert req.dry_run is True
    assert req.report is False


def test_build_install_request_locked_optional() -> None:
    spec = MatchSpec("pip")
    hist = [MatchSpec("python 3.11")]
    req = build_install_request(
        specs=(spec,),
        history=hist,
        locked_packages=None,
        channels=("defaults",),
        platform="osx-arm64",
        target_prefix="/tmp/p",
        virtual_packages=(),
        dry_run=False,
        report=True,
    )
    assert req.history == hist
    assert req.locked_packages is None


def test_rattler_runner_create_routes_through_run_transaction() -> None:
    captured: dict = {}

    def capture(**kwargs):
        captured.update(kwargs)
        return []

    runner = RattlerRunner()
    runner.run_transaction = capture  # type: ignore[method-assign]

    spec = MatchSpec("python")
    runner.create(
        build_create_request(
            specs=(spec,),
            channels=("conda-forge",),
            platform="linux-64",
            target_prefix="/tmp/ng-runner-test",
            virtual_packages=None,
            dry_run=True,
            report=False,
        )
    )
    assert captured["history"] == ()
    assert captured["locked_packages"] is None
    assert captured["removing"] is False
    assert list(captured["specs"]) == [spec]


def test_rattler_runner_install_passes_history_and_locked() -> None:
    captured: dict = {}

    def capture(**kwargs):
        captured.update(kwargs)
        return []

    runner = RattlerRunner()
    runner.run_transaction = capture  # type: ignore[method-assign]

    s = MatchSpec("pip")
    h = [MatchSpec("python 3.11")]
    locked = ()
    runner.install(
        build_install_request(
            specs=(s,),
            history=h,
            locked_packages=locked,
            channels=("conda-forge",),
            platform="linux-64",
            target_prefix="/tmp/ng-install-test",
            virtual_packages=None,
            dry_run=True,
            report=False,
        )
    )
    assert list(captured["history"]) == h
    assert captured["locked_packages"] == locked
    assert list(captured["specs"]) == [s]


def test_emit_progress_callback_order() -> None:
    events = []

    def cb(ev):
        events.append(type(ev).__name__)

    _emit(cb, SolveStarted())
    _emit(cb, SolveFinished(record_count=3, duration_seconds=0, duration_ms=12.0))
    assert events == ["SolveStarted", "SolveFinished"]


def test_emit_ignores_none_callback() -> None:
    _emit(None, SolveStarted())


def test_invocation_from_install_like(monkeypatch) -> None:
    from argparse import Namespace
    from unittest.mock import MagicMock

    import conda.base.context as bc

    fake = MagicMock()
    fake.target_prefix = "/tmp/inv-test"
    monkeypatch.setattr(bc, "context", fake)
    inv = invocation_from_install_like(
        Namespace(packages=["python=3.12", "pip"]),
        MagicMock(),
        "install",
    )
    assert inv.command == "install"
    assert inv.spec_strings == ("python=3.12", "pip")
    assert str(inv.target_prefix).endswith("inv-test")


def test_shared_cli_create_supported_flags() -> None:
    from argparse import Namespace

    assert (
        shared_cli_create_supported(Namespace(packages=["x"], file=(), clone=None))
        is True
    )
    assert (
        shared_cli_create_supported(Namespace(packages=[], file=(), clone=None))
        is False
    )
    assert (
        shared_cli_create_supported(
            Namespace(packages=["x"], file=["a.yml"], clone=None)
        )
        is False
    )


def test_shared_cli_install_supported_flags() -> None:
    from argparse import Namespace

    assert (
        shared_cli_install_supported(Namespace(packages=["x"], file=(), revision=None))
        is True
    )
    assert (
        shared_cli_install_supported(Namespace(packages=[], file=(), revision=None))
        is False
    )


def test_shared_cli_engine_reads_experimental(monkeypatch) -> None:
    from conda.base.context import context

    monkeypatch.setattr(context, "experimental", ("shared_cli_rattler",), raising=False)
    assert shared_cli_engine() == "rattler"
    monkeypatch.setattr(context, "experimental", ("shared_cli_classic",), raising=False)
    assert shared_cli_engine() == "classic"
    monkeypatch.setattr(context, "experimental", (), raising=False)
    assert shared_cli_engine() is None


def test_classic_runner_install_cli_calls_conda_install(mocker) -> None:
    from argparse import Namespace
    from unittest.mock import MagicMock

    patched = mocker.patch("conda.cli.install.install")
    from conda._ng.runner.classic_runner import ClassicCondaRunner
    from conda._ng.runner.invocation import InstallLikeInvocation

    parser = MagicMock()
    inv = InstallLikeInvocation(
        args=Namespace(),
        parser=parser,
        command="install",
        target_prefix=__import__("pathlib").Path("/tmp/p"),
        spec_strings=("pip",),
    )
    tuple(ClassicCondaRunner().install_cli(inv))
    patched.assert_called_once_with(inv.args, parser, "install")
