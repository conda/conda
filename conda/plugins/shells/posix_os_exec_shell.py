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


def get_activate_builder(activator):
    '''
    create dictionary containing the environment variables to be set, unset and exported,
    as well as the package activation and deactivation scripts to be run 
    '''
    print("Plugin: Build cmds_dict...")

    if activator.stack:
        builder_result = activator.build_stack(activator.env_name_or_prefix)
    else:
        builder_result = activator.build_activate(activator.env_name_or_prefix)
    return builder_result

def activate(activator, cmds_dict):
    '''
    change environment and run activate scripts from packages installed in new environment
    '''

    # current issue: Activation won't run if I run the shell script and needs
    # the first argument to be a path to the shell, but if the first argument is a path to 
    # the shell, I need to figure out a different method to run the package activation scripts

    print("Plugin: In activate...")

    path = "./shells/posix_os_exec_shell.sh"
    arg_list = [path]
    env_map = os.environ

    # for PosixActivator process, no unset vars and only var that is set is prompt
    # this method ignores them for now
    export_path = cmds_dict.get("export_path", {}) # seems to be empty for posix shells
    export_vars = cmds_dict.get("export_vars", {})
    activate_scripts = cmds_dict.get("activate_scripts", ())
    

    print(f"{export_path=}")
    print(f"{export_vars=}")

    for key, value in sorted(export_path.items()):
        env_map[str(key)]=str(value)
    
    for key, value in sorted(export_vars.items()):
        env_map[str(key)]=str(value)

    print(env_map)

    activate_list = [(activator.run_script_tmpl % script) + activator.command_join for script in activate_scripts]

    if activate_list:
        arg_list.extend(activate_list)

    os.execve(path, arg_list, env_map)

def deactivate_scripts(activator, cmds_dict, env):
    '''
    run deactivate scripts from packages installed into the existing environment prior to activating new environment
    '''
    print("Plugin: In deactivate_scripts...")

    path = "./shells/posix_os_exec_shell.sh"
    arg_list = [path]
    activate_command = f"conda ppws activate_pt2 {env}"

    deactivate_scripts = cmds_dict.get("deactivate_scripts", ())
    deactivate_list = [(activator.run_script_tmpl % script) + activator.command_join for script in deactivate_scripts]

    if deactivate_list:
        arg_list.extend(deactivate_list)

    arg_list.append(activate_command)

    os.execv(path, arg_list)


def raise_invalid_command_error(actual_command=None):
            message = (
                "'activate', 'deactivate', or 'reactivate'"
                "command must be given"
            )
            if actual_command:
                message += ". Instead got '%s'." % actual_command
            raise ArgumentError(message)


def posix_plugin_with_shell(*args, **kwargs):
    # package deactivation scripts need to run in old environment, before rest of activation process is run
    print("Plugin: In ppws...")

    # argparse handles cleanup but I need to check if the UTF-8 issue might still persist
    # no need to check for missing command - handled by argparse
    # env_args = tuple(ensure_text_type(s) for s in env_args) 
    parser = argparse.ArgumentParser(
    description="Process conda activate, deactivate, and reactivate")
    parser.add_argument("ppws", type=str, nargs=1, help="this package's entry point")
    parser.add_argument("command", metavar="c", type=str, nargs=1,
                    help="the command to be run: 'activate', 'deactivate' or 'reactivate'")
    parser.add_argument("env", metavar="env", default=None, type=str, nargs="?",
                    help="the name or prefix of the environment to be activated")

    args = parser.parse_args()

    command = args.command[0]
    env = args.env
    print(f"{env=}")

    context.__init__()
    init_loggers(context)

    if command not in  ("activate", "deactivate", "reactivate", "activate_pt2"):
        raise_invalid_command_error(actual_command=command)
    
    if command == "activate_pt2":
        env_args = ("activate", env)
    else:
        env_args = (command, env) if env else (command,)
    
    activator = PosixActivator(env_args)

    # call the methods leading up to the command-specific builds
    activator._parse_and_set_args(env_args)

    # at the moment, if activate is called without an environment, reactivation is being run
    # through conda's normal process because this process would be called during '_parse_and_set_args'
    # this can be dealt with later by editing the '_parse_and_set_args' method
    # or creating a new version for the plugin

    if command == 'activate' and env:
        # using redefined activate process instead of _Activator.activate
        cmds_dict = get_activate_builder(activator)
        deactivate_scripts(activator, cmds_dict, env)
    elif command == 'activate' and not env:
        # activate without an environment specified is actually reactivate
        cmds_dict = activator.build_reactivate()

    if command == 'activate_pt2':
        cmds_dict = get_activate_builder(activator)
        activate(activator, cmds_dict)

    #TODO: look into deactivation process and see what's going on here; it's not working
    # can we just exit the sub-shell? If so, how do we do that?
    if command == 'deactivate':
        cmds_dict = activator.build_deactivate()

    if command == 'reactivate':
        cmds_dict = activator.build_reactivate()




@hookimpl
def conda_shell_plugins():
    yield CondaShellPlugins(
        name="posix_exec_plugin_with_shell",
        summary="Plugin for POSIX shells that calls the conda processes used for activate, deactivate, and reactivate",
        action=posix_plugin_with_shell
    )