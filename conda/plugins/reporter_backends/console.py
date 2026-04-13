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

    def detail_view(self, data: dict[str, str | int | bool], **kwargs) -> str:
        table_parts = [""]
        longest_header = max(map(len, data.keys()))

        for header, value in data.items():
            table_parts.append(f" {header:>{longest_header}} : {value}")

        table_parts.append("\n")

        return "\n".join(table_parts)

    @staticmethod
    def envs_list(
        prefixes: Iterable[PathType | PrefixData], output=True, **kwargs
    ) -> str:
        if not output:
            return ""

        show_size = kwargs.get("show_size", False)

        output = [
            "",
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

    def spinner(self, message: str, fail_message: str = "failed\n") -> SpinnerBase:
        """
        Determines whether to return a Spinner or QuietSpinner
        """
        if context.quiet:
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

    def install_like_progress(self, data: dict[str, Any], **kwargs) -> str:
        """Install/solve milestones and package plans (classic + rattler, Rich on console)."""
        from io import StringIO

        from rich.console import Console
        from rich.panel import Panel
        from rich.text import Text

        kind = data.get("kind")
        if kind == "solve_started":
            return ""
        if kind == "solve_finished":
            rc = int(data.get("record_count", 0))
            sec = int(data.get("duration_seconds", 0))
            ms = float(data.get("duration_ms", 0))
            tail = f"{rc} packages in "
            if sec:
                tail += f"{sec}s "
            tail += f"{ms:.0f}ms"
            markup = f"[green]✔[/] solving [dim]{tail}[/]"
            buf = StringIO()
            kwargs: dict[str, Any] = {"file": buf, "soft_wrap": True}
            if not sys.stdin.isatty() or not sys.stdout.isatty():
                kwargs["width"] = 100_000
            Console(force_terminal=True, **kwargs).print(markup, highlight=False)
            return buf.getvalue() + "\n"
        if kind == "solve_failed":
            err_t = data.get("error_type", "Error")
            err_m = str(data.get("error_message", ""))[:300]
            markup = f"[red]✗[/] solve failed [dim]({err_t})[/]: {err_m}"
            buf = StringIO()
            kwargs = {"file": buf, "soft_wrap": True}
            if not sys.stdin.isatty() or not sys.stdout.isatty():
                kwargs["width"] = 100_000
            Console(force_terminal=True, **kwargs).print(markup, highlight=False)
            return buf.getvalue() + "\n"
        if kind == "verbose_hints":
            hints = data.get("hints") or ()
            buf = StringIO()
            kwargs = {"file": buf, "soft_wrap": True}
            if not sys.stdin.isatty() or not sys.stdout.isatty():
                kwargs["width"] = 100_000
            c = Console(force_terminal=True, **kwargs)
            for label, value in hints:
                if value is None or value == "":
                    continue
                c.print(f"[dim]{label}:[/] {value}", highlight=False)
            out = buf.getvalue()
            return out + "\n" if out else ""
        if kind == "install_plan_table":
            from ..._ng.cli.planning import build_install_plan_table

            rows = data.get("rows") or ()
            if not rows:
                return ""
            caption = data.get("caption")
            table = build_install_plan_table(rows, caption=caption)
            buf = StringIO()
            kwargs_ip: dict[str, Any] = {"file": buf, "soft_wrap": True}
            if not sys.stdin.isatty() or not sys.stdout.isatty():
                kwargs_ip["width"] = 100_000
            c = Console(force_terminal=True, **kwargs_ip)
            prefix = data.get("prefix")
            specs_add = data.get("specs_to_add") or ()
            specs_rm = data.get("specs_to_remove") or ()
            if prefix:
                c.print("[bold]## Package Plan ##[/]", highlight=False)
                c.print(f"  [dim]environment location:[/] {prefix}", highlight=False)
                c.print("", highlight=False)
            if specs_rm:
                c.print("  [dim]removed specs:[/]", highlight=False)
                for s in specs_rm:
                    c.print(f"    - {s}", highlight=False)
                c.print("", highlight=False)
            if specs_add:
                c.print("  [dim]added / updated specs:[/]", highlight=False)
                for s in specs_add:
                    c.print(f"    - {s}", highlight=False)
                c.print("", highlight=False)
            c.print(
                Panel(table, title="Package Plan", expand=False, padding=(0, 1)),
                highlight=False,
            )
            return buf.getvalue() + "\n"
        if kind in (
            "transaction_prepare",
            "transaction_verify",
            "transaction_execute",
            "transaction_rollback",
        ):
            if sys.stdout.isatty():
                return ""
            labels = {
                "transaction_prepare": "preparing transaction",
                "transaction_verify": "verifying transaction",
                "transaction_execute": "executing transaction",
                "transaction_rollback": "rolling back transaction",
            }
            buf = StringIO()
            kwargs_tx: dict[str, Any] = {"file": buf, "soft_wrap": True}
            kwargs_tx["width"] = 100_000
            Console(force_terminal=True, **kwargs_tx).print(
                f"[dim][conda][/] {labels[kind]}", highlight=False
            )
            return buf.getvalue() + "\n"
        if kind == "solution_plan_text":
            text = data.get("text") or ""
            return text + ("\n" if text and not text.endswith("\n") else "")
        if kind == "legacy_plan_text":
            body = (data.get("text") or "").rstrip("\n")
            if not body:
                return ""
            panel = Panel(
                Text(body),
                title="Package Plan",
                expand=False,
                padding=(0, 1),
            )
            buf = StringIO()
            kwargs = {"file": buf, "soft_wrap": True}
            if not sys.stdin.isatty() or not sys.stdout.isatty():
                kwargs["width"] = 100_000
            Console(force_terminal=True, **kwargs).print(panel)
            return buf.getvalue() + "\n"
        if kind == "awaiting_confirmation":
            return ""
        if kind == "transaction_started":
            buf = StringIO()
            kwargs: dict[str, Any] = {"file": buf, "soft_wrap": True}
            if not sys.stdin.isatty() or not sys.stdout.isatty():
                kwargs["width"] = 100_000
            Console(force_terminal=True, **kwargs).print(
                "[dim][conda][/] applying transaction", highlight=False
            )
            return buf.getvalue() + "\n"
        if kind == "transaction_finished":
            buf = StringIO()
            kwargs = {"file": buf, "soft_wrap": True}
            if not sys.stdin.isatty() or not sys.stdout.isatty():
                kwargs["width"] = 100_000
            Console(force_terminal=True, **kwargs).print(
                "[dim][conda][/] transaction finished", highlight=False
            )
            return buf.getvalue() + "\n\n"
        return ""

    def ng_install_progress(self, data: dict[str, Any], **kwargs) -> str:
        """Deprecated: use :meth:`install_like_progress`."""
        return self.install_like_progress(data, **kwargs)

    def post_create_activate(self, data: dict[str, Any], **kwargs) -> str:
        """Rich panel with activation instructions (same content as former conda-ng only)."""
        from rich.console import Console
        from rich.panel import Panel

        from ...auxlib.ish import dals

        env_name_or_prefix = data.get("env", "")
        if " " in str(env_name_or_prefix):
            env_name_or_prefix = f'"{env_name_or_prefix}"'
        message = dals(
            f"""
            To activate this environment, use:

                $ conda activate {env_name_or_prefix}

            To deactivate an active environment, use:

                $ conda deactivate"""
        )
        panel = Panel(message, title="Activation instructions", expand=False, padding=1)
        width_kw: dict[str, Any] = {"record": True, "soft_wrap": True}
        if not sys.stdin.isatty() or not sys.stdout.isatty():
            width_kw["width"] = 100_000
        console = Console(**width_kw)
        with console.capture() as capture:
            console.print(panel)
        return capture.get() + "\n"


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
