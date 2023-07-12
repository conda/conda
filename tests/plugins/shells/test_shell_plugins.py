# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import os
import re
from argparse import Namespace
from collections import namedtuple
from pathlib import PurePath

import pytest

import conda.core.index
from conda import plugins
from conda.activate import native_path_to_unix
from conda.base.constants import ROOT_ENV_NAME
from conda.base.context import conda_tests_ctxt_mgmt_def_pol, context
from conda.common.io import env_var, env_vars
from conda.exceptions import PluginError
from conda.plugins.shells.shell_plugins import PluginActivator
from conda.testing import (
    CondaCLIFixture,
    TmpEnvFixture,
    conda_cli,
    path_factory,
    tmp_env,
)
from conda.testing.solver_helpers import package_dict
from tests.test_activate import POP_THESE


class BashPlugin:
    @plugins.hookimpl
    def conda_shell_plugins():
        yield plugins.CondaShellPlugins(
            name="bash_plugin",
            summary="test bash plugin",
            script_path=os.path.abspath(
                "conda/plugins/shells/shell_scripts/posix_os_exec_shell.sh"
            ),
            pathsep_join=":".join,
            sep="/",
            path_conversion=native_path_to_unix,
            script_extension=".sh",
            tempfile_extension=None,
            command_join="\n",
            run_script_tmpl='. "%s"',
        )


@pytest.fixture
def plugin_hook(plugin_manager):
    plugin_manager.load_plugins(BashPlugin)
    return plugin_manager.get_shell_syntax()


@pytest.fixture
def test_env_no_packages(tmp_env, conda_cli):
    with tmp_env() as prefix:
        out, err, code = conda_cli("list", "--prefix", prefix)


# TODO: Make two temp envs - one with activation scripts, one without


def test_init_happy_path(plugin_hook):
    activator = PluginActivator(plugin_hook)

    assert activator.name == "bash_plugin"
    assert activator.summary == "test bash plugin"
    assert activator.script_path == os.path.abspath(
        "conda/plugins/shells/shell_scripts/posix_os_exec_shell.sh"
    )
    assert activator.pathsep_join(["a", "b", "c"]) == "a:b:c"
    assert activator.sep == "/"
    assert activator.path_conversion == native_path_to_unix
    assert activator.script_extension == ".sh"
    assert activator.tempfile_extension is None
    assert activator.command_join == "\n"
    assert activator.run_script_tmpl % "hello" == '. "hello"'
    assert activator.environ


def test_init_missing_fields_assigned_None():
    Syntax = namedtuple("empty_plugin", "name, summary")
    activator = PluginActivator(Syntax("empty_plugin", "plugin with missing fields"))

    assert activator.name == "empty_plugin"
    assert activator.summary == "plugin with missing fields"
    assert activator.script_path is None
    assert activator.pathsep_join is None
    assert activator.sep is None
    assert activator.path_conversion is None
    assert activator.script_extension is None
    assert activator.tempfile_extension is None
    assert activator.command_join is None
    assert activator.run_script_tmpl is None
    assert activator.environ


EMPTY_CMDS_DICT = {
    "unset_vars": [],
    "set_vars": {},
    "export_path": {},
    "export_vars": {},
}


def test_update_env_map_empty_cmd_dict_no_change(plugin_hook):
    current_env = os.environ.copy()

    activator = PluginActivator(plugin_hook)
    env_map = activator.update_env_map(EMPTY_CMDS_DICT)

    assert env_map == current_env


CMDS_DICT_UNSET_SET_ONLY = {
    "unset_vars": ["FRIES", "CHIPS"],
    "set_vars": {"HIGHWAY": "freeway"},
}


def test_update_env_map_unset_set_only(plugin_hook, monkeypatch):
    """
    Test that new environment mapping is updated correctly with cmd_dict that only contains
    unset_vars and set_vars keys.
    """
    current_env = os.environ.copy()
    current_env.update({"HIGHWAY": "freeway"})

    # activator makes its own copy of os.environ, so we need to update env vars directly    monkeypatch.setenv("FRIES", "with ketchup")
    monkeypatch.setenv("CHIPS", "with vinegar")

    activator = PluginActivator(plugin_hook)
    env_map = activator.update_env_map(CMDS_DICT_UNSET_SET_ONLY)

    assert env_map.get("FRIES", None) is None
    assert env_map.get("CHIPS", None) is None
    assert env_map["HIGHWAY"] == "freeway"
    assert env_map == current_env


