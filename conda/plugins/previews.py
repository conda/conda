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

    if context.preview_enabled(ENV_SETUP_PREVIEW_LABEL):
        from .._preview.env_setup.cli import main_create, main_install

        yield from main_create.conda_subcommands()
        yield from main_install.conda_subcommands()


def is_preview_subcommand(plugin_subcommand: CondaSubcommand) -> bool:
    """Return whether *plugin_subcommand* was yielded by ``conda.plugins.previews``.

    Checks ``plugin_subcommand.impl.plugin_name`` (hook provenance set by the plugin manager).
    """
    plugin_name = getattr(getattr(plugin_subcommand, "impl", None), "plugin_name", "")

    return plugin_name == PREVIEW_PLUGIN_NAME
