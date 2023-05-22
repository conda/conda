# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import argparse
import os
import re

from conda import CONDA_PACKAGE_ROOT
from conda.activate import _Activator, native_path_to_unix
from conda.base.context import context
from conda.cli.main import init_loggers
from conda.common.compat import on_win
from conda.exceptions import ArgumentError
from conda.plugins import CondaShellPlugins, hookimpl


class PosixPluginActivator(_Activator):
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


def activate(activator):
    if activator.stack:
        builder_result = activator.build_stack(activator.env_name_or_prefix)
    else:
        builder_result = activator.build_activate(activator.env_name_or_prefix)
    return builder_result


def raise_invalid_command_error(actual_command=None):
    message = "'activate', 'deactivate', or 'reactivate'" "command must be given"
    if actual_command:
        message += ". Instead got '%s'." % actual_command
    raise ArgumentError(message)


def ard(*args, **kwargs):
    # argparse handles cleanup but I need to check if the UTF-8 issue might still persist
    # no need to check for missing command - handled by argparse
    # env_args = tuple(ensure_text_type(s) for s in env_args)
    parser = argparse.ArgumentParser(
        description="Process conda activate, deactivate, and reactivate"
    )
    parser.add_argument("ardhc", type=str, nargs=1, help="this package's entry point")
    parser.add_argument(
        "command",
        metavar="c",
        type=str,
        nargs=1,
        help="the command to be run: 'activate', 'deactivate' or 'reactivate'",
    )
    parser.add_argument(
        "env",
        metavar="env",
        default=None,
        type=str,
        nargs="?",
        help="the name or prefix of the environment to be activated",
    )

    args = parser.parse_args()

    command = args.command[0]
    env = args.env

    context.__init__()
    init_loggers(context)

    if command not in ("activate", "deactivate", "reactivate"):
        raise_invalid_command_error(actual_command=command)

    env_args = (command, env) if env else (command,)
    activator = PosixPluginActivator(env_args)

    # call the methods leading up to the command-specific builds
    activator._parse_and_set_args(env_args)

    # at the moment, if activate is called without an environment, reactivation is being run
    # through conda's normal process because it would be called during '_parse_and_set_args'

    if command == "activate" and env:
        # using redefined activate function instead of _Activator.activate
        cmds_dict = activate(activator)
    elif command == "activate" and not env:
        cmds_dict = activator.build_reactivate()

    # TODO: look into deactivation process and see what's going on here; it's not working
    if command == "deactivate":
        cmds_dict = activator.build_deactivate()

    if command == "reactivate":
        cmds_dict = activator.build_reactivate()

    # unset_vars = cmds_dict["unset_vars"]
    # set_vars = cmds_dict["set_vars"]
    export_path = cmds_dict.get("export_path", {})
    export_vars = cmds_dict.get("export_vars", {})
    # deactivate_scripts = cmds_dict.get("deactivate_scripts", ())
    activate_scripts = cmds_dict.get("activate_scripts", ())

    print("activating! or deactivating!")
    env_map = os.environ

    # ignoring setting and unsetting variables for now
    # TODO: figure out how to set and unset vars :(

    for key, value in sorted(export_path.items()):
        env_map[str(key)] = str(value)

    for key, value in sorted(export_vars.items()):
        env_map[str(key)] = str(value)

    # we lose the ability to run the deactivate scripts as part of the initial environment
    # deactivate_list = [
    #     activator.run_script_tmpl % script for script in deactivate_scripts
    # ]
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
        summary="Plugin for POSIX shells used for activate, deactivate, and reactivate",
        action=ard,
    )
