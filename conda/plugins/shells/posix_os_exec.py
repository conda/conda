# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import os
import argparse


from common.compat import ensure_text_type
from base.context import context
from cli.main import init_loggers
from activate import PosixActivator
from exceptions import ArgumentError

from .. import CondaShellPlugins, hookimpl

def activate(activator):
    if activator.stack:
        builder_result = activator.build_stack(activator.env_name_or_prefix)
    else:
        builder_result = activator.build_activate(activator.env_name_or_prefix)
    return builder_result

def raise_invalid_command_error(actual_command=None):
            message = (
                "'activate', 'deactivate', or 'reactivate'"
                "command must be given"
            )
            if actual_command:
                message += ". Instead got '%s'." % actual_command
            raise ArgumentError(message)

def ard(*args, **kwargs):
    # argparse handles cleanup but I need to check if the UTF-8 issue might still persist
    # no need to check for missing command - handled by argparse
    # env_args = tuple(ensure_text_type(s) for s in env_args) 
    parser = argparse.ArgumentParser(
    description="Process conda activate, deactivate, and reactivate")
    parser.add_argument("ardhc", type=str, nargs=1, help="this package's entry point")
    parser.add_argument("command", metavar="c", type=str, nargs=1,
                    help="the command to be run: 'activate', 'deactivate' or 'reactivate'")
    parser.add_argument("env", metavar="env", default=None, type=str, nargs="?",
                    help="the name or prefix of the environment to be activated")

    args = parser.parse_args()

    command = args.command[0]
    env = args.env

    context.__init__()
    init_loggers(context)

    if command not in  ("activate", "deactivate", "reactivate"):
        raise_invalid_command_error(actual_command=command)
    
    env_args = (command, env) if env else (command,)
    activator = PosixActivator(env_args)

    # call the methods leading up to the command-specific builds
    activator._parse_and_set_args(env_args)

    # at the moment, if activate is called without an environment, reactivation is being run
    # through conda's normal process because it would be called during '_parse_and_set_args'

    if command == 'activate' and env:
        # using redefined activate function instead of _Activator.activate
        cmds_dict = activate(activator)
    elif command == 'activate' and not env:
        cmds_dict = activator.build_reactivate()

    #TODO: look into deactivation process and see what's going on here; it's not working
    if command == 'deactivate':
        cmds_dict = activator.build_deactivate()

    if command == 'reactivate':
        cmds_dict = activator.build_reactivate()

    unset_vars = cmds_dict["unset_vars"]
    set_vars = cmds_dict["set_vars"]
    export_path = cmds_dict.get("export_path", {})
    export_vars = cmds_dict.get("export_vars", {})
    deactivate_scripts = cmds_dict.get("deactivate_scripts", ())
    activate_scripts = cmds_dict.get("activate_scripts", ())

    print("activating! or deactivating!")
    env_map = os.environ

    # ignoring setting and unsetting variables for now
    # TODO: figure out how to set and unset vars :(
    
    
    for key, value in sorted(export_path.items()):
        env_map[str(key)]=str(value)
    
    for key, value in sorted(export_vars.items()):
        env_map[str(key)]=str(value)

    # we lose the ability to run the deactivate scripts as part of the initial environment
    deactivate_list = [activator.run_script_tmpl % script for script in deactivate_scripts]
    # TODO: run the deactivate scripts as sub-processes (attempt this)

    activate_list = [activator.run_script_tmpl % script for script in activate_scripts]

    shell_path = env_map["SHELL"]
    exec_shell = f". {shell_path}"

    # creating the list of arguments to be executed by os.execve
    # minimum argument is to execute the shell
    # order should be deactivate scripts followed by activation followed by activate scripts
    arg_list = []

    # deactivate scripts must be run BEFORE the new environment is activated!
    # the below would take place in the new environment
    # user would have to type in two commands for us to run os.exec twice
    # if deactivate_list:
    #     arg_list.extend(deactivate_list)
    
    arg_list.append(exec_shell)

    if activate_list:
        arg_list.extend(activate_list)

    os.execve(shell_path, arg_list, env_map)

@hookimpl
def conda_shell_plugins():
    yield CondaShellPlugins(
        name="posix_exec_plugin",
        summary="Plugin for POSIX shells that calls the conda processes used for activate, deactivate, and reactivate",
        action=ard
    )
