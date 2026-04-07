# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
# Copyright (C) 2026 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Tests for install path when the solver produces an empty transaction."""

from __future__ import annotations

import json
from argparse import Namespace
from types import SimpleNamespace
from typing import TYPE_CHECKING

from conda.base.context import context, reset_context
from conda.cli.install import _nothing_to_do_message, handle_txn

if TYPE_CHECKING:
    from pytest import CaptureFixture, MonkeyPatch


def test_nothing_to_do_message_plain_when_not_conda_on_base(
    monkeypatch: MonkeyPatch,
) -> None:
    reset_context()
    monkeypatch.setenv("CONDA_JSON", "no")
    msg = _nothing_to_do_message("/some/prefix", "install", ("numpy",))
    assert "All requested packages already installed." in msg
    assert "constraints" not in msg.lower()


def test_nothing_to_do_message_extra_lines_for_conda_on_base(
    monkeypatch: MonkeyPatch,
) -> None:
    reset_context()
    monkeypatch.setenv("CONDA_JSON", "no")
    monkeypatch.setattr(context, "notify_outdated_conda", True)
    base = str(context.root_prefix)
    msg = _nothing_to_do_message(base, "update", ("conda",))
    assert "All requested packages already installed." in msg
    assert "newer conda" in msg.lower()


def test_handle_txn_nothing_to_do_conda_json_hints(
    monkeypatch: MonkeyPatch,
    capsys: CaptureFixture,
) -> None:
    monkeypatch.setenv("CONDA_JSON", "yes")
    reset_context()
    assert context.json
    monkeypatch.setattr(context, "notify_outdated_conda", True)

    txn = SimpleNamespace(nothing_to_do=True)
    base = str(context.root_prefix)
    args = Namespace()
    handle_txn(
        txn,
        base,
        args,
        newenv=False,
        install_command="install",
        requested_names=("conda",),
    )
    out = capsys.readouterr().out
    data = json.loads(out.strip())
    assert data["success"] is True
    assert data["message"] == "All requested packages already installed."
    assert data["hint_codes"] == ["conda_upgrade_blocked_hints"]
    assert "hint" in data
