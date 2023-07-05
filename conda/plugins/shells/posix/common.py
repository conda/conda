# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import argparse
import re
from os.path import join

from conda import CONDA_PACKAGE_ROOT
from conda.activate import _Activator
from conda.base.context import context
from conda.common.compat import on_win
from conda.plugins.types import CondaShellPlugins


class PosixPluginActivator(_Activator):
    """
    Define syntax that is specific to Posix shells.
    Also contains logic that takes into account Posix shell use on Windows.

    This child class is inentionally a near-replica of the current PosixActivator class:
    the only difference is the included _parse_and_set_args method.
    """

    def __init__(self, syntax, arguments=None):
        """Set syntax attributes yielded from the plugin hook."""
        for field in CondaShellPlugins._fields:
            setattr(self, field, getattr(syntax, field, None))

        self.hook_source_path = join(
            CONDA_PACKAGE_ROOT,
            "shell",
            "etc",
            "profile.d",
            "conda.sh",
        )
        super().__init__(arguments)

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
        self.command = args.command  # only necessary for posix_activate.py
        context.dev = args.dev or context.dev

        if self.command == "activate":
            self.env_name_or_prefix = args.env or "base"

            if args.stack is None:
                self.stack = context.auto_stack and context.shlvl <= context.auto_stack
            else:
                self.stack = args.stack

        return


def add_subparsers(parser: argparse.ArgumentParser) -> None:
    """
    Add activate, deactivate and reactivate commands, along with associated sub-commands, to parser
    """
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


# the following functions are common only to posix_os_exec_shell.py and posix_os_exec.py
def get_activate_builder(activator: type[_Activator]) -> dict:
    """
    Create dictionary containing the environment variables to be set, unset and
    exported, as well as the package activation and deactivation scripts to be run.
    """
    if activator.stack:
        builder_result = activator.build_stack(activator.env_name_or_prefix)
    else:
        builder_result = activator.build_activate(activator.env_name_or_prefix)
    return builder_result


def parse_and_build(activator: type[_Activator], args: argparse.Namespace) -> dict:
    """
    Parse CLI arguments. Build and return the dictionary that contains environment variables to be
    set, unset, and exported, and any relevant package activation and deactivation scripts that
    should be run.
    """
    activator._parse_and_set_args(args)

    if args.command == "activate":
        # using redefined activate process instead of _Activator.activate
        cmds_dict = get_activate_builder(activator)
    elif args.command == "deactivate":
        cmds_dict = activator.build_deactivate()
    elif args.command == "reactivate":
        cmds_dict = activator.build_reactivate()

    return cmds_dict
