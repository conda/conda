# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
Defines a "console" reporter handler

This reporter handler provides the default output for conda.
"""

from __future__ import annotations

import sys
from errno import EPIPE, ESHUTDOWN
from os.path import basename, dirname
from typing import TYPE_CHECKING

from ...base.constants import ROOT_ENV_NAME
from ...common.io import ProgressBarBase, swallow_broken_pipe
from ...common.path import paths_equal
from .. import CondaReporterHandler, hookimpl
from ..types import ReporterHandlerBase

if TYPE_CHECKING:
    from typing import Callable


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
    TODO: This still doesn't work correctly; I need to add back the logic for ``self.enabled``
    """

    def __init__(
        self, description: str, render: Callable, position=None, leave=True, **kwargs
    ) -> None:
        super().__init__(description, render)

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


class RichProgressBar(ProgressBarBase):
    def __init__(
        self,
        description: str,
        render: Callable,
        position=None,
        leave=True,
        progress=None,
    ) -> None:
        super().__init__(description, render)

        self.enabled = True

        self.progress = progress
        self.task = self.progress.add_task(description, total=1)
        self.last_advance = 0

    def update_to(self, fraction) -> None:
        self.progress.update(self.task, completed=fraction)

        if fraction == 1:
            self.progress.update(self.task, visible=False)

    def close(self) -> None:
        """"""
        # self.progress.update(self.task, visible=False)
        self.progress.remove_task(self.task)
        # self.progress.stop()

    def refresh(self) -> None:
        """"""
        # self.progress.refresh()


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
        # TODO: what happens when this is ``None``?
        context = kwargs.get("context")

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
        self, description: str, render, settings=None, **kwargs
    ) -> ProgressBarBase:
        """Determines whether to return a TQDMProgressBar or QuietProgressBar"""
        quiet = settings.get("quiet") if settings is not None else False

        if quiet:
            return QuietProgressBar(description, render, **kwargs)
        else:
            return RichProgressBar(description, render, **kwargs)
            # return TQDMProgressBar(description, render, **kwargs)


@hookimpl
def conda_reporter_handlers():
    """
    Reporter handler for console

    This is the default reporter handler that returns what is displayed by default in conda
    """
    yield CondaReporterHandler(
        name="console",
        description="Default implementation for console reporting in conda",
        handler=ConsoleReporterHandler(),
    )
