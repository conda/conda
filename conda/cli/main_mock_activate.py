# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Subshell implementation for `conda activate` and `deactivate`.

Instead of modifying the current shell, new subshells are spawned.
"""

from __future__ import annotations

import os
import shlex
import shutil
import signal
import struct
import subprocess
import sys
from logging import getLogger
from pathlib import Path
from tempfile import NamedTemporaryFile
from textwrap import dedent
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from argparse import ArgumentParser, Namespace, _SubParsersAction
    from collections.abc import Iterable

if sys.platform != "win32":
    import fcntl
    import termios

    import pexpect

import shellingham

from .. import activate
from ..base.constants import COMPATIBLE_SHELLS
from ..common.io import dashlist
from ..exceptions import CondaError

log = getLogger(f"conda.{__name__}")


class Shell:
    Activator: activate._Activator
    hook_help_msg: str = "N/A"

    def __init__(self, prefix: Path, stack: bool = False):
        self.prefix = prefix
        self._prefix_str = str(prefix)
        self._stack = stack
        self._activator_args = ["activate"]
        if self._stack:
            self._activator_args.append("--stack")
        self._activator_args.append(str(prefix))
        self._activator = self.Activator(self._activator_args)
        self._files_to_remove = []

    def spawn(self) -> int:
        """
        Creates a new shell session with the conda environment at `path`
        already activated and waits for the shell session to finish.

        Returns the exit code of such process.
        """
        if not sys.stdin.isatty():
            raise CondaError(
                "Running `conda activate` from a non-interactive shell! "
                f"Initialize the session with: `{self.hook_help_msg}`."
            )
        return self._spawn()

    def _spawn(self) -> int:
        raise NotImplementedError

    def script(self) -> str:
        raise NotImplementedError

    def prompt(self) -> str:
        raise NotImplementedError

    def prompt_modifier(self) -> str:
        conda_default_env = self._activator._default_env(self._prefix_str)
        return self._activator._prompt_modifier(self._prefix_str, conda_default_env)

    def executable(self) -> str:
        raise NotImplementedError

    def args(self) -> tuple[str, ...]:
        raise NotImplementedError

    def env(self) -> dict[str, str]:
        env = os.environ.copy()
        env["_CONDA_SUBSHELL"] = "1"
        return env

    def __del__(self):
        for path in self._files_to_remove:
            try:
                os.unlink(path)
            except OSError as exc:
                log.debug("Could not delete %s", path, exc_info=exc)


class PosixShell(Shell):
    Activator = activate.PosixActivator
    default_shell = "/bin/sh"
    default_args = ("-l", "-i")
    hook_help_msg = "eval $(conda shell.posix hook)"

    def _spawn(self, command: Iterable[str] | None = None) -> int:
        return self.spawn_tty(command).wait()

    def script(self) -> str:
        script = self._activator.execute()
        lines = []
        for line in script.splitlines(keepends=True):
            if "PS1=" in line:
                continue
            lines.append(line)
        return "".join(lines)

    def prompt(self) -> str:
        return f'PS1="{self.prompt_modifier()}${{PS1:-}}"'

    def executable(self):
        return os.environ.get("SHELL", self.default_shell)

    def args(self):
        return self.default_args

    def spawn_tty(self, command: Iterable[str] | None = None) -> pexpect.spawn:
        def _sigwinch_passthrough(sig, data):
            # NOTE: Taken verbatim from pexpect's .interact() docstring.
            # Check for buggy platforms (see pexpect.setwinsize()).
            if "TIOCGWINSZ" in dir(termios):
                TIOCGWINSZ = termios.TIOCGWINSZ
            else:
                TIOCGWINSZ = 1074295912  # assume
            s = struct.pack("HHHH", 0, 0, 0, 0)
            a = struct.unpack("HHHH", fcntl.ioctl(sys.stdout.fileno(), TIOCGWINSZ, s))
            child.setwinsize(a[0], a[1])

        size = shutil.get_terminal_size()
        executable = self.executable()

        child = pexpect.spawn(
            self.executable(),
            [*self.args()],
            env=self.env(),
            echo=False,
            dimensions=(size.lines, size.columns),
        )
        try:
            with NamedTemporaryFile(
                prefix="conda-spawn-",
                suffix=self.Activator.script_extension,
                delete=False,
                mode="w",
            ) as f:
                f.write(self.script())
            signal.signal(signal.SIGWINCH, _sigwinch_passthrough)
            # Source the activation script. We do this in a single line for performance.
            # (It's slower to send several lines than paying the IO overhead).
            # We set the PS1 prompt outside the script because it's otherwise invisible.
            # stty echo is equivalent to `child.setecho(True)` but the latter didn't work
            # reliably across all shells and OSs.
            child.sendline(f' . "{f.name}" && {self.prompt()} && stty echo')
            os.read(child.child_fd, 4096)  # consume buffer before interact
            if Path(executable).name == "zsh":
                # zsh also needs this for a truly silent activation
                child.expect("\r\n")
            if command:
                child.sendline(shlex.join(command))
            if sys.stdin.isatty():
                child.interact()
            return child
        finally:
            self._files_to_remove.append(f.name)


class BashShell(PosixShell):
    def executable(self):
        return "bash"


class ZshShell(PosixShell):
    def executable(self):
        return "zsh"


class CshShell(Shell):
    hook_help_msg = "eval $(conda shell.csh hook)"


class XonshShell(Shell):
    hook_help_msg = "eval $(conda shell.xonsh hook)"


class FishShell(Shell):
    hook_help_msg = "eval $(conda shell.fish hook)"


class PowershellShell(Shell):
    Activator = activate.PowerShellActivator
    hook_help_msg = ". $(conda shell.powershell hook)"  # TODO: CHECK

    def spawn_popen(
        self, command: Iterable[str] | None = None, **kwargs
    ) -> subprocess.Popen:
        try:
            with NamedTemporaryFile(
                prefix="conda-spawn-",
                suffix=self.Activator.script_extension,
                delete=False,
                mode="w",
            ) as f:
                f.write(f"{self.script()}\r\n")
                f.write(f"{self.prompt()}\r\n")
                if command:
                    command = subprocess.list2cmdline(command)
                    f.write(f"echo {command}\r\n")
                    f.write(f"{command}\r\n")
            return subprocess.Popen(
                [self.executable(), *self.args(), f.name], env=self.env(), **kwargs
            )
        finally:
            self._files_to_remove.append(f.name)

    def _spawn(self, command: Iterable[str] | None = None) -> int:
        proc = self.spawn_popen(command)
        proc.communicate()
        return proc.wait()

    def script(self) -> str:
        return self._activator.execute()

    def prompt(self) -> str:
        return (
            "\r\n$old_prompt = $function:prompt\r\n"
            f'function prompt {{"{self.prompt_modifier()}$($old_prompt.Invoke())"}};'
        )

    def executable(self) -> str:
        return "powershell"

    def args(self) -> tuple[str, ...]:
        return ("-NoLogo", "-NoExit", "-File")

    def env(self) -> dict[str, str]:
        env = os.environ.copy()
        env["_CONDA_SUBSHELL"] = "1"
        return env


class CmdExeShell(PowershellShell):
    Activator = activate.CmdExeActivator
    hook_help_msg = "CALL $(conda shell.cmd.exe hook)"  # TODO: CHECK

    def script(self):
        return "\r\n".join(
            [
                "@ECHO OFF",
                Path(self._activator.execute()).read_text(),
                "@ECHO ON",
            ]
        )

    def prompt(self) -> str:
        return f'@SET "PROMPT={self.prompt_modifier()}$P$G"'

    def executable(self) -> str:
        return "cmd"

    def args(self) -> tuple[str, ...]:
        return ("/D", "/K")


SHELLS: dict[str, type[Shell]] = {
    "ash": PosixShell,
    "bash": BashShell,
    "cmd.exe": CmdExeShell,
    "cmd": CmdExeShell,
    "csh": CshShell,
    "dash": PosixShell,
    "fish": FishShell,
    "posix": PosixShell,
    "powershell": PowershellShell,
    "pwsh": PowershellShell,
    "tcsh": CshShell,
    "xonsh": XonshShell,
    "zsh": ZshShell,
}


def default_shell_class():
    if sys.platform == "win32":
        return CmdExeShell
    return PosixShell


def detect_shell_class():
    try:
        name, _ = shellingham.detect_shell()
    except shellingham.ShellDetectionFailure:
        return default_shell_class()
    else:
        try:
            return SHELLS[name]
        except KeyError:
            log.warning("Did not recognize shell %s, returning default.", name)
            return default_shell_class()


def shell_specifier_to_shell(name: str | None = None) -> type[Shell]:
    if name is None:
        return detect_shell_class()

    try:
        return SHELLS[name]
    except KeyError:
        raise ShellNotSupported(name)


class ShellNotSupported(CondaError):
    def __init__(self, name: str):
        message = (
            f"The specified shell {name} is not supported."
            "Try one of:\n"
            f"{dashlist(COMPATIBLE_SHELLS)}"
        )
        super().__init__(message)


def configure_parser(sub_parsers: _SubParsersAction, **kwargs) -> ArgumentParser:
    p: ArgumentParser = sub_parsers.add_parser(
        "activate",
        help="Activate a conda environment.",
        **kwargs,
    )
    p.set_defaults(func="conda.cli.main_mock_activate.execute")
    p.add_argument(
        "environment",
        nargs="?",
        default=None,
        help="Environment to activate. Can be either a name or a path. Paths are only detected "
        "if they contain a (back)slash. Use the ./env idiom environments in working directory.",
    )
    mutex = p.add_mutually_exclusive_group()
    mutex.add_argument(
        "--replace",
        action="store_true",
        help="Spawning shells within activated shells is disallowed by default. "
        "This flag enables nested spawns by replacing the activated environment.",
    )
    mutex.add_argument(
        "--stack",
        action="store_true",
        help="Spawning shells within activated shells is disallowed by default. "
        "This flag enables nested spawns by stacking the newly activated environment "
        "on top of the current one.",
    )

    return p


def execute(args: Namespace, parser: ArgumentParser) -> int:
    import os

    from conda.base.context import context, locate_prefix_by_name
    from conda.exceptions import CondaError, EnvironmentLocationNotFound

    if args.environment is None:
        prefix = context.default_activation_prefix
    elif "/" in args.environment or "\\" in args.environment:
        prefix = os.path.expanduser(os.path.expandvars(args.environment))
        if not os.path.isfile(os.path.join(args.environment, "conda-meta", "history")):
            raise EnvironmentLocationNotFound(prefix)
    else:
        prefix = locate_prefix_by_name(args.environment)

    if (
        os.getenv("_CONDA_SUBSHELL", "0") not in ("", "0")
        and not args.replace
        and not args.stack
    ):
        if current_env := os.getenv("CONDA_PREFIX"):
            env_info = f" for environment '{current_env}'"
        else:
            env_info = ""
        raise CondaError(
            dedent(
                f"""
                Detected active shell session{env_info}.

                Nested activation is disallowed by default.
                Please exit the current session before starting a new one by running 'exit'.
                Alternatively, check the usage of --replace and/or --stack.
                """
            ).lstrip()
        )
    return shell_specifier_to_shell()(prefix).spawn()
