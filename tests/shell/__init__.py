# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import os
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from os.path import dirname
from shutil import which
from signal import SIGINT
from typing import TYPE_CHECKING
from uuid import uuid4

from pexpect.popen_spawn import PopenSpawn

from conda import CONDA_PACKAGE_ROOT, CONDA_SOURCE_ROOT
from conda.activate import activator_map
from conda.common.compat import on_win
from conda.common.path import unix_path_to_win, win_path_to_unix
from conda.utils import quote_for_shell

if TYPE_CHECKING:
    from collections.abc import Iterable


# Here, by removing --dev you can try weird situations that you may want to test, upgrade paths
# and the like? What will happen is that the conda being run and the shell scripts it's being run
# against will be essentially random and will vary over the course of activating and deactivating
# environments. You will have absolutely no idea what's going on as you change code or scripts and
# encounter some different code that ends up being run (some of the time). You will go slowly mad.
# No, you are best off keeping --dev on the end of these. For sure, if conda bundled its own tests
# module then we could remove --dev if we detect we are being run in that way.
dev_arg = "--dev"
activate = f" activate {dev_arg} "
deactivate = f" deactivate {dev_arg} "
install = f" install {dev_arg} "


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
    def resolve(cls, value: str | tuple[str, ...] | Shell) -> Shell | None:
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
    def interactive(self, *args, **kwargs) -> InteractiveShell:
        with InteractiveShell(self, *args, **kwargs) as interactive:
            yield interactive


class InteractiveShellType(type):
    EXE_WIN = sys.executable if on_win else unix_path_to_win(sys.executable)
    EXE_UNIX = win_path_to_unix(sys.executable) if on_win else sys.executable
    SHELLS: dict[str, dict] = {
        "posix": {
            "activator": "posix",
            "init_command": f'eval "$({EXE_UNIX} -m conda shell.posix hook {dev_arg})"',
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
        # It should be noted here that we use the latest hook with whatever conda.exe is installed
        # in sys.prefix (and we will activate all of those PATH entries).  We will set PYTHONPATH
        # though, so there is that.  What I'm getting at is that this is a huge mixup and a mess.
        "cmd.exe": {
            "activator": "cmd.exe",
            # For non-dev-mode you'd have:
            #            'init_command': 'set "CONDA_SHLVL=" '
            #                            '&& @CALL {}\\shell\\condabin\\conda_hook.bat {} '
            #                            '&& set CONDA_EXE={}'
            #                            '&& set _CE_M='
            #                            '&& set _CE_CONDA='
            #                            .format(CONDA_PACKAGE_ROOT, dev_arg,
            #                                    join(sys.prefix, "Scripts", "conda.exe")),
            "init_command": (
                '@SET "CONDA_SHLVL=" '
                f"&& @CALL {CONDA_PACKAGE_ROOT}\\shell\\condabin\\conda_hook.bat {dev_arg} "
                f'&& @SET "CONDA_EXE={sys.executable}" '
                '&& @SET "_CE_M=-m" '
                '&& @SET "_CE_CONDA=conda"'
            ),
            "print_env_var": "@ECHO %%%s%%",
        },
        "csh": {
            "activator": "csh",
            # "args": ("-v", "-x"),  # for debugging
            # unset conda alias before calling conda shell hook
            "init_command": f'unalias conda;\neval "`{EXE_UNIX} -m conda shell.csh hook {dev_arg}`"',
            "print_env_var": 'echo "$%s"',
        },
        "tcsh": {"base_shell": "csh"},
        "fish": {
            "activator": "fish",
            "init_command": f"eval ({EXE_UNIX} -m conda shell.fish hook {dev_arg})",
            "print_env_var": "echo $%s",
        },
        # We don't know if the PowerShell executable is called
        # powershell, pwsh, or pwsh-preview.
        "powershell": {
            "activator": "powershell",
            "args": ("-NoProfile", "-NoLogo"),
            "init_command": f"{EXE_WIN} -m conda shell.powershell hook --dev | Out-String | Invoke-Expression",
            "print_env_var": "$Env:%s",
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
        self.exit_cmd = exit_cmd
        self.env = env or {}

    def __enter__(self):
        self.p = PopenSpawn(
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

    def sendline(self, *args, **kwargs):
        return self.p.sendline(*args, **kwargs)

    def expect(self, *args, **kwargs):
        try:
            return self.p.expect(*args, **kwargs)
        except Exception:
            print(f"{self.p.before=}", file=sys.stderr)
            print(f"{self.p.after=}", file=sys.stderr)
            raise

    def expect_exact(self, *args, **kwargs):
        try:
            return self.p.expect_exact(*args, **kwargs)
        except Exception:
            print(f"{self.p.before=}", file=sys.stderr)
            print(f"{self.p.after=}", file=sys.stderr)
            raise

    def assert_env_var(self, env_var, value, use_exact=False):
        # value is actually a regex
        self.sendline(self.print_env_var % env_var)
        if use_exact:
            self.expect_exact(value)
            self.clear()
        else:
            self.expect(rf"{value}\r?\n")

    def get_env_var(self, env_var, default=None):
        self.sendline(self.print_env_var % env_var)
        if self.shell_name == "cmd.exe":
            self.expect(rf"@ECHO %{env_var}%\r?\n([^\r\n]*)\r?\n")
        elif self.shell_name in ("powershell", "pwsh"):
            self.expect(rf"\$Env:{env_var}\r?\n([^\r\n]*)\r?\n")
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

    def path_conversion(self, *args, **kwargs):
        return self.activator.path_conversion(*args, **kwargs)
