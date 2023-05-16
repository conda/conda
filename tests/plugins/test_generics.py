# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import pytest

from conda import plugins
from conda.plugins.types import CondaOnException, CondaPostRun, CondaPreRun


class PreRunPlugin:
    def __init__(self):
        self.invoked = False
        self.args = None

    def generic_pre_run_plugin():
        pass

    @plugins.hookimpl
    def conda_pre_run(self):
        yield CondaPreRun(
            name="custom_pre_run", action=self.generic_pre_run_plugin, run_for="install"
        )


class PostRunPlugin:
    def __init__(self):
        self.invoked = False
        self.args = None

    def generic_post_run_plugin():
        pass

    @plugins.hookimpl
    def conda_post_run(self):
        yield CondaPostRun(
            name="custom_post_run",
            action=self.generic_post_run_plugin,
            run_for="install",
        )


class OnExceptionPlugin:
    def __init__(self):
        self.invoked = False
        self.args = None

    def generic_on_exception_plugin():
        pass

    @plugins.hookimpl
    def conda_on_exception(self):
        yield CondaOnException(
            name="custom_on_exception",
            action=self.generic_on_exception_plugin,
        )


@pytest.fixture()
def pre_run_plugin(mocker, plugin_manager):
    mocker.patch.object(PreRunPlugin, "custom_pre_run")

    generic_pre_run_plugin = PreRunPlugin()
    plugin_manager.register(generic_pre_run_plugin)
    return generic_pre_run_plugin


# TODO Create fixtures for post-run and on-exception plugins

# TODO Create tests for generic plugins


def test_pre_run_invoked(generic_pre_run_plugin, cli_main):
    pass
