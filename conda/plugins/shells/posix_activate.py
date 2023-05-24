# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import re
import sys
from os.path import join

from conda import CONDA_PACKAGE_ROOT
from conda.activate import _Activator, native_path_to_unix
from conda.base.context import context
from conda.cli.main import init_loggers
from conda.common.compat import ensure_text_type, on_win
from conda.exceptions import conda_exception_handler

from .. import CondaShellPlugins, hookimpl


class PosixPluginActivator(_Activator):
    """
    Define syntax that is specific to Posix shells.
    Also contains logic that takes into account Posix shell use on Windows.
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


def handle_env(*args, **kwargs):
    """
    Export existing activate/reactivate/deactivate logic to a plugin.
    Would work in conjunction with a modified version of conda.sh that forwards
    to the plugin, rather than to an internally-defined activate process.
    A similar process to conda init would inject code into the user's shell profile
    to set the associated shell script as conda's entry point.
    """
    # cleanup argv
    # this can be updated to use argparse, in line with the os_exec approach
    env_args = sys.argv[2:]  # drop executable/script and sub-command
    env_args = tuple(ensure_text_type(s) for s in env_args)

    context.__init__()
    init_loggers(context)

    activator = PosixPluginActivator(env_args)
    print(activator.execute(), end="")

    return 0


def handle_exceptions(*args, **kwargs):
    """
    Return the appropriate error code if an exception occurs.
    These are handled through main.py and __main__.py during the current
    activate/reactivate/deactivate process.
    """
    return sys.exit(conda_exception_handler(handle_env, *args, **kwargs))


@hookimpl
def conda_shell_plugins():
    yield CondaShellPlugins(
        name="posix_plugin_current_logic",
        summary="Plugin for POSIX shells: handles conda activate, deactivate, and reactivate",
        action=handle_exceptions,
    )
