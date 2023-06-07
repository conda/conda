# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import argparse
import re
import sys
from os.path import join

from conda import CONDA_PACKAGE_ROOT
from conda.activate import _Activator, native_path_to_unix
from conda.base.context import context
from conda.cli.main import init_loggers
from conda.common.compat import on_win
from conda.exceptions import conda_exception_handler
from conda.plugins import CondaShellPlugins, CondaSubcommand, hookimpl


class PosixPluginActivator(_Activator):
    """
    Define syntax that is specific to Posix shells.
    Also contains logic that takes into account Posix shell use on Windows.

    This child class is inentionally a near-replica of the current PosixActivator class:
    the only difference is the included _parse_and_set_args method.
    """

    pathsep_join = ":".join
    sep = "/"
    path_conversion = staticmethod(native_path_to_unix)
    script_extension = ".sh"
    tempfile_extension = None  # output to stdout
    command_join = "\n"

    unset_var_tmpl = "unset %s"
    export_var_tmpl = "export %s='%s'"
    set_var_tmpl = "%s='%s'"
    run_script_tmpl = '. "%s"'

    hook_source_path = join(
        CONDA_PACKAGE_ROOT,
        "shell",
        "etc",
        "profile.d",
        "conda.sh",
    )

    def _update_prompt(self, set_vars, conda_prompt_modifier):
        ps1 = self.environ.get("PS1", "")
        if "POWERLINE_COMMAND" in ps1:
            # Defer to powerline (https://github.com/powerline/powerline) if it's in use.
            return
        current_prompt_modifier = self.environ.get("CONDA_PROMPT_MODIFIER")
        if current_prompt_modifier:
            ps1 = re.sub(re.escape(current_prompt_modifier), r"", ps1)
        # Because we're using single-quotes to set shell variables, we need to handle the
        # proper escaping of single quotes that are already part of the string.
        # Best solution appears to be https://stackoverflow.com/a/1250279
        ps1 = ps1.replace("'", "'\"'\"'")
        set_vars.update(
            {
                "PS1": conda_prompt_modifier + ps1,
            }
        )

    def _hook_preamble(self) -> str:
        result = []
        for key, value in context.conda_exe_vars_dict.items():
            if value is None:
                # Using `unset_var_tmpl` would cause issues for people running
                # with shell flag -u set (error on unset).
                result.append(self.export_var_tmpl % (key, ""))
            elif on_win and ("/" in value or "\\" in value):
                result.append(f'''export {key}="$(cygpath '{value}')"''')
            else:
                result.append(self.export_var_tmpl % (key, value))
        return "\n".join(result) + "\n"

    # this will be in _Activate parent class logic once architecture is decided
    def _parse_and_set_args(self, args: argparse.Namespace) -> None:
        """
        Set self.command to the specified command (activate, deactivate, reactivate).
        Set context.dev if a --dev flag exists.
        For activate, set self.env_name_or_prefix and self.stack.
        """
        self.command = args.command
        context.dev = args.dev or context.dev

        if self.command == "activate":
            self.env_name_or_prefix = args.env or "base"

            if args.stack is None:
                self.stack = context.auto_stack and context.shlvl <= context.auto_stack
            else:
                self.stack = args.stack

        return


def get_parsed_args(argv: list[str]) -> argparse.Namespace:
    """
    Parse CLI arguments to determine desired command.
    Create namespace with 'command' and 'env' keys.
    """
    parser = argparse.ArgumentParser(
        "posix_plugin_current_logic",
        description="Process conda activate, deactivate, and reactivate",
    )

    commands = parser.add_subparsers(
        required=True,
        dest="command",
    )

    activate = commands.add_parser(
        "activate",
        help="Activate a conda environment",
    )
    activate.add_argument(
        "env",
        metavar="env_name_or_prefix",
        default=None,
        type=str,
        nargs="?",
        help="""
            The environment name or prefix to activate. If the prefix is a relative path,
            it must start with './' (or '.\' on Windows). If no environment is specified,
            the base environment will be activated.
            """,
    )
    stack = activate.add_mutually_exclusive_group()
    stack.add_argument(
        "--stack",
        action="store_true",
        help="""
        Stack the environment being activated on top of the
        previous active environment, rather replacing the
        current active environment with a new one. Currently,
        only the PATH environment variable is stacked. This
        may be enabled implicitly by the 'auto_stack'
        configuration variable.
        """,
    )
    stack.add_argument(
        "--no-stack",
        dest="stack",
        action="store_false",
        help="Do not stack the environment. Overrides 'auto_stack' setting.",
    )
    activate.add_argument(
        "--dev", action="store_true", default=False, help=argparse.SUPPRESS
    )

    deactivate = commands.add_parser(
        "deactivate", help="Deactivate the current active conda environment"
    )
    deactivate.add_argument(
        "--dev", action="store_true", default=False, help=argparse.SUPPRESS
    )

    reactivate = commands.add_parser(
        "reactivate",
        help="Reactivate the current conda environment, updating environment variables",
    )
    reactivate.add_argument(
        "--dev", action="store_true", default=False, help=argparse.SUPPRESS
    )

    try:
        args = parser.parse_args(argv)
    except SystemExit:
        # SystemExit: help blurb was printed, intercepting SystemExit(0) to avoid
        # evaluation of help strings by shell interface
        raise SystemExit(1)

    return args


def handle_env(*args, **kwargs):
    """
    Execute logic associated with parsed CLI command (activate, deactivate, reactivate).
    Print relevant shell commands to stdout, for evaluation by shell forwarding function on return.
    See modified forwarding function at conda/shell/etc/profile.d/conda.sh
    In a final version, this method would either require automatic evaluation logic to be
    run via the user's shell profile or the user would have to manually run the evaluation logic.

    This plugin is intended for use only with POSIX shells.
    """
    args = get_parsed_args(sys.argv[2:])  # drop executable/script and plugin name

    context.__init__()
    init_loggers(context)

    activator = PosixPluginActivator(args)
    print(activator.execute(), end="")

    return 0


def handle_exceptions(*args, **kwargs):
    """
    Upon return, exit the Python interpreter and return the appropriate
    error code if an exception occurs.
    These are handled through main.py and __main__.py during the current
    activate/reactivate/deactivate process.
    """
    return sys.exit(conda_exception_handler(handle_env, *args, **kwargs))


@hookimpl
def conda_subcommands():
    yield CondaSubcommand(
        name="posix_plugin_current_logic",
        summary="Plugin for POSIX shells: handles conda activate, deactivate, and reactivate",
        action=handle_exceptions,
    )


@hookimpl
def conda_shell_plugins():
    yield CondaShellPlugins(
        name="posix_plugin_current_logic",
        summary="Plugin for POSIX shells: handles conda activate, deactivate, and reactivate",
        activator=PosixPluginActivator,
    )
