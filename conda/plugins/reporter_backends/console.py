# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
Defines a "console" reporter backend.

This reporter backend provides the default output for conda.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from errno import EPIPE, ESHUTDOWN
from itertools import cycle
from threading import Event, Thread
from time import sleep
from typing import TYPE_CHECKING

from ...base.constants import (
    DEFAULT_CONSOLE_REPORTER_BACKEND,
)
from ...base.context import context
from ...common.datetime import format_relative_time
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


class Spinner(SpinnerBase):
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


class QuietSpinner(SpinnerBase):
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


class ConsoleReporterRenderer(ReporterRendererBase):
    """
    Default implementation for console reporting in conda
    """

    def render(self, data: Any, **kwargs) -> str:
        text = super().render(data, **kwargs)
        # trailing newline
        return text if text.endswith("\n") else f"{text}\n"

    def detail_view(self, data: dict[str, str | int | bool], **kwargs) -> str:
        table_parts = []
        longest_header = max(map(len, data.keys()))

        for header, value in data.items():
            table_parts.append(f" {header:>{longest_header}} : {value}")

        # leading and trailing newlines
        return "\n" + "\n".join(table_parts) + "\n\n"

    @staticmethod
    def envs_list(prefixes: Iterable[PathType | PrefixData], **kwargs) -> str:
        show_size = kwargs.get("show_size", False)

        home = os.path.expanduser("~")
        home_n = os.path.normcase(home)

        def display_path(path: PathType) -> str:
            """Shorten path if the home path is a part of the path"""
            path = str(path)
            path_n = os.path.normcase(path)
            if path_n == home_n:
                return "~"
            if path_n.startswith(home_n + os.sep):
                return "~" + path[len(home) :]
            return path

        def marker(prefix: PrefixData) -> str:
            """Return a marker indicating the environment status."""
            return "*" if prefix.is_active else "+" if prefix.is_frozen() else " "

        rows = []
        for env_prefix in prefixes:
            if not isinstance(env_prefix, PrefixData):
                env_prefix = PrefixData(env_prefix)

            rel = lambda dt: format_relative_time(dt) if dt else "-"
            row = [
                marker(env_prefix),
                env_prefix.name,
                rel(env_prefix.last_activated),
                rel(env_prefix.created),
            ]
            if show_size:
                row.append(human_bytes(env_prefix.size()))
            row.append(display_path(env_prefix.prefix_path))
            rows.append(row)

        headers = ["", "Name", "Last Active", "Created"]
        right_aligned = set()
        if show_size:
            size_column = len(headers)
            headers.append("Size")
            right_aligned.add(size_column)
        headers.append("Path")

        widths = [
            max(len(headers[i]), *(len(row[i]) for row in rows))
            for i in range(len(headers))
        ]

        def format_row(row_data: list[str], right_aligned=frozenset()) -> str:
            """Format table rowe with assumption path is the last column and unpadded."""
            formatted_cells = [cell.rjust(widths[i]) if i in right_aligned
                               else cell.ljust(widths[i])
                               for i, cell in enumerate(row_data[:-1])]
            formatted_cells.append(row_data[-1])

            return "   ".join(formatted_cells)

        header_line = format_row(headers)
        formatted_rows = [format_row(row, right_aligned) for row in rows]
        long_line = "-" * (len(header_line) + 10)

        output = [
            header_line,
            long_line,
            *formatted_rows,
            "",
            "* = Active, + = Frozen",
        ]

        # leading and trailing newlines
        return "\n" + "\n".join(output) + "\n\n"

    @property
    def animations_disabled(self) -> bool:
        """True when progress bars/spinners should be suppressed."""
        return context.quiet or not is_tty() or term_dumb()

    def progress_bar(
        self,
        description: str,
        **kwargs,
    ) -> ProgressBarBase:
        """
        Determines whether to return a TQDMProgressBar or QuietProgressBar.

        Animations are suppressed when:
        * ``context.quiet`` is set,
        * the output is not a TTY (e.g. piped to a file), or
        * ``TERM=dumb`` or ``TERM=unknown`` is set.
        """
        if self.animations_disabled:
            return QuietProgressBar(description, **kwargs)
        else:
            return TQDMProgressBar(description, **kwargs)

    def spinner(self, message: str, fail_message: str = "failed\n") -> SpinnerBase:
        """
        Determines whether to return a Spinner or QuietSpinner.

        Animations are suppressed under the same conditions as
        :meth:`progress_bar`.
        """
        if self.animations_disabled:
            return QuietSpinner(message, fail_message)
        else:
            return Spinner(message, fail_message)

    def prompt(self, message="Proceed", choices=("yes", "no"), default="yes") -> str:
        """
        Implementation of a prompt dialog
        """
        if default not in choices:
            raise ValueError(f"Default value '{default}' must be part of `choices`")
        options = []

        for option in choices:
            if option == default:
                options.append(f"[{option[0]}]")
            else:
                options.append(option[0])

        message = "{} ({})? ".format(message, "/".join(options))
        choices = {alt: choice for choice in choices for alt in [choice, choice[0]]}
        choices[""] = default
        while True:
            # raw_input has a bug and prints to stderr, not desirable
            sys.stdout.write(message)
            sys.stdout.flush()
            try:
                user_choice = sys.stdin.readline().strip().lower()
            except OSError as e:
                raise CondaError(f"cannot read from stdin: {e}")
            if user_choice not in choices:
                print(f"Invalid choice: {user_choice}")
            else:
                sys.stdout.write("\n")
                sys.stdout.flush()
                return choices[user_choice]


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
