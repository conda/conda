# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import os
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from os.path import dirname, join
from shutil import which
from signal import SIGINT
from typing import TYPE_CHECKING, overload
from uuid import uuid4

import pexpect
from pexpect.popen_spawn import PopenSpawn

from conda import CONDA_PACKAGE_ROOT, CONDA_SOURCE_ROOT
from conda.activate import activator_map
from conda.common.compat import on_win
from conda.common.path import BIN_DIRECTORY, unix_path_to_win, win_path_to_unix
from conda.utils import quote_for_shell

if TYPE_CHECKING:
    import re
    from collections.abc import Iterable, Iterator
    from typing import Annotated, Any, Literal, Self, TypeVar

    Regex = Annotated[str, lambda x: re.compile(x)]
    T = TypeVar("T")


activate = " activate "
deactivate = " deactivate "
install = " install "


@dataclass
class Shell:
    name: str | tuple[str, ...]  # shell name
    path: str | None = None  # $PATH style path to search for shell
    exe: str | None = None  # shell executable path

    def __post_init__(self) -> None:
        if isinstance(self.name, str):
            pass
        elif isinstance(self.name, tuple) and all(
            isinstance(name, str) for name in self.name
        ):
            pass
        else:
            raise TypeError(
                f"shell name must be str or tuple of str, not {self.name!r}"
            )

    @classmethod
    def resolve(cls, value: str | tuple[str, ...] | Shell) -> Shell:
        shell = value if isinstance(value, Shell) else cls(value)

        # if shell.exe is already set, use it
        if shell.exe:
            return shell

        # find shell executable
        names = [shell.name] if isinstance(shell.name, str) else list(shell.name)
        for name in names:
            if exe := which(name, path=shell.path):
                return Shell(name=name, exe=exe)
        raise FileNotFoundError(f"{shell} not found")

    @contextmanager
    def interactive(self, *args, **kwargs) -> Iterator[InteractiveShell]:
        with InteractiveShell(self, *args, **kwargs) as sh:
            yield sh


class InteractiveShellType(type):
    EXE_WIN = sys.executable if on_win else unix_path_to_win(sys.executable)
    EXE_UNIX = win_path_to_unix(sys.executable) if on_win else sys.executable
    SHELLS: dict[str, dict] = {
        "posix": {
            "activator": "posix",
            "init_command": f'eval "$({EXE_UNIX} -m conda shell.posix hook)"',
            "print_env_var": 'echo "$%s"',
        },
        "bash": {
            # MSYS2's login scripts handle mounting the filesystem. Without it, /c is /cygdrive.
            "args": ("-l",) if on_win else (),
            "base_shell": "posix",  # inheritance implemented in __init__
        },
        "ash": {"base_shell": "posix"},
        "dash": {"base_shell": "posix"},
        "zsh": {"base_shell": "posix"},
        # Hook from the checkout; CONDA_EXE is the conda launcher in sys.prefix.
        # PYTHONPATH (set in InteractiveShell) makes that launcher import the checkout,
        # matching dev/start.bat.
        "cmd.exe": {
            "activator": "cmd.exe",
            "init_command": (
                '@SET "CONDA_SHLVL=" '
                f"&& @CALL {CONDA_PACKAGE_ROOT}\\shell\\condabin\\conda_hook.bat "
                f'&& @SET "CONDA_EXE={join(sys.prefix, BIN_DIRECTORY, "conda.exe")}" '
                '&& @SET "_CE_M=" '
                '&& @SET "_CE_CONDA="'
            ),
            "print_env_var": '@ECHO "%%%s%%"',
            "assert_env_var": r'"%s"\r?\n',
            "get_env_var": r'@ECHO "%%%s%%"\r?\n"([^\r\n]*)"\r?\n',
        },
        "csh": {
            "activator": "csh",
            # "args": ("-v", "-x"),  # for debugging
            # unset conda alias before calling conda shell hook
            "init_command": f'unalias conda;\neval "`{EXE_UNIX} -m conda shell.csh hook`"',
            "print_env_var": 'echo "$%s"',
        },
        "tcsh": {"base_shell": "csh"},
        "fish": {
            "activator": "fish",
            "init_command": f"eval ({EXE_UNIX} -m conda shell.fish hook)",
            "print_env_var": "echo $%s",
        },
        # We don't know if the PowerShell executable is called
        # powershell, pwsh, or pwsh-preview.
        "powershell": {
            "activator": "powershell",
            "args": ("-NoProfile", "-NoLogo"),
            "init_command": f"{EXE_WIN} -m conda shell.powershell hook | Out-String | Invoke-Expression",
            "print_env_var": "$Env:%s",
            "get_env_var": r"\$Env:%s\r?\n([^\r\n]*)\r?\n",
            "exit_cmd": "exit",
        },
        "pwsh": {"base_shell": "powershell"},
        "pwsh-preview": {"base_shell": "powershell"},
        "xonsh": {
            "activator": "xonsh",
            "args": (
                "--interactive",
                # Workaround for some issues with prompt_toolkit
                # https://github.com/conda/conda/issues/15611
                "--shell-type=readline",
            ),
            "init_command": f'__xonsh__.execer.exec($("{EXE_UNIX}" -m conda shell.xonsh hook))',
            "print_env_var": "print($%s)",
        },
    }

    def __call__(self, shell: str | tuple[str, ...] | Shell, **kwargs):
        shell = Shell.resolve(shell)
        return super().__call__(
            shell,
            **{
                **self.SHELLS.get(self.SHELLS[shell.name].get("base_shell"), {}),
                **self.SHELLS[shell.name],
                **kwargs,
            },
        )


