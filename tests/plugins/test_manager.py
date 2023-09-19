# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import logging
import re
import sys

import pluggy
import pytest
from packaging.version import Version
from pytest_mock import MockerFixture

from conda import plugins
from conda.core import solve
from conda.exceptions import CondaValueError, PluginError
from conda.plugins import virtual_packages
from conda.plugins.manager import CondaPluginManager

log = logging.getLogger(__name__)
this_module = sys.modules[__name__]

# detect if this is an older pluggy
pluggy_v100 = Version(pluggy.__version__) <= Version("1.0.0")


class VerboseSolver(solve.Solver):
    def solve_final_state(self, *args, **kwargs):
        log.info("My verbose solver!")
        return super().solve_final_state(*args, **kwargs)


VerboseCondaSolver = plugins.CondaSolver(
    name="verbose-classic",
    backend=VerboseSolver,
)


class VerboseSolverPlugin:
    @plugins.hookimpl
    def conda_solvers(*args):
        yield VerboseCondaSolver


DummyVirtualPackage = plugins.CondaVirtualPackage("dummy", "version", "build")
NoNameVirtualPackage = plugins.CondaVirtualPackage(None, None, None)


class DummyVirtualPackagePlugin:
    @plugins.hookimpl
    def conda_virtual_packages(*args):
        yield DummyVirtualPackage


class NoNameVirtualPackagePlugin:
    @plugins.hookimpl
    def conda_virtual_packages(*args):
        yield NoNameVirtualPackage


def test_load_without_plugins(plugin_manager: CondaPluginManager):
    plugin_names = plugin_manager.load_plugins()
    assert plugin_names == 0


def test_load_two_plugins_one_impls(plugin_manager: CondaPluginManager):
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


def test_get_hook_results(plugin_manager: CondaPluginManager):
    name = "virtual_packages"
    assert plugin_manager.get_hook_results(name) == []

    # loading the archspec plugin module and make sure it was loaded correctly
    plugin_manager.load_plugins(virtual_packages.archspec)
    hook_result = plugin_manager.get_hook_results(name)
    assert len(hook_result) == 1
    assert hook_result[0].name == "archspec"

    # loading an unknown hook result should raise an error
    with pytest.raises(PluginError, match="Could not find requested `unknown` plugins"):
        plugin_manager.get_hook_results("unknown")

    # let's double-check the validation of conflicting plugins works
    class SecondArchspec:
        @plugins.hookimpl
        def conda_virtual_packages():
            yield plugins.CondaVirtualPackage("archspec", "", None)

    plugin_manager.register(SecondArchspec)
    with pytest.raises(
        PluginError, match="Conflicting `virtual_packages` plugins found"
    ):
        plugin_manager.get_hook_results(name)


def test_load_plugins_error(plugin_manager: CondaPluginManager):
    # first load the plugin once
    plugin_manager.load_plugins(VerboseSolverPlugin)
    assert plugin_manager.get_plugins() == {VerboseSolverPlugin}


def test_load_entrypoints_success(plugin_manager: CondaPluginManager):
    assert plugin_manager.load_entrypoints("test_plugin", "success") == 1
    assert len(plugin_manager.get_plugins()) == 1
    assert plugin_manager.list_name_plugin()[0][0] == "test_plugin.success"


def test_load_entrypoints_importerror(
    plugin_manager: CondaPluginManager,
    mocker: MockerFixture,
):
    mocked_warning = mocker.patch("conda.plugins.manager.log.warning")

    assert plugin_manager.load_entrypoints("test_plugin", "importerror") == 0
    assert len(plugin_manager.get_plugins()) == 0

    assert mocked_warning.call_count == 1
    assert mocked_warning.call_args.args[0] == (
        "Error while loading conda entry point: importerror "
        "(No module named 'package_that_does_not_exist')"
    )


def test_load_entrypoints_blocked(plugin_manager: CondaPluginManager):
    plugin_manager.set_blocked("test_plugin.blocked")

    assert plugin_manager.load_entrypoints("test_plugin", "blocked") == 0
    if pluggy_v100:
        assert plugin_manager.get_plugins() == set()
    else:
        assert plugin_manager.get_plugins() == {None}
    assert plugin_manager.list_name_plugin() == [("test_plugin.blocked", None)]


def test_load_entrypoints_register_valueerror(plugin_manager: CondaPluginManager):
    """
    Cover check when self.register() raises ValueError.
    """
    plugin_manager.load_entrypoints("test_plugin", "success")
    plugin_manager.load_entrypoints("test_plugin", "success")


def test_unknown_solver(plugin_manager: CondaPluginManager):
    """
    Cover getting a solver that doesn't exist.
    """
    with pytest.raises(CondaValueError):
        plugin_manager.get_solver_backend("p_equals_np")


def test_known_solver(plugin_manager: CondaPluginManager):
    """
    Cover getting a solver that exists.
    """
    plugin_manager.load_plugins(VerboseSolverPlugin)
    assert plugin_manager.get_solver_backend("verbose-classic") == VerboseSolver


def test_get_canonical_name_object(plugin_manager: CondaPluginManager):
    canonical_name = plugin_manager.get_canonical_name(object())
    assert re.match(r"<unknown_module>.object\[\d+\]", canonical_name), canonical_name


def test_get_canonical_name_module(plugin_manager: CondaPluginManager):
    assert plugin_manager.get_canonical_name(this_module) == __name__


def test_get_canonical_name_class(plugin_manager: CondaPluginManager):
    canonical_name = plugin_manager.get_canonical_name(VerboseSolverPlugin)
    assert canonical_name == f"{__name__}.VerboseSolverPlugin"


def test_get_canonical_name_instance(plugin_manager: CondaPluginManager):
    canonical_name = plugin_manager.get_canonical_name(VerboseSolverPlugin())
    assert re.match(
        rf"{__name__}.VerboseSolverPlugin\[\d+\]",
        canonical_name,
    )


@pytest.mark.parametrize("plugin", [this_module, VerboseSolverPlugin])
def test_disable_external_plugins(plugin_manager: CondaPluginManager, plugin: object):
    """
    Run a test to ensure we can successfully disable externally registered plugins.
    """
    assert plugin_manager.load_plugins(plugin) == 1
    assert plugin_manager.get_plugins() == {plugin}
    plugin_manager.disable_external_plugins()
    if pluggy_v100:
        assert plugin_manager.get_plugins() == set()
    else:
        assert plugin_manager.get_plugins() == {None}


def test_get_virtual_packages(plugin_manager: CondaPluginManager):
    plugin_manager.load_plugins(DummyVirtualPackagePlugin)
    assert plugin_manager.get_virtual_packages() == (DummyVirtualPackage,)


def test_get_virtual_packages_no_name(plugin_manager: CondaPluginManager):
    plugin_manager.load_plugins(NoNameVirtualPackagePlugin)
    with pytest.raises(PluginError, match="Invalid plugin names"):
        plugin_manager.get_virtual_packages()


def test_get_solvers(plugin_manager: CondaPluginManager):
    plugin_manager.load_plugins(VerboseSolverPlugin)
    assert plugin_manager.get_plugins() == {VerboseSolverPlugin}
    assert plugin_manager.get_solvers() == {"verbose-classic": VerboseCondaSolver}
