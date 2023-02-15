# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import json

from conda.base.context import context
from conda.models.channel import Channel

from ... import CondaSubcommand, hookimpl


def display_cache_info() -> None:
    from conda.core import subdir_data

    for channel in context.channels:
        for subdir in ("noarch", "osx-aarch64"):
            channel = Channel(channel, platform=subdir)
            sd = subdir_data.SubdirData(channel)
            print(json.dumps(dict(repodata=sd.cache_path_json, state=sd.cache_path_state)))


def execute(argv: list[str]) -> None:
    """
    Show cache information for all channels.
    """
    display_cache_info()


@hookimpl
def conda_subcommands():
    yield CondaSubcommand(
        name="cache-info",
        summary="Display cache filenames for Navigator.",
        action=execute,
    )
