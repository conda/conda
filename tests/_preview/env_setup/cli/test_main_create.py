# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Integration tests for conda/_preview/env_setup/cli/main_create.py.

These tests verify that:
- When the env-setup preview is NOT enabled, `conda create` runs via the standard path.
- When the env-setup preview IS enabled, `conda create` is routed to the stub and
  raises OperationNotAllowed.
- An unrecognized preview label does not crash `conda create`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from conda.exceptions import OperationNotAllowed
from conda.plugins.manager import get_plugin_manager

if TYPE_CHECKING:
    from pytest import MonkeyPatch

    from conda.testing.fixtures import CondaCLIFixture


def test_create_preview_disabled(conda_cli: CondaCLIFixture):
    """conda create without CONDA_PREVIEW set routes to the standard implementation."""
    # --help exits cleanly via SystemExit(0); if routing had fired it would raise
    # OperationNotAllowed instead, so a clean SystemExit proves no redirection occurred.
    with pytest.raises(SystemExit, match="0"):
        conda_cli("create", "--help")


def test_create_preview_enabled(
    conda_cli: CondaCLIFixture,
    monkeypatch: MonkeyPatch,
):
    """conda create with CONDA_PREVIEW=env-setup is routed to the stub."""
    monkeypatch.setenv("CONDA_PREVIEW", "env-setup")

    with pytest.raises(OperationNotAllowed, match=r"'env-setup'.+'conda create'"):
        conda_cli("create", "--name", "test-env", "python")


def test_create_preview_enabled_with_no_plugins(
    conda_cli: CondaCLIFixture,
    monkeypatch: MonkeyPatch,
):
    """Bundled preview subcommands remain available with --no-plugins."""
    monkeypatch.setenv("CONDA_PREVIEW", "env-setup")

    get_plugin_manager.cache_clear()
    try:
        out, err, exc = conda_cli(
            "--no-plugins",
            "create",
            "--name",
            "test-env",
            "python",
            raises=OperationNotAllowed,
        )
    finally:
        get_plugin_manager.cache_clear()

    assert exc.value is not None
    assert "env-setup" in str(exc.value)
    assert "conda create" in str(exc.value)


def test_create_preview_uses_builtin_parser_arguments(
    conda_cli: CondaCLIFixture,
    monkeypatch: MonkeyPatch,
):
    """The preview stub accepts options from the built-in create parser."""
    monkeypatch.setenv("CONDA_PREVIEW", "env-setup")

    out, err, exc = conda_cli(
        "create", "--clone", "base", "--name", "test-env", raises=OperationNotAllowed
    )

    assert exc.value is not None
    assert "env-setup" in str(exc.value)
    assert "conda create" in str(exc.value)


def test_create_preview_can_extend_builtin_parser(
    conda_cli: CondaCLIFixture,
    monkeypatch: MonkeyPatch,
):
    """A preview override can add options to the built-in command parser."""
    from conda._preview.env_setup.cli import main_create
    from conda.plugins.types import CondaSubcommand

    def configure_parser(parser):
        parser.add_argument("--preview-only-option", action="store_true")

    def execute(args):
        assert args.preview_only_option is True
        raise OperationNotAllowed("preview-only option parsed")

    def conda_subcommands():
        yield CondaSubcommand(
            name="create",
            summary="Create a new conda environment.",
            action=execute,
            configure_parser=configure_parser,
        )

    monkeypatch.setattr(main_create, "conda_subcommands", conda_subcommands)
    monkeypatch.setenv("CONDA_PREVIEW", "env-setup")

    out, err, exc = conda_cli(
        "create",
        "--name",
        "test-env",
        "--preview-only-option",
        raises=OperationNotAllowed,
    )

    assert exc.value is not None
    assert "preview-only option parsed" in str(exc.value)


def test_unknown_preview_label_no_crash(
    conda_cli: CondaCLIFixture,
    monkeypatch: MonkeyPatch,
):
    """An unrecognized preview label produces no crash; the normal path is used."""
    monkeypatch.setenv("CONDA_PREVIEW", "typo-label")

    # --help exits cleanly; proves normal path was followed despite unknown label
    with pytest.raises(SystemExit, match="0"):
        conda_cli("create", "--help")