class InteractiveShell(metaclass=InteractiveShellType):
    def __init__(
        self,
        shell: str | tuple[str, ...] | Shell,
        *,
        activator: str,
        args: Iterable[str] = (),
        init_command: str,
        print_env_var: str,
        assert_env_var: str | None = None,
        get_env_var: str | None = None,
        exit_cmd: str | None = None,
        base_shell: str | None = None,  # ignored
        env: dict[str, str] | None = None,
    ):
        shell = Shell.resolve(shell)
        self.shell_name = shell.name
        self.shell_exe = quote_for_shell(shell.exe, *args)
        self.shell_dir = dirname(shell.exe)

        self.activator = activator_map[activator]()
        self.args = args
        self.init_command = init_command
        self.print_env_var = print_env_var
        self._assert_env_var = assert_env_var
        self._get_env_var = get_env_var
        self.exit_cmd = exit_cmd
        self.env = env or {}

    def __enter__(self) -> Self:
        # Fish shell needs a PTY to work properly with pexpect
        # Use pexpect.spawn (PTY) for Fish instead of PopenSpawn (pipes)
        use_pty = self.shell_name == "fish"
        spawn_class = pexpect.spawn if use_pty else PopenSpawn

        self.p = spawn_class(
            self.shell_exe,
            timeout=30,
            maxread=5000,
            searchwindowsize=None,
            logfile=sys.stdout,
            cwd=os.getcwd(),
            env={
                **os.environ,
                "CONDA_AUTO_ACTIVATE": "false",
                "CONDA_AUTO_STACK": "0",
                "CONDA_CHANGEPS1": "true",
                # "CONDA_ENV_PROMPT": "({default_env}) ",
                "PYTHONPATH": self.path_conversion(CONDA_SOURCE_ROOT),
                "PATH": self.activator.pathsep_join(
                    self.path_conversion(
                        (
                            *self.activator._get_starting_path_list(),
                            self.shell_dir,
                        )
                    )
                ),
                # ensure PATH is shared with any msys2 bash shell, rather than starting fresh
                "MSYS2_PATH_TYPE": "inherit",
                "CHERE_INVOKING": "1",
                **self.env,
            },
            encoding="utf-8",
            codec_errors="strict",
        )

        if self.init_command:
            self.p.sendline(self.init_command)

        # want CONDA_SHLVL=0 before running tests so deactivate any active environments
        # since we do not know how many environments have been activated by the user/CI
        # just to be safe deactivate a few times
        for _ in range(5):
            self.p.sendline("conda deactivate")

        self.clear()

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            print(f"Exception encountered: ({exc_type}) {exc_val}", file=sys.stderr)

        if self.p:
            if self.exit_cmd:
                self.sendline(self.exit_cmd)

            self.p.kill(SIGINT)

    def sendline(self, *args, **kwargs) -> int:
        return self.p.sendline(*args, **kwargs)

    def expect(self, *args, **kwargs) -> int:
        try:
            return self.p.expect(*args, **kwargs)
        except Exception:
            print(f"{self.p.before=}", file=sys.stderr)
            print(f"{self.p.after=}", file=sys.stderr)
            raise

    def expect_exact(self, *args, **kwargs) -> int:
        try:
            return self.p.expect_exact(*args, **kwargs)
        except Exception:
            print(f"{self.p.before=}", file=sys.stderr)
            print(f"{self.p.after=}", file=sys.stderr)
            raise

    @overload
    def assert_env_var(
        self, env_var: str, value: Regex, use_exact: Literal[False] = False
    ) -> None: ...

    @overload
    def assert_env_var(
        self, env_var: str, value: str, use_exact: Literal[True]
    ) -> None: ...

    def assert_env_var(self, env_var: str, value: str, use_exact: bool = False) -> None:
        # value is actually a regex
        self.sendline(self.print_env_var % env_var)
        if use_exact:
            self.expect_exact(value)
            self.clear()
        elif self._assert_env_var:
            self.expect(self._assert_env_var % value)
        else:
            self.expect(rf"{value}\r?\n")

    @overload
    def get_env_var(self, env_var: str, default: None = None) -> Any | None: ...

    @overload
    def get_env_var(self, env_var: str, default: T) -> Any | T: ...

    def get_env_var(self, env_var, default=None):
        self.sendline(self.print_env_var % env_var)
        if self._get_env_var:
            self.expect(self._get_env_var % env_var)
        else:
            marker = f"get_env_var-{uuid4().hex}"
            self.sendline(f"echo {marker}")
            self.expect(rf"([^\r\n]*)\r?\n{marker}\r?\n")

        value = self.p.match.group(1)
        return default if value is None else value

    def clear(self) -> None:
        marker = f"clear-{uuid4().hex}"
        self.sendline(f"echo {marker}")
        self.expect(rf"{marker}\r?\n")

    def path_conversion(self, *args, **kwargs) -> str | tuple[str, ...] | None:
        return self.activator.path_conversion(*args, **kwargs)
