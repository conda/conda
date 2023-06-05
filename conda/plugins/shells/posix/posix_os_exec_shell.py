# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import argparse
import os
import re

from conda import CONDA_PACKAGE_ROOT
from conda.activate import _Activator, native_path_to_unix
from conda.base.context import context
from conda.cli.main import init_loggers
from conda.common.compat import on_win
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

    hook_source_path = os.path.join(
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
        Set context.dev if a --dev flag exists.
        For activate, set self.env_name_or_prefix and self.stack.
        """
        context.dev = args.dev or context.dev

        if args.command == "activate":
            self.env_name_or_prefix = args.env

            if args.stack is None:
                self.stack = context.auto_stack and context.shlvl <= context.auto_stack
            else:
                self.stack = args.stack

        return


def get_parsed_args(argv: list[str]) -> argparse.Namespace:
    """
    Parse CLI arguments to determine desired command.
    Create namespace with 'command' key, optional 'dev' key and, for activate only,
    optional 'env' and 'stack' keys.
    """
    parser = argparse.ArgumentParser(
        "conda posix_plugin_with_shell",
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
        default=None,
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
        default=None,
        action="store_false",
        help="Do not stack the environment. Overrides 'auto_stack' setting.",
    )
    activate.add_argument(
        "--dev", action="store_true", default=False, help=argparse.SUPPRESS
    )

    commands.add_parser("deactivate", help="deactivate the current environment")
    commands.add_parser(
        "reactivate",
        help="reactivate the current environment, updating environment variables",
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

    args = parser.parse_args(argv)

    return args


def get_activate_builder(activator):
    """
    Create dictionary containing the environment variables to be set, unset and
    exported, as well as the package activation and deactivation scripts to be run.
    """
    if activator.stack:
        builder_result = activator.build_stack(activator.env_name_or_prefix)
    else:
        builder_result = activator.build_activate(activator.env_name_or_prefix)
    return builder_result


def activate(activator, cmds_dict):
    """
    Change environment. As a new process in in new environment, run deactivate
    scripts from packages in old environment (to reset env variables) and
    activate scripts from packages installed in new environment.
    """
    path = "conda/plugins/shells/shell_scripts/posix_os_exec_shell.sh"
    arg_list = [path]
    env_map = os.environ.copy()

    unset_vars = cmds_dict["unset_vars"]
    set_vars = cmds_dict["set_vars"]
    export_path = cmds_dict.get("export_path", {})  # seems to be empty for posix shells
    export_vars = cmds_dict.get("export_vars", {})

    for key in unset_vars:
        env_map.pop(str(key), None)

    for key, value in set_vars.items():
        env_map[str(key)] = str(value)

    for key, value in export_path.items():
        env_map[str(key)] = str(value)

    for key, value in export_vars.items():
        env_map[str(key)] = str(value)

    deactivate_scripts = cmds_dict.get("deactivate_scripts", ())

    if deactivate_scripts:
        deactivate_list = [
            (activator.run_script_tmpl % script) + activator.command_join
            for script in deactivate_scripts
        ]
        arg_list.extend(deactivate_list)

    activate_scripts = cmds_dict.get("activate_scripts", ())

    if activate_scripts:
        activate_list = [
            (activator.run_script_tmpl % script) + activator.command_join
            for script in activate_scripts
        ]
        arg_list.extend(activate_list)

    os.execve(path, arg_list, env_map)


def posix_plugin_with_shell(argv: list[str]) -> SystemExit:
    """
    Run process associated with parsed CLI command (activate, deactivate, reactivate).
    This plugin is intended for use only with POSIX shells.
    """
    args = get_parsed_args(argv)

    context.__init__()
    init_loggers(context)

    activator = PosixPluginActivator(args)
    activator._parse_and_set_args(args)

    if args.command == "activate":
        # using redefined activate process instead of _Activator.activate
        cmds_dict = get_activate_builder(activator)
    elif args.command == "deactivate":
        cmds_dict = activator.build_deactivate()
    elif args.command == "reactivate":
        cmds_dict = activator.build_reactivate()

    return activate(activator, cmds_dict)


@hookimpl
def conda_subcommands():
    yield CondaSubcommand(
        name="posix_plugin_with_shell",
        summary="Plugin for POSIX shells used for activate, deactivate, and reactivate",
        action=posix_plugin_with_shell,
    )


@hookimpl
def conda_shell_plugins():
    yield CondaShellPlugins(
        name="posix_plugin_with_shell",
        summary="Plugin for POSIX shells used for activate, deactivate, and reactivate",
        activator=PosixPluginActivator,
    )
