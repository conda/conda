# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import logging
import re
import sys

import pluggy
import pytest
from packaging.version import Version

from conda import plugins
from conda.core import solve
from conda.exceptions import PluginError
from conda.plugins import virtual_packages

log = logging.getLogger(__name__)
this_module = sys.modules[__name__]


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
    assert plugin_names == 0


def test_load_two_plugins_one_impls(plugin_manager):
    plugin_names = plugin_manager.load_plugins(this_module)
    assert plugin_names == 1
    assert plugin_manager.get_plugins() == {this_module}
    assert plugin_manager.hook.conda_solvers.get_hookimpls() == []

    plugin_names = plugin_manager.load_plugins(VerboseSolverPlugin)
    assert plugin_names == 1
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

    # loading an unknown hook result should raise an error
    with pytest.raises(
        PluginError, match=re.escape("Could not find requested `unknown` plugins")
    ):
        plugin_manager.get_hook_results("unknown")

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


def test_load_plugins_error(plugin_manager):
    # first load the plugin once
    plugin_manager.load_plugins(VerboseSolverPlugin)
    # then try again to trigger a PluginError via the `ValueError` that
    # pluggy.PluginManager.register throws on duplicate plugins
    with pytest.raises(
        PluginError, match="Error while loading first-party conda plugin"
    ):
        plugin_manager.load_plugins(VerboseSolverPlugin)
    assert plugin_manager.get_plugins() == {VerboseSolverPlugin}


def test_load_entrypoints_success(plugin_manager):
    assert plugin_manager.load_entrypoints("test_plugin", "success") == 1
    assert len(plugin_manager.get_plugins()) == 1
    assert plugin_manager.list_name_plugin()[0][0] == "test_plugin.success"


def test_load_entrypoints_importerror(plugin_manager, mocker):
    mocked_warning = mocker.patch("conda.plugins.manager.log.warning")

    assert plugin_manager.load_entrypoints("test_plugin", "importerror") == 0
    assert len(plugin_manager.get_plugins()) == 0

    assert mocked_warning.call_count == 1
    assert mocked_warning.call_args.args[0] == (
        "Error while loading conda entry point: importerror "
        "(No module named 'package_that_does_not_exist')"
    )


def test_load_entrypoints_blocked(plugin_manager):
    plugin_manager.set_blocked("test_plugin.blocked")

    assert plugin_manager.load_entrypoints("test_plugin", "blocked") == 0
    if Version(pluggy.__version__) > Version("1.0.0"):
        assert plugin_manager.get_plugins() == {None}
    else:
        assert plugin_manager.get_plugins() == set()
    assert plugin_manager.list_name_plugin() == [("test_plugin.blocked", None)]


def test_get_canonical_name_object(plugin_manager):
    canonical_name = plugin_manager.get_canonical_name(object())
    assert re.match(r"<unknown_module>.object\[\d+\]", canonical_name), canonical_name


def test_get_canonical_name_module(plugin_manager):
    assert plugin_manager.get_canonical_name(this_module) == __name__


def test_get_canonical_name_class(plugin_manager):
    canonical_name = plugin_manager.get_canonical_name(VerboseSolverPlugin)
    assert canonical_name == f"{__name__}.VerboseSolverPlugin"


def test_get_canonical_name_instance(plugin_manager):
    canonical_name = plugin_manager.get_canonical_name(VerboseSolverPlugin())
    assert re.match(
        rf"{__name__}.VerboseSolverPlugin\[\d+\]",
        canonical_name,
    )
