# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""
This module does not run any test but provides a plugin that can be loaded as a module.

The plugin contained here is a simple implementation of the ``conda_pre_commands`` plugin
hook that simply prints, "hello" before the ``conda info`` command runs.
"""
from conda import plugins


def verbose_pre_command_action(*args, **kwargs):
    print("hello")


@plugins.hookimpl
def conda_pre_commands():
    yield plugins.CondaPreCommand(
        name="verbose_pre_command", action=verbose_pre_command_action, run_for={"info"}
    )
