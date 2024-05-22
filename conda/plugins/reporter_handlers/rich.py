# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
Defines a "rich" reporter handler

This reporter handler provides the default output for conda.
"""

from __future__ import annotations

from os.path import basename, dirname
from typing import TYPE_CHECKING

from rich.progress import Progress

from ...base.constants import ROOT_ENV_NAME
from ...common.io import ProgressBarBase
from ...common.path import paths_equal
from ...exceptions import CondaError
from .. import CondaReporterHandler, hookimpl
from ..types import ReporterHandlerBase

if TYPE_CHECKING:
    from typing import Callable, ContextManager


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


class RichProgressBar(ProgressBarBase):
    def __init__(
        self,
        description: str,
        render: Callable,
        position=None,
        leave=True,
        progress_context_managers=None,
    ) -> None:
        super().__init__(description, render)

        self.progress = None

        # We are passed in a list of context managers. Only one of them
        # is allowed to be the ``rich.Progress`` one we've defined. We
        # find it and then set it to ``self.progress``.
        for progress in progress_context_managers:
            if isinstance(progress, Progress):
                self.progress = progress
                break

        # Unrecoverable state has been reached
        if self.progress is None:
            raise CondaError(
                "Rich is configured, but there is no progress bar available"
            )

        self.progress = progress
        self.task = self.progress.add_task(description, total=1)

    def update_to(self, fraction) -> None:
        self.progress.update(self.task, completed=fraction)

        if fraction == 1:
            self.progress.update(self.task, visible=False)

    def close(self) -> None:
        self.progress.stop_task(self.task)

    def refresh(self) -> None:
        self.progress.refresh()


class RichReporterHandler(ReporterHandlerBase):
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
        """
        Determines whether to return a RichProgressBar or QuietProgressBar
        """
        quiet = settings.get("quiet") if settings is not None else False

        if quiet:
            return QuietProgressBar(description, render, **kwargs)
        else:
            return RichProgressBar(description, render, **kwargs)

    @classmethod
    def progress_bar_context_manager(cls) -> ContextManager:
        return Progress(transient=True)


@hookimpl
def conda_reporter_handlers():
    """
    Reporter handler for console

    This is the default reporter handler that returns what is displayed by default in conda
    """
    yield CondaReporterHandler(
        name="rich",
        description="Rich implementation for console reporting in conda",
        handler=RichReporterHandler(),
    )
