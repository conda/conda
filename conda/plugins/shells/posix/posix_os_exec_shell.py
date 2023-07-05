# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import argparse
import os

from conda.activate import native_path_to_unix
from conda.base.context import context
from conda.cli.main import init_loggers
from conda.plugins import CondaShellPlugins, CondaSubcommand, hookimpl

from .common import PosixPluginActivator, add_subparsers, parse_and_build


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
    add_subparsers(parser)
    args = parser.parse_args(argv)

    return args


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

    syntax = context.plugin_manager.get_shell_syntax("posix_plugin_with_shell")
    activator = PosixPluginActivator(syntax, args)
    cmds_dict = parse_and_build(activator, args)

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
        script_path=os.path.abspath(
            "conda/plugins/shells/shell_scripts/posix_os_exec_shell.sh"
        ),
        pathsep_join=":".join,
        sep="/",
        path_conversion=native_path_to_unix,
        script_extension=".sh",
        tempfile_extension=None,
        command_join="\n",
        run_script_tmpl='. "%s"',
        unset_var_tmpl=None,
        export_var_tmpl=None,
        set_var_tmpl=None,
    )
