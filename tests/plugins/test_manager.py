# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import logging
import re
import sys

import pytest

from conda import plugins
from conda.base.context import context, reset_context
from conda.common.io import env_var
from conda.core import solve
from conda.exceptions import PluginError
from conda.plugins import virtual_packages

from .test_pre_command import pre_command_plugin

log = logging.getLogger(__name__)


class VerboseSolver(solve.Solver):
    def solve_final_state(self, *args, **kwargs):
        log.info("My verbose solver!")
        return super().solve_final_state(*args, **kwargs)


class VerboseSolverPlugin:
    @plugins.hookimpl
    def conda_solvers(self):
        yield plugins.CondaSolver(
            name="verbose-classic",
            backend=VerboseSolver,
        )


def test_load_no_plugins(plugin_manager):
    plugin_names = plugin_manager.load_plugins()
    assert plugin_names == []


def test_load_two_plugins_one_impls(plugin_manager):
    this_module = sys.modules[__name__]
    plugin_names = plugin_manager.load_plugins(this_module)
    assert plugin_names == [__name__]
    assert plugin_manager.get_plugins() == {this_module}
    assert plugin_manager.hook.conda_solvers.get_hookimpls() == []

    plugin_names = plugin_manager.load_plugins(VerboseSolverPlugin)
    assert plugin_names == ["VerboseSolverPlugin"]
    assert plugin_manager.get_plugins() == {this_module, VerboseSolverPlugin}

    hooks_impls = plugin_manager.hook.conda_solvers.get_hookimpls()
    assert len(hooks_impls) == 1
    assert hooks_impls[0].plugin == VerboseSolverPlugin


def test_get_hook_results(plugin_manager):
    name = "virtual_packages"
    assert plugin_manager.get_hook_results(name) == []

    # loading the archspec plugin module and make sure it was loaded correctly
    plugin_manager.load_plugins(virtual_packages.archspec)
    hook_result = plugin_manager.get_hook_results(name)
    assert len(hook_result) == 1
    assert hook_result[0].name == "archspec"

    # let's double-check the validation of conflicting plugins works
    class SecondArchspec:
        @plugins.hookimpl
        def conda_virtual_packages():
            yield plugins.CondaVirtualPackage("archspec", "", None)

    plugin_manager.register(SecondArchspec)
    with pytest.raises(
        PluginError, match=re.escape("Conflicting `virtual_packages` plugins found")
    ):
        plugin_manager.get_hook_results(name)


def test_load_plugins_error(plugin_manager, mocker):
    mocker.patch.object(
        plugin_manager, "register", side_effect=ValueError("load_plugins error")
    )
    with pytest.raises(PluginError) as exc:
        plugin_manager.load_plugins(VerboseSolverPlugin)
    assert plugin_manager.get_plugins() == set()
    assert exc.value.return_code == 1
    assert "load_plugins error" in str(exc.value)


def test_load_entrypoints_importerror(plugin_manager, mocker, monkeypatch):
    # the fake package under data/test-plugin is added to the PYTHONPATH
    # via the pytest config
    mocked_warning = mocker.patch("conda.plugins.manager.log.warning")
    plugin_manager.load_entrypoints("conda")
    assert plugin_manager.get_plugins() == set()
    assert mocked_warning.call_count == 1
    assert mocked_warning.call_args.args[0] == (
        "Could not load conda plugin `conda-test-plugin`:\n\nNo module named 'package_that_does_not_exist'"
    )


def test_disable_plugins_with_flag(
    conda_cli, pre_command_plugin
):
    """
    Run a test to ensure we can successfully disable externally registered plugins
    with the --no-plugins flag
    """
    assert not context.no_plugins
    out, err, code = conda_cli("--no-plugins", "info")
    assert pre_command_plugin.pre_command_action.mock_calls == []
    assert err == ""


def test_disable_plugins_with_env_var(
    conda_cli, monkeypatch, pre_command_plugin
):
    """
    Run a test to ensure we can successfully disable externally registered plugins
    via the CONDA_NO_PLUGINS environment variable
    """
    monkeypatch.setenv("CONDA_NO_PLUGINS", "True")
    reset_context()
    assert context.no_plugins

    out, err, code = conda_cli("info")
    assert pre_command_plugin.pre_command_action.mock_calls == []
    assert err == ""
