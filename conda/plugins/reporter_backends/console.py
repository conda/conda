# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
Defines a "console" reporter backend.

This reporter backend provides the default output for conda.
"""

from __future__ import annotations

import sys
from errno import EPIPE, ESHUTDOWN
from os.path import basename, dirname

from ...base.constants import DEFAULT_CONSOLE_REPORTER_BACKEND, ROOT_ENV_NAME
from ...base.context import context
from ...common.io import swallow_broken_pipe
from ...common.path import paths_equal
from .. import CondaReporterBackend, hookimpl
from ..types import ProgressBarBase, ReporterRendererBase


class QuietProgressBar(ProgressBarBase):
    """
    Progress bar class used when no output should be printed
    """

    def update_to(self, fraction) -> None:
        pass

    def refresh(self) -> None:
        pass

    def close(self) -> None:
        pass


class TQDMProgressBar(ProgressBarBase):
    """
    Progress bar class used for tqdm progress bars
    """

    def __init__(
        self,
        description: str,
        position=None,
        leave=True,
        **kwargs,
    ) -> None:
        super().__init__(description)

        self.enabled = True

        bar_format = "{desc}{bar} | {percentage:3.0f}% "

        try:
            self.pbar = self._tqdm(
                desc=description,
                bar_format=bar_format,
                ascii=True,
                total=1,
                file=sys.stdout,
                position=position,
                leave=leave,
            )
        except OSError as e:
            if e.errno in (EPIPE, ESHUTDOWN):
                self.enabled = False
            else:
                raise

    def update_to(self, fraction) -> None:
        try:
            if self.enabled:
                self.pbar.update(fraction - self.pbar.n)
        except OSError as e:
            if e.errno in (EPIPE, ESHUTDOWN):
                self.enabled = False
            else:
                raise

    @swallow_broken_pipe
    def close(self) -> None:
        if self.enabled:
            self.pbar.close()

    def refresh(self) -> None:
        if self.enabled:
            self.pbar.refresh()

    @staticmethod
    def _tqdm(*args, **kwargs):
        """Deferred import so it doesn't hit the `conda activate` paths."""
        from tqdm.auto import tqdm

        return tqdm(*args, **kwargs)


class ConsoleReporterRenderer(ReporterRendererBase):
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

    def envs_list(self, prefixes, output=True, **kwargs) -> str:
        if not output:
            return ""

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

    def progress_bar(
        self,
        description: str,
        **kwargs,
    ) -> ProgressBarBase:
        """
        Determines whether to return a TQDMProgressBar or QuietProgressBar
        """
        if context.quiet:
            return QuietProgressBar(description, **kwargs)
        else:
            return TQDMProgressBar(description, **kwargs)


@hookimpl(
    tryfirst=True
)  # make sure the default console reporter backend can't be overridden
def conda_reporter_backends():
    """
    Reporter backend for console
    """
    yield CondaReporterBackend(
        name=DEFAULT_CONSOLE_REPORTER_BACKEND,
        description="Default implementation for console reporting in conda",
        renderer=ConsoleReporterRenderer,
    )
