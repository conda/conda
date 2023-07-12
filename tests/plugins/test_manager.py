# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import logging
import re
import sys

import pytest

from conda import plugins
from conda.core import solve
from conda.exceptions import PluginError
from conda.plugins import shells, virtual_packages

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


class OneShellPlugin:
    @plugins.hookimpl
    def conda_shell_plugins():
        yield plugins.CondaShellPlugins(
            name="shellplugin",
            summary="test plugin",
            script_path="abc.sh",
            pathsep_join=":".join,
            sep="/",
            path_conversion=lambda x: x + 1,
            script_extension=".sh",
            tempfile_extension=None,
            command_join="\n",
            run_script_tmpl='. "%s"',
        )


class TwoShellPlugins:
    @plugins.hookimpl
    def conda_shell_plugins():
        yield plugins.CondaShellPlugins(
            name="shellplugin",
            summary="test plugin",
            script_path="abc.sh",
            pathsep_join=":".join,
            sep="/",
            path_conversion=lambda x: x,
            script_extension=".sh",
            tempfile_extension=None,
            command_join="\n",
            run_script_tmpl='. "%s"',
        )
        yield plugins.CondaShellPlugins(
            name="shellplugin2",
            summary="second test plugin",
            script_path="abc.sh",
            pathsep_join=":".join,
            sep="/",
            path_conversion=lambda x: x,
            script_extension=".sh",
            tempfile_extension=None,
            command_join="\n",
            run_script_tmpl='. "%s"',
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


def test_get_shell_syntax_no_plugins(plugin_manager):
    """Raise error if no shell plugins are loaded"""
    plugin_manager.load_plugins()

    with pytest.raises(PluginError) as e:
        plugin_manager.get_shell_syntax()

    assert "No plugins installed are compatible with this shell" in str(e.value)


def test_get_shell_syntax(plugin_manager):
    """Ensure that hook is returned correctly"""
    plugin_manager.load_plugins(OneShellPlugin)
    results = list(plugin_manager.get_hook_results("shell_plugins"))
    assert len(results) == 1

    hook = plugin_manager.get_shell_syntax()

    assert hook.name == "shellplugin"
    assert hook.summary == "test plugin"
    assert hook.script_path == "abc.sh"
    assert hook.pathsep_join(["a", "b", "c"]) == "a:b:c"
    assert hook.sep == "/"
    assert hook.path_conversion(3) == 4
    assert hook.script_extension == ".sh"
    assert hook.tempfile_extension is None
    assert hook.command_join == "\n"
    assert hook.run_script_tmpl % hook.script_path == '. "abc.sh"'


def test_get_shell_syntax_error_multiple_plugins(plugin_manager):
    """Raise error if multiple shell plugins are yielded"""
    plugin_manager.load_plugins(TwoShellPlugins)

    with pytest.raises(PluginError) as e:
        plugin_manager.get_shell_syntax()

    assert "Multiple compatible plugins found" in str(e.value)
    assert "shellplugin" in str(e.value)
    assert "shellplugin2" in str(e.value)


def test_get_shell_syntax_error_no_plugins(plugin_manager):
    """Raise error if no shell plugins are yielded"""
    plugin_manager.load_plugins()

    with pytest.raises(PluginError) as e:
        plugin_manager.get_shell_syntax()

    assert "No plugins installed are compatible with this shell" in str(e.value)
