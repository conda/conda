# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Built-in plugin hooks for opt-in preview features."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..base.context import context
from . import hookimpl

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

    from .types import CondaSubcommand

PREVIEW_PLUGIN_NAME = __name__


@hookimpl
def conda_subcommands():
    from .._preview.env_setup import PREVIEW_LABEL as ENV_SETUP_PREVIEW_LABEL
    from .._preview.env_setup.cli import main_create, main_install

    yield from _preview_subcommands(
        ENV_SETUP_PREVIEW_LABEL,
        main_create.conda_subcommands,
        main_install.conda_subcommands,
    )


def _preview_subcommands(
    label: str,
    *subcommand_hooks: Callable[[], Iterable[CondaSubcommand]],
) -> Iterable[CondaSubcommand]:
    if not context.preview_enabled(label):
        return

    for subcommand_hook in subcommand_hooks:
        yield from subcommand_hook()


def is_preview_subcommand(plugin_subcommand: CondaSubcommand) -> bool:
    """
    Determine whether this plugin subcommand is a bundled preview command.
    """
    plugin_name = getattr(getattr(plugin_subcommand, "impl", None), "plugin_name", "")

    return plugin_name == PREVIEW_PLUGIN_NAME