def test_update_env_map_missing_env_var(plugin_hook, monkeypatch):
    """
    Test that new environment mapping is updated correctly with cmd_dict that contains
    an unset var that does not exist.
    """
    current_env = os.environ.copy()
    current_env.update({"HIGHWAY": "freeway"})

    # activator makes its own copy of os.environ, so we need to update env vars directly    monkeypatch.setenv("CHIPS", "with vinegar")

    activator = PluginActivator(plugin_hook)
    env_map = activator.update_env_map(CMDS_DICT_UNSET_SET_ONLY)

    assert env_map.get("FRIES", None) is None
    assert env_map.get("CHIPS", None) is None
    assert env_map["HIGHWAY"] == "freeway"
    assert env_map == current_env


# use data types that need to be converted to strings
CMDS_DICT_ALL = {
    "unset_vars": ["A", 1],
    "set_vars": {"B": 2, "C": "c", 4: True},
    "export_path": {"PATH": "/".join([".", "a", "b", "c"])},
    "export_vars": {"E": 5, "F": "f", 6: False},
}


def test_update_env_map_all(plugin_hook, monkeypatch):
    combined_dict = {
        **CMDS_DICT_ALL["set_vars"],
        **CMDS_DICT_ALL["export_path"],
        **CMDS_DICT_ALL["export_vars"],
    }
    update_dict = {str(k): str(v) for k, v in combined_dict.items()}
    current_env = os.environ.copy()
    current_env.update(update_dict)

    # activator makes its own copy of os.environ, so we need to update env vars directly
    monkeypatch.setenv("A", "a")
    monkeypatch.setenv("1", "one")

    activator = PluginActivator(plugin_hook)
    env_map = activator.update_env_map(CMDS_DICT_ALL)

    assert env_map.get("A", None) is None
    assert env_map.get("1", None) is None
    assert env_map["B"] == "2"
    assert env_map["C"] == "c"
    assert env_map["4"] == "True"
    assert env_map["PATH"] == "./a/b/c"
    assert env_map["E"] == "5"
    assert env_map["F"] == "f"
    assert env_map["6"] == "False"
    assert env_map == current_env


def test_parse_and_build_dev_env(plugin_hook):
    ns = Namespace(command="activate", env=None, dev=True, stack=None)
    activator = PluginActivator(plugin_hook)
    builder = activator.parse_and_build(ns)

    assert isinstance(builder["unset_vars"], tuple)
    assert isinstance(builder["set_vars"], dict)
    assert isinstance(builder["export_vars"], dict)
    assert int(builder["export_vars"]["CONDA_SHLVL"]) == 1
    assert "devenv" in builder["export_vars"]["PATH"]


ENV_VARS = (
    "CONDA_PREFIX",
    "CONDA_SHLVL",
    "CONDA_DEFAULT_ENV",
    "CONDA_PROMPT_MODIFIER",
    "CONDA_PREFIX_1",
)

PARSE_AND_BUILD_TEST_CASES = (
    # (Namespace(command="activate", dev=True, env="tmp_env", stack=False), "activate"),
    (Namespace(command="activate", dev=True, env="tmp_env", stack=True), "activate"),
)


# I have to specify a solver
@pytest.mark.skip
def test_parse_and_build_activate_tmp_env_no_stack(tmp_env, plugin_hook, monkeypatch):
    ns = Namespace(command="activate", dev=True, env="tmp_env", stack=False)
    monkeypatch.setenv("CONDA_SHLVL", "1")

    with tmp_env() as prefix:
        if ns.command == "activate" and ns.env == "tmp_env":
            ns.env = prefix
        activator = PluginActivator(plugin_hook)
        builder = activator.parse_and_build(ns)

    assert type(builder["unset_vars"]) is tuple
    assert type(builder["set_vars"]) is dict
    assert type(builder["export_vars"]) is dict
    assert int(builder["export_vars"]["CONDA_SHLVL"]) == 2
    assert prefix in PurePath(builder["export_vars"].get("CONDA_PREFIX", "/none")).name
