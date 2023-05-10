# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import os

from .. import CondaShellPlugins, hookimpl

def posix_plugin_with_shell():
    # the Python print statement will print to stdout as is but will not be evaluated
    # all arguments passed in to os.exec will be evaluated by the shell script

    print("echo Hello from Python!")

    path = "./shells/posix_os_exec_shell.sh"

    # all elements of arg list need to be strings
    # the arg list will be evaluated by act.sh, as written on 2023-05-10
    # the line break allows each argument to be evaluated separately
    # scripts that take in command line arguments will not have any interference from items passed in afterward.
    # arguments will continue to be processed even if there is an error caused by an earlier argument
    # still can't set PS1
    arg_list = [
        "./shells/posix_os_exec_shell.sh",
        "echo Hello from the act script\n",
        "echo Testing multiple args\n",
        "echo Testing running multiple new scripts\n",
        "./sum.sh 3 6\n"
        "~/learning/bash-mastery/sum_nums\n",
        "PS1='(we stan katherine chen) $'\n"
        "echo 5\n"
        "echo 13"]

    os.execv(path, arg_list)


@hookimpl
def conda_shell_plugins():
    yield CondaShellPlugins(
        name="posix_plugin_with_shell",
        summary="Plugin for POSIX shells that calls the conda processes used for activate, deactivate, and reactivate",
        action=posix_plugin_with_shell
    )