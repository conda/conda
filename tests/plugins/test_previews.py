# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Unit tests for conda.plugins.previews."""

from __future__ import annotations

from unittest.mock import MagicMock

import conda.plugins.previews as previews
from conda._preview.env_setup import PREVIEW_LABEL as ENV_SETUP_PREVIEW_LABEL
from conda.base.context import reset_context
from conda.plugins.previews import (
    PREVIEW_PLUGIN_NAME,
    conda_subcommands,
    is_preview_subcommand,
)
from conda.plugins.types import CondaSubcommand


def test_preview_plugin_name_is_module_name():
    # The constant must equal the fully-qualified module name so that
    # is_preview_subcommand() can reliably identify bundled preview commands.
    assert PREVIEW_PLUGIN_NAME == "conda.plugins.previews"


def test_conda_subcommands_env_setup_disabled_yields_nothing(monkeypatch):
    """conda_subcommands yields nothing when the env-setup preview is off."""
    monkeypatch.setenv("CONDA_PREVIEW", "")
    reset_context()

    result = list(conda_subcommands())

    assert result == []


def test_conda_subcommands_env_setup_enabled_yields_create_and_install(monkeypatch):
    """conda_subcommands yields 'create' and 'install' when env-setup is enabled."""
    monkeypatch.setenv("CONDA_PREVIEW", ENV_SETUP_PREVIEW_LABEL)
    reset_context()

    result = list(conda_subcommands())

    names = [sc.name for sc in result]
    assert names == ["create", "install"]


def test_conda_subcommands_env_setup_subcommand_names(monkeypatch):
    """Each yielded CondaSubcommand has the expected name attribute."""
    monkeypatch.setenv("CONDA_PREVIEW", ENV_SETUP_PREVIEW_LABEL)
    reset_context()

    subcommands = {sc.name: sc for sc in conda_subcommands()}

    assert "create" in subcommands
    assert "install" in subcommands


def test_conda_subcommands_unrelated_preview_yields_nothing(monkeypatch):
    """Enabling an unrelated preview label does not activate env-setup subcommands."""
    monkeypatch.setenv("CONDA_PREVIEW", "some-other-preview")
    reset_context()

    result = list(conda_subcommands())

    assert result == []


def test_is_preview_subcommand_true_when_plugin_name_matches():
    """Returns True when impl.plugin_name equals PREVIEW_PLUGIN_NAME."""
    impl = MagicMock()
    impl.plugin_name = PREVIEW_PLUGIN_NAME

    sc = MagicMock(spec=CondaSubcommand)
    sc.impl = impl

    assert is_preview_subcommand(sc) is True


def test_is_preview_subcommand_false_when_plugin_name_differs():
    """Returns False when impl.plugin_name is a different string."""
    impl = MagicMock()
    impl.plugin_name = "some.other.plugin"

    sc = MagicMock(spec=CondaSubcommand)
    sc.impl = impl

    assert is_preview_subcommand(sc) is False


def test_is_preview_subcommand_false_when_no_impl():
    """Returns False when the subcommand has no impl attribute."""
    sc = MagicMock(spec=CondaSubcommand)
    # Remove the impl attribute so getattr falls back to the default ""
    del sc.impl

    assert is_preview_subcommand(sc) is False


def test_is_preview_subcommand_false_when_impl_has_no_plugin_name():
    """Returns False when impl exists but has no plugin_name attribute."""
    impl = MagicMock(spec=[])  # spec=[] means no attributes
    sc = MagicMock(spec=CondaSubcommand)
    sc.impl = impl

    assert is_preview_subcommand(sc) is False


def test_is_preview_subcommand_false_when_plugin_name_empty():
    """Returns False when impl.plugin_name is an empty string."""
    impl = MagicMock()
    impl.plugin_name = ""

    sc = MagicMock(spec=CondaSubcommand)
    sc.impl = impl

    assert is_preview_subcommand(sc) is False


def test_is_preview_subcommand_with_plugin_manager(
    plugin_manager,
    monkeypatch,
):
    """
    Subcommands registered via the previews module are identified as preview
    subcommands by is_preview_subcommand after going through get_subcommands(),
    which is the code path that sets impl on each CondaSubcommand.
    """
    monkeypatch.setenv("CONDA_PREVIEW", ENV_SETUP_PREVIEW_LABEL)
    reset_context()

    plugin_manager.register(previews)

    subcommands = plugin_manager.get_subcommands()

    preview_subcommands = [
        sc for sc in subcommands.values() if is_preview_subcommand(sc)
    ]
    assert len(preview_subcommands) == 2  # create + install

    non_preview_subcommands = [
        sc for sc in subcommands.values() if not is_preview_subcommand(sc)
    ]
    for sc in non_preview_subcommands:
        assert not is_preview_subcommand(sc)
