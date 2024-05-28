# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
Defines a "console" reporter handler.

This reporter handler provides the default output for conda.
"""

from __future__ import annotations

from os.path import basename, dirname

from ...base.constants import ROOT_ENV_NAME
from ...base.context import context
from ...common.path import paths_equal
from .. import CondaReporterHandler, hookimpl
from ..types import ReporterHandlerBase


class ConsoleReporterHandler(ReporterHandlerBase):
    """
    Default implementation for console reporting in conda
    """

    def detail_view(self, data: dict[str, str | int | bool], **kwargs) -> str:
        table_parts = [""]
        longest_header = max(map(len, data.keys()))

        for header, value in data.items():
            table_parts.append(f" {header:>{longest_header}} : {value}")

        table_parts.append("\n")

        return "\n".join(table_parts)

    def envs_list(self, prefixes, **kwargs) -> str:
        output = ["", "# conda environments:", "#"]

        def disp_env(prefix):
            active = "*" if prefix == context.active_prefix else " "
            if prefix == context.root_prefix:
                name = ROOT_ENV_NAME
            elif any(
                paths_equal(envs_dir, dirname(prefix)) for envs_dir in context.envs_dirs
            ):
                name = basename(prefix)
            else:
                name = ""
            return f"{name:20} {active} {prefix}"

        for env_prefix in prefixes:
            output.append(disp_env(env_prefix))

        output.append("\n")

        return "\n".join(output)


@hookimpl
def conda_reporter_handlers():
    """
    Reporter handler for console
    """
    yield CondaReporterHandler(
        name="console",
        description="Default implementation for console reporting in conda",
        handler=ConsoleReporterHandler(),
    )
