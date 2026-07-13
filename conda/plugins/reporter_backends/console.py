# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
Defines a "console" reporter backend.

This reporter backend provides the default output for conda.
"""

from __future__ import annotations

import sys
from errno import EPIPE, ESHUTDOWN
from itertools import cycle
from threading import Event, Thread
from time import sleep
from typing import TYPE_CHECKING

from ...base.constants import (
    DEFAULT_CONSOLE_REPORTER_BACKEND,
)
from ...base.context import context
from ...common.io import swallow_broken_pipe
from ...common.path import paths_equal
from ...common.terminal import is_tty, term_dumb
from ...core.prefix_data import PrefixData
from ...exceptions import CondaError
from ...utils import human_bytes
from .. import hookimpl
from ..types import (
    CondaReporterBackend,
    ProgressBarBase,
    ReporterRendererBase,
    SpinnerBase,
)

if TYPE_CHECKING:
    from collections.abc import Iterable
    from typing import Any

    from ...common.path import PathType
    from ..reporter_backends.events import (
        DetailViewEvent,
        EnvsListEvent,
        FetchSectionEndEvent,
        FetchSectionStartEvent,
        FetchTaskEndEvent,
        FetchTaskProgressEvent,
        FetchTaskStartEvent,
        RenderDataEvent,
        SpinnerEndEvent,
        SpinnerStartEvent,
    )


def _format_fetch_description(name: str, version: str, size: int | None) -> str:
    """Format a human-readable progress-bar description for a fetch task.

    This logic was previously inlined in
    ``ProgressiveFetchExtract._progress_bar()``.
    """
    description = ""
    if name and version:
        description = f"{name}-{version}"
    size_str = size and human_bytes(size) or ""
    if description:
        description = "%-20.20s | " % description
    if size_str:
        description += "%-9s | " % size_str
    return description


# ---------------------------------------------------------------------------
# Private widget classes (implementation details of ConsoleReporterRenderer)
# ---------------------------------------------------------------------------


class _QuietProgressBar(ProgressBarBase):
    """Progress bar used when no animated output should be produced."""

    def update_to(self, fraction) -> None:
        pass

    def refresh(self) -> None:
        pass

    def close(self) -> None:
        pass


class _TQDMProgressBar(ProgressBarBase):
    """Animated tqdm progress bar for TTY output."""

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


class _Spinner(SpinnerBase):
    spinner_cycle = cycle("/-\\|")

    def __init__(self, message, fail_message="failed\n"):
        super().__init__(message, fail_message)

        self.show_spin: bool = True
        self._stop_running = Event()
        self._spinner_thread = Thread(target=self._start_spinning)
        self._indicator_length = len(next(self.spinner_cycle)) + 1
        self.fh = sys.stdout

    def start(self):
        self._spinner_thread.start()

    def stop(self):
        self._stop_running.set()
        self._spinner_thread.join()
        self.show_spin = False

    def _start_spinning(self):
        try:
            while not self._stop_running.is_set():
                self.fh.write(next(self.spinner_cycle) + " ")
                self.fh.flush()
                sleep(0.10)
                self.fh.write("\b" * self._indicator_length)
        except OSError as e:
            if e.errno in (EPIPE, ESHUTDOWN):
                self.stop()
            else:
                raise

    @swallow_broken_pipe
    def __enter__(self):
        sys.stdout.write(f"{self.message}: ")
        sys.stdout.flush()
        self.start()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
        with swallow_broken_pipe:
            if exc_type or exc_val:
                sys.stdout.write(self.fail_message)
            else:
                sys.stdout.write("done\n")
            sys.stdout.flush()


class _QuietSpinner(SpinnerBase):
    def __enter__(self):
        sys.stdout.write(f"{self.message}: ")
        sys.stdout.flush()

        sys.stdout.write("...working... ")
        sys.stdout.flush()

    def __exit__(self, exc_type, exc_val, exc_tb):
        with swallow_broken_pipe:
            if exc_type or exc_val:
                sys.stdout.write(self.fail_message)
            else:
                sys.stdout.write("done\n")
            sys.stdout.flush()


# ---------------------------------------------------------------------------
# Deprecated public aliases — kept for third-party plugins during migration
# ---------------------------------------------------------------------------

QuietProgressBar = _QuietProgressBar
""".. deprecated:: 25.3  Use the ``render_*`` event methods instead."""
TQDMProgressBar = _TQDMProgressBar
""".. deprecated:: 25.3  Use the ``render_*`` event methods instead."""
Spinner = _Spinner
""".. deprecated:: 25.3  Use the ``render_*`` event methods instead."""
QuietSpinner = _QuietSpinner
""".. deprecated:: 25.3  Use the ``render_*`` event methods instead."""


# ---------------------------------------------------------------------------
# ConsoleReporterRenderer
# ---------------------------------------------------------------------------


class ConsoleReporterRenderer(ReporterRendererBase):
    """
    Default implementation for console reporting in conda.
    """

    def __init__(self) -> None:
        self._fetch_bars: dict[int, _TQDMProgressBar | _QuietProgressBar] = {}
        self._spinners: dict[str, _Spinner | _QuietSpinner] = {}

    @property
    def _animations_disabled(self) -> bool:
        """True when progress bars and spinners should be suppressed."""
        return context.quiet or not is_tty() or term_dumb()

    # ------------------------------------------------------------------
    # render_* event handlers
    # ------------------------------------------------------------------

    def render_data(self, event: RenderDataEvent) -> None:
        text = str(event.data)
        if not text.endswith("\n"):
            text += "\n"
        sys.stdout.write(text)

    def render_detail_view(self, event: DetailViewEvent) -> None:
        data = event.data
        longest_header = max(map(len, data.keys()))
        table_parts = []
        for header, value in data.items():
            table_parts.append(f" {header:>{longest_header}} : {value}")
        sys.stdout.write("\n" + "\n".join(table_parts) + "\n\n")

    def render_envs_list(self, event: EnvsListEvent) -> None:
        show_size = event.show_size
        output = [
            "# conda environments:",
            "#",
            "# * -> active",
            "# + -> frozen",
        ]

        def disp_env(prefix: PrefixData) -> str:
            active = (
                "*"
                if context.active_prefix
                and paths_equal(prefix.prefix_path, context.active_prefix)
                else " "
            )
            frozen = "+" if prefix.is_frozen() else " "
            if show_size:
                size_str = human_bytes(prefix.size())
                return f"{prefix.name:20} {active} {frozen} {size_str:>10} {prefix.prefix_path}"
            else:
                return f"{prefix.name:20} {active} {frozen} {prefix.prefix_path}"

        for env_prefix in event.prefixes:
            if not isinstance(env_prefix, PrefixData):
                env_prefix = PrefixData(env_prefix)
            output.append(disp_env(env_prefix))

        sys.stdout.write("\n" + "\n".join(output) + "\n\n")

    def render_spinner_start(self, event: SpinnerStartEvent) -> None:
        if self._animations_disabled:
            spinner: _Spinner | _QuietSpinner = _QuietSpinner(
                event.message, event.fail_message
            )
        else:
            spinner = _Spinner(event.message, event.fail_message)
        self._spinners[event.message] = spinner
        spinner.__enter__()

    def render_spinner_end(self, event: SpinnerEndEvent) -> None:
        spinner = self._spinners.pop(event.message, None)
        if spinner is not None:
            exc = None if event.success else Exception
            spinner.__exit__(exc, None, None)

    def render_fetch_section_start(self, event: FetchSectionStartEvent) -> None:
        if not context.verbose and not context.quiet and not context.json:
            print(
                "\nDownloading and Extracting Packages:",
                end="\n" if is_tty() and not term_dumb() else " ...working...",
            )

    def render_fetch_task_start(self, event: FetchTaskStartEvent) -> None:
        description = _format_fetch_description(event.name, event.version, event.size)
        if self._animations_disabled:
            bar: _TQDMProgressBar | _QuietProgressBar = _QuietProgressBar(description)
        else:
            bar = _TQDMProgressBar(description)
        self._fetch_bars[event.task_id] = bar

    def render_fetch_task_progress(self, event: FetchTaskProgressEvent) -> None:
        bar = self._fetch_bars.get(event.task_id)
        if bar is not None:
            bar.update_to(event.fraction)

    def render_fetch_task_end(self, event: FetchTaskEndEvent) -> None:
        bar = self._fetch_bars.get(event.task_id)
        if bar is not None:
            bar.finish()
            bar.refresh()

    def render_fetch_section_end(self, event: FetchSectionEndEvent) -> None:
        for bar in self._fetch_bars.values():
            bar.close()
        self._fetch_bars.clear()
        if not context.verbose and not context.quiet and not context.json:
            if is_tty() and not term_dumb():
                print("\r")
            else:
                print(" done")

    # ------------------------------------------------------------------
    # Synchronous query
    # ------------------------------------------------------------------

    def prompt(self, message="Proceed", choices=("yes", "no"), default="yes") -> str:
        """Implementation of a prompt dialog."""
        if default not in choices:
            raise ValueError(f"Default value '{default}' must be part of `choices`")
        options = []

        for option in choices:
            if option == default:
                options.append(f"[{option[0]}]")
            else:
                options.append(option[0])

        message = "{} ({})? ".format(message, "/".join(options))
        choices_map = {alt: choice for choice in choices for alt in [choice, choice[0]]}
        choices_map[""] = default
        while True:
            # raw_input has a bug and prints to stderr, not desirable
            sys.stdout.write(message)
            sys.stdout.flush()
            try:
                user_choice = sys.stdin.readline().strip().lower()
            except OSError as e:
                raise CondaError(f"cannot read from stdin: {e}")
            if user_choice not in choices_map:
                print(f"Invalid choice: {user_choice}")
            else:
                sys.stdout.write("\n")
                sys.stdout.flush()
                return choices_map[user_choice]

    # ------------------------------------------------------------------
    # Legacy factory methods — delegates to internal classes.
    # Deprecated; kept for third-party renderers during migration window.
    # ------------------------------------------------------------------

    def render(self, data: Any, **kwargs) -> str:
        text = str(data)
        return text if text.endswith("\n") else f"{text}\n"

    def detail_view(self, data: dict[str, str | int | bool], **kwargs) -> str:
        longest_header = max(map(len, data.keys()))
        table_parts = []
        for header, value in data.items():
            table_parts.append(f" {header:>{longest_header}} : {value}")
        return "\n" + "\n".join(table_parts) + "\n\n"

    @staticmethod
    def envs_list(prefixes: Iterable[PathType | PrefixData], **kwargs) -> str:
        show_size = kwargs.get("show_size", False)
        output = [
            "# conda environments:",
            "#",
            "# * -> active",
            "# + -> frozen",
        ]

        def disp_env(prefix: PrefixData) -> str:
            active = (
                "*"
                if context.active_prefix
                and paths_equal(prefix.prefix_path, context.active_prefix)
                else " "
            )
            frozen = "+" if prefix.is_frozen() else " "
            if show_size:
                size_str = human_bytes(prefix.size())
                return f"{prefix.name:20} {active} {frozen} {size_str:>10} {prefix.prefix_path}"
            else:
                return f"{prefix.name:20} {active} {frozen} {prefix.prefix_path}"

        for env_prefix in prefixes:
            if not isinstance(env_prefix, PrefixData):
                env_prefix = PrefixData(env_prefix)
            output.append(disp_env(env_prefix))

        return "\n" + "\n".join(output) + "\n\n"

    @property
    def animations_disabled(self) -> bool:
        """True when progress bars/spinners should be suppressed."""
        return self._animations_disabled

    def progress_bar(self, description: str, **kwargs) -> ProgressBarBase:
        if self._animations_disabled:
            return _QuietProgressBar(description, **kwargs)
        else:
            return _TQDMProgressBar(description, **kwargs)

    def spinner(self, message: str, fail_message: str = "failed\n") -> SpinnerBase:
        if self._animations_disabled:
            return _QuietSpinner(message, fail_message)
        else:
            return _Spinner(message, fail_message)


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
