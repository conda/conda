# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import json
import os
import platform
import sys
from functools import lru_cache
from itertools import chain
from logging import getLogger
from os.path import dirname, isdir, join
from pathlib import Path
from re import escape
from shutil import which
from subprocess import CalledProcessError, check_output
from tempfile import gettempdir
from typing import Iterable
from uuid import uuid4

import pytest

from conda import CONDA_PACKAGE_ROOT, CONDA_SOURCE_ROOT
from conda import __version__ as conda_version
from conda.activate import (
    CmdExeActivator,
    CshActivator,
    FishActivator,
    PosixActivator,
    PowerShellActivator,
    XonshActivator,
    _build_activator_cls,
    activator_map,
    native_path_to_unix,
)
from conda.auxlib.ish import dals
from conda.base.constants import (
    CONDA_ENV_VARS_UNSET_VAR,
    PACKAGE_ENV_VARS_DIR,
    PREFIX_STATE_FILE,
    ROOT_ENV_NAME,
)
from conda.base.context import conda_tests_ctxt_mgmt_def_pol, context
from conda.cli.main import main_sourced
from conda.common.compat import ensure_text_type, on_win
from conda.common.io import captured, env_var, env_vars
from conda.exceptions import EnvironmentLocationNotFound, EnvironmentNameNotFound
from conda.gateways.disk.create import mkdir_p
from conda.gateways.disk.delete import rm_rf
from conda.gateways.disk.update import touch
from conda.testing import CondaCLIFixture, PathFactoryFixture, TmpEnvFixture
from conda.testing.helpers import tempdir
from conda.testing.integration import SPACER_CHARACTER

log = getLogger(__name__)


# Here, by removing --dev you can try weird situations that you may want to test, upgrade paths
# and the like? What will happen is that the conda being run and the shell scripts it's being run
# against will be essentially random and will vary over the course of activating and deactivating
# environments. You will have absolutely no idea what's going on as you change code or scripts and
# encounter some different code that ends up being run (some of the time). You will go slowly mad.
# No, you are best off keeping --dev on the end of these. For sure, if conda bundled its own tests
# module then we could remove --dev if we detect we are being run in that way.
dev_arg = "--dev"
activate_args = ["activate", dev_arg]
reactivate_args = ["reactivate", dev_arg]
deactivate_args = ["deactivate", dev_arg]

if on_win:
    import ctypes

    PYTHONIOENCODING = "cp" + str(ctypes.cdll.kernel32.GetACP())
else:
    PYTHONIOENCODING = None

POP_THESE = (
    "CONDA_SHLVL",
    "CONDA_DEFAULT_ENV",
    "CONDA_PREFIX",
    "CONDA_PREFIX_0",
    "CONDA_PREFIX_1",
    "CONDA_PREFIX_2",
    "PS1",
    "prompt",
)

ENV_VARS_FILE = """
{
  "version": 1,
  "env_vars": {
    "ENV_ONE": "one",
    "ENV_TWO": "you",
    "ENV_THREE": "me",
    "ENV_WITH_SAME_VALUE": "with_same_value"
  }
}"""

PKG_A_ENV_VARS = """
{
    "PKG_A_ENV": "yerp"
}
"""

PKG_B_ENV_VARS = """
{
    "PKG_B_ENV": "berp"
}
"""

HDF5_VERSION = "1.12.1"


@lru_cache(maxsize=None)
def bash_unsupported_because():
    bash = which("bash")
    reason = ""
    if not bash:
        reason = "bash: was not found on PATH"
    elif on_win:
        try:
            output = check_output(bash + " -c " + '"uname -v"')
        except CalledProcessError as exc:
            reason = f"bash: something went wrong while running bash, output:\n{exc.output}\n"
        else:
            if b"Microsoft" in output:
                reason = "bash: WSL is not yet supported. Pull requests welcome."
            else:
                output = check_output(bash + " --version")
                if b"msys" not in output and b"cygwin" not in output:
                    reason = f"bash: Only MSYS2 and Cygwin bash are supported on Windows, found:\n{output}\n"
                elif bash.startswith(sys.prefix):
                    reason = (
                        f"bash: MSYS2 bash installed from m2-bash in prefix {sys.prefix}.\n"
                        "This is unsupportable due to Git-for-Windows conflicts.\n"
                        "Please use upstream MSYS2 and have it on PATH.  ."
                    )
    return reason


def bash_unsupported():
    return True if bash_unsupported_because() else False


def bash_unsupported_win_because():
    if on_win:
        return (
            "You are using Windows. These tests involve setting PATH to POSIX values\n"
            "but our Python is a Windows program and Windows doesn't understand POSIX values."
        )
    return bash_unsupported_because()


def bash_unsupported_win():
    return True if bash_unsupported_win_because() else False


@pytest.fixture
def reset_environ() -> None:
    # store copy of original environment variables
    original = os.environ.copy()
    for var in POP_THESE:
        os.environ.pop(var, None)

    yield

    # restore original environment variables
    os.environ.clear
    os.environ.update(original)


def write_pkg_env_vars(prefix):
    activate_pkg_env_vars = join(prefix, PACKAGE_ENV_VARS_DIR)
    mkdir_p(activate_pkg_env_vars)
    with open(join(activate_pkg_env_vars, "pkg_a.json"), "w") as f:
        f.write(PKG_A_ENV_VARS)
    with open(join(activate_pkg_env_vars, "pkg_b.json"), "w") as f:
        f.write(PKG_B_ENV_VARS)


def test_activate_environment_not_found(reset_environ: None):
    activator = PosixActivator()

    with tempdir() as td:
        with pytest.raises(EnvironmentLocationNotFound):
            activator.build_activate(td)

    with pytest.raises(EnvironmentLocationNotFound):
        activator.build_activate("/not/an/environment")

    with pytest.raises(EnvironmentNameNotFound):
        activator.build_activate("wontfindmeIdontexist_abc123")


def test_PS1(reset_environ: None):
    with env_var(
        "CONDA_CHANGEPS1", "yes", stack_callback=conda_tests_ctxt_mgmt_def_pol
    ):
        activator = PosixActivator()
        assert (
            activator._prompt_modifier("/dont/matter", ROOT_ENV_NAME)
            == "(%s) " % ROOT_ENV_NAME
        )

        instructions = activator.build_activate("base")
        assert (
            instructions["export_vars"]["CONDA_PROMPT_MODIFIER"]
            == "(%s) " % ROOT_ENV_NAME
        )


def test_PS1_no_changeps1(reset_environ: None):
    with env_var("CONDA_CHANGEPS1", "no", stack_callback=conda_tests_ctxt_mgmt_def_pol):
        activator = PosixActivator()
        assert activator._prompt_modifier("/dont/matter", "root") == ""

        instructions = activator.build_activate("base")
        assert instructions["export_vars"]["CONDA_PROMPT_MODIFIER"] == ""


def test_add_prefix_to_path_posix(reset_environ: None):
    if on_win and "PWD" not in os.environ:
        pytest.skip("This test cannot be run from the cmd.exe shell.")

    activator = PosixActivator()

    path_dirs = activator.path_conversion(
        ["/path1/bin", "/path2/bin", "/usr/local/bin", "/usr/bin", "/bin"]
    )
    assert len(path_dirs) == 5
    test_prefix = "/usr/mytest/prefix"
    added_paths = activator.path_conversion(activator._get_path_dirs(test_prefix))
    if isinstance(added_paths, str):
        added_paths = (added_paths,)

    new_path = activator._add_prefix_to_path(test_prefix, path_dirs)
    condabin_dir = activator.path_conversion(
        os.path.join(context.conda_prefix, "condabin")
    )
    assert new_path == added_paths + (condabin_dir,) + path_dirs


@pytest.mark.skipif(not on_win, reason="windows-specific test")
def test_add_prefix_to_path_cmdexe(reset_environ: None):
    activator = CmdExeActivator()

    path_dirs = activator.path_conversion(
        ["C:\\path1", "C:\\Program Files\\Git\\cmd", "C:\\WINDOWS\\system32"]
    )
    assert len(path_dirs) == 3
    test_prefix = "/usr/mytest/prefix"
    added_paths = activator.path_conversion(activator._get_path_dirs(test_prefix))
    if isinstance(added_paths, str):
        added_paths = (added_paths,)

    new_path = activator._add_prefix_to_path(test_prefix, path_dirs)
    assert new_path[: len(added_paths)] == added_paths
    assert new_path[-len(path_dirs) :] == path_dirs
    assert len(new_path) == len(added_paths) + len(path_dirs) + 1
    assert new_path[len(added_paths)].endswith("condabin")


def test_remove_prefix_from_path_1(reset_environ: None):
    activator = PosixActivator()
    original_path = tuple(activator._get_starting_path_list())
    keep_path = activator.path_conversion("/keep/this/path")
    final_path = (keep_path,) + original_path
    final_path = activator.path_conversion(final_path)

    test_prefix = join(os.getcwd(), "mytestpath")
    new_paths = tuple(activator._get_path_dirs(test_prefix))
    prefix_added_path = (keep_path,) + new_paths + original_path
    new_path = activator._remove_prefix_from_path(test_prefix, prefix_added_path)
    assert final_path == new_path


def test_remove_prefix_from_path_2(reset_environ: None):
    # this time prefix doesn't actually exist in path
    activator = PosixActivator()
    original_path = tuple(activator._get_starting_path_list())
    keep_path = activator.path_conversion("/keep/this/path")
    final_path = (keep_path,) + original_path
    final_path = activator.path_conversion(final_path)

    test_prefix = join(os.getcwd(), "mytestpath")
    prefix_added_path = (keep_path,) + original_path
    new_path = activator._remove_prefix_from_path(test_prefix, prefix_added_path)

    assert final_path == new_path


def test_replace_prefix_in_path_1(reset_environ: None):
    activator = PosixActivator()
    original_path = tuple(activator._get_starting_path_list())
    new_prefix = join(os.getcwd(), "mytestpath-new")
    new_paths = activator.path_conversion(activator._get_path_dirs(new_prefix))
    if isinstance(new_paths, str):
        new_paths = (new_paths,)
    keep_path = activator.path_conversion("/keep/this/path")
    final_path = (keep_path,) + new_paths + original_path
    final_path = activator.path_conversion(final_path)

    replace_prefix = join(os.getcwd(), "mytestpath")
    replace_paths = tuple(activator._get_path_dirs(replace_prefix))
    prefix_added_path = (keep_path,) + replace_paths + original_path
    new_path = activator._replace_prefix_in_path(
        replace_prefix, new_prefix, prefix_added_path
    )

    assert final_path == new_path


@pytest.mark.skipif(not on_win, reason="windows-specific test")
def test_replace_prefix_in_path_2(reset_environ: None):
    path1 = join("c:\\", "temp", "6663 31e0")
    path2 = join("c:\\", "temp", "6663 31e0", "envs", "charizard")
    one_more = join("d:\\", "one", "more")
    #   old_prefix: c:\users\builder\appdata\local\temp\6663 31e0
    #   new_prefix: c:\users\builder\appdata\local\temp\6663 31e0\envs\charizard
    activator = CmdExeActivator()
    old_path = activator.pathsep_join(activator._add_prefix_to_path(path1))
    old_path = one_more + ";" + old_path
    with env_var("PATH", old_path):
        activator = PosixActivator()
        path_elements = activator._replace_prefix_in_path(path1, path2)
    old_path = native_path_to_unix(old_path.split(";"))

    assert path_elements[0] == native_path_to_unix(one_more)
    assert path_elements[1] == native_path_to_unix(
        next(activator._get_path_dirs(path2))
    )
    assert len(path_elements) == len(old_path)


def test_default_env(reset_environ: None):
    activator = PosixActivator()
    assert ROOT_ENV_NAME == activator._default_env(context.root_prefix)

    with tempdir() as td:
        assert td == activator._default_env(td)

        p = mkdir_p(join(td, "envs", "named-env"))
        assert "named-env" == activator._default_env(p)


def test_build_activate_dont_activate_unset_var(reset_environ: None):
    with tempdir() as td:
        mkdir_p(join(td, "conda-meta"))
        activate_d_dir = mkdir_p(join(td, "etc", "conda", "activate.d"))
        activate_d_1 = join(activate_d_dir, "see-me.sh")
        activate_d_2 = join(activate_d_dir, "dont-see-me.bat")
        touch(join(activate_d_1))
        touch(join(activate_d_2))

        env_vars_file = (
            """
        {
          "version": 1,
          "env_vars": {
            "ENV_ONE": "one",
            "ENV_TWO": "you",
            "ENV_THREE": "%s"
          }
        }"""
            % CONDA_ENV_VARS_UNSET_VAR
        )

        activate_env_vars = join(td, PREFIX_STATE_FILE)
        with open(activate_env_vars, "w") as f:
            f.write(env_vars_file)

        write_pkg_env_vars(td)

        with env_var("CONDA_SHLVL", "0"):
            with env_var("CONDA_PREFIX", ""):
                activator = PosixActivator()
                builder = activator.build_activate(td)
                new_path = activator.pathsep_join(activator._add_prefix_to_path(td))
                conda_prompt_modifier = "(%s) " % td
                ps1 = conda_prompt_modifier + os.environ.get("PS1", "")
                unset_vars = []

                set_vars = {"PS1": ps1}
                export_vars = {
                    "PATH": new_path,
                    "CONDA_PREFIX": td,
                    "CONDA_SHLVL": 1,
                    "CONDA_DEFAULT_ENV": td,
                    "CONDA_PROMPT_MODIFIER": conda_prompt_modifier,
                    "PKG_A_ENV": "yerp",
                    "PKG_B_ENV": "berp",
                    "ENV_ONE": "one",
                    "ENV_TWO": "you",
                }
                export_vars, unset_vars = activator.add_export_unset_vars(
                    export_vars, unset_vars
                )
                assert builder["unset_vars"] == unset_vars
                assert builder["set_vars"] == set_vars
                assert builder["export_vars"] == export_vars
                assert builder["activate_scripts"] == (
                    activator.path_conversion(activate_d_1),
                )
                assert builder["deactivate_scripts"] == ()


def test_build_activate_shlvl_warn_clobber_vars(reset_environ: None):
    with tempdir() as td:
        mkdir_p(join(td, "conda-meta"))
        activate_d_dir = mkdir_p(join(td, "etc", "conda", "activate.d"))
        activate_d_1 = join(activate_d_dir, "see-me.sh")
        activate_d_2 = join(activate_d_dir, "dont-see-me.bat")
        touch(join(activate_d_1))
        touch(join(activate_d_2))

        env_vars_file = """
        {
          "version": 1,
          "env_vars": {
            "ENV_ONE": "one",
            "ENV_TWO": "you",
            "ENV_THREE": "me",
            "PKG_A_ENV": "teamnope"
          }
        }"""

        activate_env_vars = join(td, PREFIX_STATE_FILE)
        with open(activate_env_vars, "w") as f:
            f.write(env_vars_file)

        write_pkg_env_vars(td)

        with env_var("CONDA_SHLVL", "0"):
            with env_var("CONDA_PREFIX", ""):
                activator = PosixActivator()
                builder = activator.build_activate(td)
                new_path = activator.pathsep_join(activator._add_prefix_to_path(td))
                conda_prompt_modifier = "(%s) " % td
                ps1 = conda_prompt_modifier + os.environ.get("PS1", "")
                unset_vars = []

                set_vars = {"PS1": ps1}
                export_vars = {
                    "PATH": new_path,
                    "CONDA_PREFIX": td,
                    "CONDA_SHLVL": 1,
                    "CONDA_DEFAULT_ENV": td,
                    "CONDA_PROMPT_MODIFIER": conda_prompt_modifier,
                    "PKG_A_ENV": "teamnope",
                    "PKG_B_ENV": "berp",
                    "ENV_ONE": "one",
                    "ENV_TWO": "you",
                    "ENV_THREE": "me",
                }
                export_vars, unset_vars = activator.add_export_unset_vars(
                    export_vars, unset_vars
                )
                assert builder["unset_vars"] == unset_vars
                assert builder["set_vars"] == set_vars
                assert builder["export_vars"] == export_vars
                assert builder["activate_scripts"] == (
                    activator.path_conversion(activate_d_1),
                )
                assert builder["deactivate_scripts"] == ()


def test_build_activate_shlvl_0(reset_environ: None):
    with tempdir() as td:
        mkdir_p(join(td, "conda-meta"))
        activate_d_dir = mkdir_p(join(td, "etc", "conda", "activate.d"))
        activate_d_1 = join(activate_d_dir, "see-me.sh")
        activate_d_2 = join(activate_d_dir, "dont-see-me.bat")
        touch(join(activate_d_1))
        touch(join(activate_d_2))

        activate_env_vars = join(td, PREFIX_STATE_FILE)
        with open(activate_env_vars, "w") as f:
            f.write(ENV_VARS_FILE)

        write_pkg_env_vars(td)

        with env_var("CONDA_SHLVL", "0"):
            with env_var("CONDA_PREFIX", ""):
                activator = PosixActivator()
                builder = activator.build_activate(td)
                new_path = activator.pathsep_join(activator._add_prefix_to_path(td))
                conda_prompt_modifier = "(%s) " % td
                ps1 = conda_prompt_modifier + os.environ.get("PS1", "")
                unset_vars = []

                set_vars = {"PS1": ps1}
                export_vars = {
                    "PATH": new_path,
                    "CONDA_PREFIX": td,
                    "CONDA_SHLVL": 1,
                    "CONDA_DEFAULT_ENV": td,
                    "CONDA_PROMPT_MODIFIER": conda_prompt_modifier,
                    "PKG_A_ENV": "yerp",
                    "PKG_B_ENV": "berp",
                    "ENV_ONE": "one",
                    "ENV_TWO": "you",
                    "ENV_THREE": "me",
                    "ENV_WITH_SAME_VALUE": "with_same_value",
                }
                export_vars, unset_vars = activator.add_export_unset_vars(
                    export_vars, unset_vars
                )
                assert builder["unset_vars"] == unset_vars
                assert builder["set_vars"] == set_vars
                assert builder["export_vars"] == export_vars
                assert builder["activate_scripts"] == (
                    activator.path_conversion(activate_d_1),
                )
                assert builder["deactivate_scripts"] == ()


@pytest.mark.skipif(bash_unsupported_win(), reason=bash_unsupported_win_because())
def test_build_activate_shlvl_1(reset_environ: None):
    with tempdir() as td:
        mkdir_p(join(td, "conda-meta"))
        activate_d_dir = mkdir_p(join(td, "etc", "conda", "activate.d"))
        activate_d_1 = join(activate_d_dir, "see-me.sh")
        activate_d_2 = join(activate_d_dir, "dont-see-me.bat")
        touch(join(activate_d_1))
        touch(join(activate_d_2))

        activate_env_vars = join(td, PREFIX_STATE_FILE)
        with open(activate_env_vars, "w") as f:
            f.write(ENV_VARS_FILE)

        write_pkg_env_vars(td)

        old_prefix = "/old/prefix"
        activator = PosixActivator()
        old_path = activator.pathsep_join(activator._add_prefix_to_path(old_prefix))

        with env_vars(
            {
                "CONDA_SHLVL": "1",
                "CONDA_PREFIX": old_prefix,
                "PATH": old_path,
                "CONDA_ENV_PROMPT": "({default_env})",
            },
            stack_callback=conda_tests_ctxt_mgmt_def_pol,
        ):
            activator = PosixActivator()
            builder = activator.build_activate(td)
            new_path = activator.pathsep_join(
                activator._replace_prefix_in_path(old_prefix, td)
            )
            conda_prompt_modifier = "(%s)" % td
            ps1 = conda_prompt_modifier + os.environ.get("PS1", "")

            assert activator.path_conversion(td) in new_path
            assert old_prefix not in new_path

            unset_vars = []

            set_vars = {"PS1": ps1}
            export_vars = {
                "PATH": new_path,
                "CONDA_PREFIX": td,
                "CONDA_SHLVL": 2,
                "CONDA_DEFAULT_ENV": td,
                "CONDA_PROMPT_MODIFIER": conda_prompt_modifier,
                "PKG_A_ENV": "yerp",
                "PKG_B_ENV": "berp",
                "ENV_ONE": "one",
                "ENV_TWO": "you",
                "ENV_THREE": "me",
                "ENV_WITH_SAME_VALUE": "with_same_value",
            }
            export_vars, _ = activator.add_export_unset_vars(export_vars, None)
            export_vars["CONDA_PREFIX_1"] = old_prefix
            export_vars, unset_vars = activator.add_export_unset_vars(
                export_vars, unset_vars
            )

            assert builder["unset_vars"] == unset_vars
            assert builder["set_vars"] == set_vars
            assert builder["export_vars"] == export_vars
            assert builder["activate_scripts"] == (
                activator.path_conversion(activate_d_1),
            )
            assert builder["deactivate_scripts"] == ()

            with env_vars(
                {
                    "PATH": new_path,
                    "CONDA_PREFIX": td,
                    "CONDA_PREFIX_1": old_prefix,
                    "CONDA_SHLVL": 2,
                    "CONDA_DEFAULT_ENV": td,
                    "CONDA_PROMPT_MODIFIER": conda_prompt_modifier,
                    "PKG_B_ENV": "berp",
                    "PKG_A_ENV": "yerp",
                    "ENV_ONE": "one",
                    "ENV_TWO": "you",
                    "ENV_THREE": "me",
                    "ENV_WITH_SAME_VALUE": "with_same_value",
                }
            ):
                activator = PosixActivator()
                builder = activator.build_deactivate()

                unset_vars = [
                    "CONDA_PREFIX_1",
                    "PKG_A_ENV",
                    "PKG_B_ENV",
                    "ENV_ONE",
                    "ENV_TWO",
                    "ENV_THREE",
                    "ENV_WITH_SAME_VALUE",
                ]
                assert builder["set_vars"] == {
                    "PS1": "(/old/prefix)",
                }
                export_vars = {
                    "CONDA_PREFIX": old_prefix,
                    "CONDA_SHLVL": 1,
                    "CONDA_DEFAULT_ENV": old_prefix,
                    "CONDA_PROMPT_MODIFIER": "(%s)" % old_prefix,
                }
                export_path = {
                    "PATH": old_path,
                }
                export_vars, unset_vars = activator.add_export_unset_vars(
                    export_vars, unset_vars
                )
                assert builder["unset_vars"] == unset_vars
                assert builder["export_vars"] == export_vars
                assert builder["export_path"] == export_path
                assert builder["activate_scripts"] == ()
                assert builder["deactivate_scripts"] == ()


@pytest.mark.skipif(bash_unsupported_win(), reason=bash_unsupported_win_because())
def test_build_stack_shlvl_1(reset_environ: None):
    with tempdir() as td:
        mkdir_p(join(td, "conda-meta"))
        activate_d_dir = mkdir_p(join(td, "etc", "conda", "activate.d"))
        activate_d_1 = join(activate_d_dir, "see-me.sh")
        activate_d_2 = join(activate_d_dir, "dont-see-me.bat")
        touch(join(activate_d_1))
        touch(join(activate_d_2))

        activate_env_vars = join(td, PREFIX_STATE_FILE)
        with open(activate_env_vars, "w") as f:
            f.write(ENV_VARS_FILE)

        write_pkg_env_vars(td)

        old_prefix = "/old/prefix"
        activator = PosixActivator()
        old_path = activator.pathsep_join(activator._add_prefix_to_path(old_prefix))

        with env_vars(
            {
                "CONDA_SHLVL": "1",
                "CONDA_PREFIX": old_prefix,
                "PATH": old_path,
                "CONDA_ENV_PROMPT": "({default_env})",
            },
            stack_callback=conda_tests_ctxt_mgmt_def_pol,
        ):
            activator = PosixActivator()
            builder = activator.build_stack(td)
            new_path = activator.pathsep_join(activator._add_prefix_to_path(td))
            conda_prompt_modifier = "(%s)" % td
            ps1 = conda_prompt_modifier + os.environ.get("PS1", "")

            assert td in new_path
            assert old_prefix in new_path

            set_vars = {"PS1": ps1}
            export_vars = {
                "PATH": new_path,
                "CONDA_PREFIX": td,
                "CONDA_SHLVL": 2,
                "CONDA_DEFAULT_ENV": td,
                "CONDA_PROMPT_MODIFIER": conda_prompt_modifier,
                "PKG_A_ENV": "yerp",
                "PKG_B_ENV": "berp",
                "ENV_ONE": "one",
                "ENV_TWO": "you",
                "ENV_THREE": "me",
                "ENV_WITH_SAME_VALUE": "with_same_value",
            }
            export_vars, unset_vars = activator.add_export_unset_vars(export_vars, [])
            export_vars["CONDA_PREFIX_1"] = old_prefix
            export_vars["CONDA_STACKED_2"] = "true"

            assert builder["unset_vars"] == unset_vars
            assert builder["set_vars"] == set_vars
            assert builder["export_vars"] == export_vars
            assert builder["activate_scripts"] == (
                activator.path_conversion(activate_d_1),
            )
            assert builder["deactivate_scripts"] == ()

            with env_vars(
                {
                    "PATH": new_path,
                    "CONDA_PREFIX": td,
                    "CONDA_PREFIX_1": old_prefix,
                    "CONDA_SHLVL": 2,
                    "CONDA_DEFAULT_ENV": td,
                    "CONDA_PROMPT_MODIFIER": conda_prompt_modifier,
                    "CONDA_STACKED_2": "true",
                    "PKG_A_ENV": "yerp",
                    "PKG_B_ENV": "berp",
                    "ENV_ONE": "one",
                    "ENV_TWO": "you",
                    "ENV_THREE": "me",
                }
            ):
                activator = PosixActivator()
                builder = activator.build_deactivate()

                unset_vars = [
                    "CONDA_PREFIX_1",
                    "CONDA_STACKED_2",
                    "PKG_A_ENV",
                    "PKG_B_ENV",
                    "ENV_ONE",
                    "ENV_TWO",
                    "ENV_THREE",
                    "ENV_WITH_SAME_VALUE",
                ]
                assert builder["set_vars"] == {
                    "PS1": "(/old/prefix)",
                }
                export_vars = {
                    "CONDA_PREFIX": old_prefix,
                    "CONDA_SHLVL": 1,
                    "CONDA_DEFAULT_ENV": old_prefix,
                    "CONDA_PROMPT_MODIFIER": f"({old_prefix})",
                }
                export_vars, unset_vars = activator.add_export_unset_vars(
                    export_vars, unset_vars
                )
                assert builder["unset_vars"] == unset_vars
                assert builder["export_vars"] == export_vars
                assert builder["activate_scripts"] == ()
                assert builder["deactivate_scripts"] == ()


def test_activate_same_environment(reset_environ: None):
    with tempdir() as td:
        mkdir_p(join(td, "conda-meta"))
        activate_d_dir = mkdir_p(join(td, "etc", "conda", "activate.d"))
        activate_d_1 = join(activate_d_dir, "see-me.sh")
        activate_d_2 = join(activate_d_dir, "dont-see-me.bat")
        touch(join(activate_d_1))
        touch(join(activate_d_2))

        old_prefix = td
        deactivate_d_dir = mkdir_p(join(old_prefix, "etc", "conda", "deactivate.d"))
        deactivate_d_1 = join(deactivate_d_dir, "see-me.sh")
        deactivate_d_2 = join(deactivate_d_dir, "dont-see-me.bat")
        touch(join(deactivate_d_1))
        touch(join(deactivate_d_2))

        with env_var("CONDA_SHLVL", "1"):
            with env_var("CONDA_PREFIX", old_prefix):
                activator = PosixActivator()

                builder = activator.build_activate(td)

                new_path_parts = activator._replace_prefix_in_path(
                    old_prefix, old_prefix
                )
                conda_prompt_modifier = "(%s) " % old_prefix
                ps1 = conda_prompt_modifier + os.environ.get("PS1", "")

                set_vars = {"PS1": ps1}
                export_vars = {
                    "PATH": activator.pathsep_join(new_path_parts),
                    "CONDA_SHLVL": 1,
                    "CONDA_PROMPT_MODIFIER": "(%s) " % td,
                }
                assert builder["unset_vars"] == ()
                assert builder["set_vars"] == set_vars
                assert builder["export_vars"] == export_vars
                assert builder["activate_scripts"] == (
                    activator.path_conversion(activate_d_1),
                )
                assert builder["deactivate_scripts"] == (
                    activator.path_conversion(deactivate_d_1),
                )


@pytest.mark.skipif(bash_unsupported_win(), reason=bash_unsupported_win_because())
def test_build_deactivate_shlvl_2_from_stack(reset_environ: None):
    with tempdir() as td:
        mkdir_p(join(td, "conda-meta"))
        deactivate_d_dir = mkdir_p(join(td, "etc", "conda", "deactivate.d"))
        deactivate_d_1 = join(deactivate_d_dir, "see-me-deactivate.sh")
        deactivate_d_2 = join(deactivate_d_dir, "dont-see-me.bat")
        touch(join(deactivate_d_1))
        touch(join(deactivate_d_2))

        activate_env_vars = join(td, PREFIX_STATE_FILE)
        with open(activate_env_vars, "w") as f:
            f.write(ENV_VARS_FILE)

        activate_pkg_env_vars_a = join(td, PACKAGE_ENV_VARS_DIR)
        mkdir_p(activate_pkg_env_vars_a)
        with open(join(activate_pkg_env_vars_a, "pkg_a.json"), "w") as f:
            f.write(PKG_A_ENV_VARS)

        old_prefix = join(td, "old")
        mkdir_p(join(old_prefix, "conda-meta"))
        activate_d_dir = mkdir_p(join(old_prefix, "etc", "conda", "activate.d"))
        activate_d_1 = join(activate_d_dir, "see-me-activate.sh")
        activate_d_2 = join(activate_d_dir, "dont-see-me.bat")
        touch(join(activate_d_1))
        touch(join(activate_d_2))

        activate_env_vars_old = join(old_prefix, PREFIX_STATE_FILE)
        with open(activate_env_vars_old, "w") as f:
            f.write(
                """
                {
                  "version": 1,
                  "env_vars": {
                    "ENV_FOUR": "roar",
                    "ENV_FIVE": "hive"
                  }
                }
            """
            )
        activate_pkg_env_vars_b = join(old_prefix, PACKAGE_ENV_VARS_DIR)
        mkdir_p(activate_pkg_env_vars_b)
        with open(join(activate_pkg_env_vars_b, "pkg_b.json"), "w") as f:
            f.write(PKG_B_ENV_VARS)

        activator = PosixActivator()
        original_path = activator.pathsep_join(
            activator._add_prefix_to_path(old_prefix)
        )
        with env_var("PATH", original_path):
            activator = PosixActivator()
            starting_path = activator.pathsep_join(activator._add_prefix_to_path(td))

            with env_vars(
                {
                    "CONDA_SHLVL": "2",
                    "CONDA_PREFIX_1": old_prefix,
                    "CONDA_PREFIX": td,
                    "CONDA_STACKED_2": "true",
                    "PATH": starting_path,
                    "ENV_ONE": "one",
                    "ENV_TWO": "you",
                    "ENV_THREE": "me",
                    "ENV_FOUR": "roar",
                    "ENV_FIVE": "hive",
                    "PKG_A_ENV": "yerp",
                    "PKG_B_ENV": "berp",
                },
                stack_callback=conda_tests_ctxt_mgmt_def_pol,
            ):
                activator = PosixActivator()
                builder = activator.build_deactivate()

                unset_vars = [
                    "CONDA_PREFIX_1",
                    "CONDA_STACKED_2",
                    "PKG_A_ENV",
                    "ENV_ONE",
                    "ENV_TWO",
                    "ENV_THREE",
                    "ENV_WITH_SAME_VALUE",
                ]

                conda_prompt_modifier = "(%s) " % old_prefix
                ps1 = conda_prompt_modifier + os.environ.get("PS1", "")

                set_vars = {"PS1": ps1}
                export_vars = {
                    "CONDA_PREFIX": old_prefix,
                    "CONDA_SHLVL": 1,
                    "CONDA_DEFAULT_ENV": old_prefix,
                    "CONDA_PROMPT_MODIFIER": conda_prompt_modifier,
                    "PKG_B_ENV": "berp",
                    "ENV_FOUR": "roar",
                    "ENV_FIVE": "hive",
                }
                export_path = {
                    "PATH": original_path,
                }
                export_vars, unset_vars = activator.add_export_unset_vars(
                    export_vars, unset_vars
                )
                assert builder["unset_vars"] == unset_vars
                assert builder["set_vars"] == set_vars
                assert builder["export_vars"] == export_vars
                assert builder["export_path"] == export_path
                assert builder["activate_scripts"] == (
                    activator.path_conversion(activate_d_1),
                )
                assert builder["deactivate_scripts"] == (
                    activator.path_conversion(deactivate_d_1),
                )


@pytest.mark.skipif(bash_unsupported_win(), reason=bash_unsupported_win_because())
def test_build_deactivate_shlvl_2_from_activate(reset_environ: None):
    with tempdir() as td:
        mkdir_p(join(td, "conda-meta"))
        deactivate_d_dir = mkdir_p(join(td, "etc", "conda", "deactivate.d"))
        deactivate_d_1 = join(deactivate_d_dir, "see-me-deactivate.sh")
        deactivate_d_2 = join(deactivate_d_dir, "dont-see-me.bat")
        touch(join(deactivate_d_1))
        touch(join(deactivate_d_2))

        activate_env_vars = join(td, PREFIX_STATE_FILE)
        with open(activate_env_vars, "w") as f:
            f.write(ENV_VARS_FILE)

        activate_pkg_env_vars_a = join(td, PACKAGE_ENV_VARS_DIR)
        mkdir_p(activate_pkg_env_vars_a)
        with open(join(activate_pkg_env_vars_a, "pkg_a.json"), "w") as f:
            f.write(PKG_A_ENV_VARS)

        old_prefix = join(td, "old")
        mkdir_p(join(old_prefix, "conda-meta"))
        activate_d_dir = mkdir_p(join(old_prefix, "etc", "conda", "activate.d"))
        activate_d_1 = join(activate_d_dir, "see-me-activate.sh")
        activate_d_2 = join(activate_d_dir, "dont-see-me.bat")
        touch(join(activate_d_1))
        touch(join(activate_d_2))

        activate_env_vars_old = join(old_prefix, PREFIX_STATE_FILE)
        with open(activate_env_vars_old, "w") as f:
            f.write(
                """
               {
                 "version": 1,
                 "env_vars": {
                   "ENV_FOUR": "roar",
                   "ENV_FIVE": "hive"
                 }
               }
           """
            )
        activate_pkg_env_vars_b = join(old_prefix, PACKAGE_ENV_VARS_DIR)
        mkdir_p(activate_pkg_env_vars_b)
        with open(join(activate_pkg_env_vars_b, "pkg_b.json"), "w") as f:
            f.write(PKG_B_ENV_VARS)

        activator = PosixActivator()
        original_path = activator.pathsep_join(
            activator._add_prefix_to_path(old_prefix)
        )
        new_path = activator.pathsep_join(activator._add_prefix_to_path(td))
        with env_vars(
            {
                "CONDA_SHLVL": "2",
                "CONDA_PREFIX_1": old_prefix,
                "CONDA_PREFIX": td,
                "PATH": new_path,
                "ENV_ONE": "one",
                "ENV_TWO": "you",
                "ENV_THREE": "me",
                "PKG_A_ENV": "yerp",
                "PKG_B_ENV": "berp",
            },
            stack_callback=conda_tests_ctxt_mgmt_def_pol,
        ):
            activator = PosixActivator()
            builder = activator.build_deactivate()

            unset_vars = [
                "CONDA_PREFIX_1",
                "PKG_A_ENV",
                "ENV_ONE",
                "ENV_TWO",
                "ENV_THREE",
                "ENV_WITH_SAME_VALUE",
            ]

            conda_prompt_modifier = "(%s) " % old_prefix
            ps1 = conda_prompt_modifier + os.environ.get("PS1", "")

            set_vars = {"PS1": ps1}
            export_vars = {
                "CONDA_PREFIX": old_prefix,
                "CONDA_SHLVL": 1,
                "CONDA_DEFAULT_ENV": old_prefix,
                "CONDA_PROMPT_MODIFIER": conda_prompt_modifier,
                "PKG_B_ENV": "berp",
                "ENV_FOUR": "roar",
                "ENV_FIVE": "hive",
            }
            export_path = {
                "PATH": original_path,
            }
            export_vars, unset_vars = activator.add_export_unset_vars(
                export_vars, unset_vars
            )

            assert builder["unset_vars"] == unset_vars
            assert builder["set_vars"] == set_vars
            assert builder["export_vars"] == export_vars
            assert builder["export_path"] == export_path
            assert builder["activate_scripts"] == (
                activator.path_conversion(activate_d_1),
            )
            assert builder["deactivate_scripts"] == (
                activator.path_conversion(deactivate_d_1),
            )


def test_build_deactivate_shlvl_1(reset_environ: None):
    with tempdir() as td:
        mkdir_p(join(td, "conda-meta"))
        deactivate_d_dir = mkdir_p(join(td, "etc", "conda", "deactivate.d"))
        deactivate_d_1 = join(deactivate_d_dir, "see-me-deactivate.sh")
        deactivate_d_2 = join(deactivate_d_dir, "dont-see-me.bat")
        touch(join(deactivate_d_1))
        touch(join(deactivate_d_2))

        activate_env_vars = join(td, PREFIX_STATE_FILE)
        with open(activate_env_vars, "w") as f:
            f.write(ENV_VARS_FILE)

        write_pkg_env_vars(td)

        with env_var("CONDA_SHLVL", "1"):
            with env_var("CONDA_PREFIX", td):
                activator = PosixActivator()
                original_path = tuple(activator._get_starting_path_list())
                builder = activator.build_deactivate()

                new_path = activator.pathsep_join(
                    activator.path_conversion(original_path)
                )
                export_vars, unset_vars = activator.add_export_unset_vars(
                    {"CONDA_SHLVL": 0},
                    [
                        "CONDA_PREFIX",
                        "CONDA_DEFAULT_ENV",
                        "CONDA_PROMPT_MODIFIER",
                        "PKG_A_ENV",
                        "PKG_B_ENV",
                        "ENV_ONE",
                        "ENV_TWO",
                        "ENV_THREE",
                        "ENV_WITH_SAME_VALUE",
                    ],
                )
                assert builder["set_vars"] == {"PS1": os.environ.get("PS1", "")}
                assert builder["export_vars"] == export_vars
                assert builder["unset_vars"] == unset_vars
                assert builder["export_path"] == {"PATH": new_path}
                assert builder["activate_scripts"] == ()
                assert builder["deactivate_scripts"] == (
                    activator.path_conversion(deactivate_d_1),
                )


def test_get_env_vars_big_whitespace(reset_environ: None):
    with tempdir() as td:
        STATE_FILE = join(td, PREFIX_STATE_FILE)
        mkdir_p(dirname(STATE_FILE))
        with open(STATE_FILE, "w") as f:
            f.write(
                """
                {
                  "version": 1,
                  "env_vars": {
                    "ENV_ONE": "one",
                    "ENV_TWO": "you",
                    "ENV_THREE": "me"
                  }}"""
            )
        activator = PosixActivator()
        env_vars = activator._get_environment_env_vars(td)
        assert env_vars == {"ENV_ONE": "one", "ENV_TWO": "you", "ENV_THREE": "me"}


def test_get_env_vars_empty_file(reset_environ: None):
    with tempdir() as td:
        env_var_parent_dir = join(td, "conda-meta")
        mkdir_p(env_var_parent_dir)
        activate_env_vars = join(env_var_parent_dir, "env_vars")
        with open(activate_env_vars, "w") as f:
            f.write(
                """
            """
            )
        activator = PosixActivator()
        env_vars = activator._get_environment_env_vars(td)
        assert env_vars == {}


@pytest.mark.skipif(bash_unsupported_win(), reason=bash_unsupported_win_because())
def test_build_activate_restore_unset_env_vars(reset_environ: None):
    with tempdir() as td:
        mkdir_p(join(td, "conda-meta"))
        activate_d_dir = mkdir_p(join(td, "etc", "conda", "activate.d"))
        activate_d_1 = join(activate_d_dir, "see-me.sh")
        activate_d_2 = join(activate_d_dir, "dont-see-me.bat")
        touch(join(activate_d_1))
        touch(join(activate_d_2))

        activate_env_vars = join(td, PREFIX_STATE_FILE)
        with open(activate_env_vars, "w") as f:
            f.write(ENV_VARS_FILE)

        write_pkg_env_vars(td)

        old_prefix = "/old/prefix"
        activator = PosixActivator()
        old_path = activator.pathsep_join(activator._add_prefix_to_path(old_prefix))

        with env_vars(
            {
                "CONDA_SHLVL": "1",
                "CONDA_PREFIX": old_prefix,
                "PATH": old_path,
                "CONDA_ENV_PROMPT": "({default_env})",
                "ENV_ONE": "already_set_env_var",
                "ENV_WITH_SAME_VALUE": "with_same_value",
            },
            stack_callback=conda_tests_ctxt_mgmt_def_pol,
        ):
            activator = PosixActivator()
            builder = activator.build_activate(td)
            new_path = activator.pathsep_join(
                activator._replace_prefix_in_path(old_prefix, td)
            )
            conda_prompt_modifier = "(%s)" % td
            ps1 = conda_prompt_modifier + os.environ.get("PS1", "")

            assert activator.path_conversion(td) in new_path
            assert old_prefix not in new_path

            unset_vars = []

            set_vars = {"PS1": ps1}
            export_vars = {
                "PATH": new_path,
                "CONDA_PREFIX": td,
                "CONDA_SHLVL": 2,
                "CONDA_DEFAULT_ENV": td,
                "CONDA_PROMPT_MODIFIER": conda_prompt_modifier,
                "PKG_A_ENV": "yerp",
                "PKG_B_ENV": "berp",
                "ENV_ONE": "one",
                "ENV_TWO": "you",
                "ENV_THREE": "me",
                "ENV_WITH_SAME_VALUE": "with_same_value",
                "__CONDA_SHLVL_1_ENV_ONE": "already_set_env_var",
                "__CONDA_SHLVL_1_ENV_WITH_SAME_VALUE": "with_same_value",
            }
            export_vars, _ = activator.add_export_unset_vars(export_vars, None)
            export_vars["CONDA_PREFIX_1"] = old_prefix
            export_vars, unset_vars = activator.add_export_unset_vars(
                export_vars, unset_vars
            )

            assert builder["unset_vars"] == unset_vars
            assert builder["set_vars"] == set_vars
            assert builder["export_vars"] == export_vars
            assert builder["activate_scripts"] == (
                activator.path_conversion(activate_d_1),
            )
            assert builder["deactivate_scripts"] == ()

            with env_vars(
                {
                    "PATH": new_path,
                    "CONDA_PREFIX": td,
                    "CONDA_PREFIX_1": old_prefix,
                    "CONDA_SHLVL": 2,
                    "CONDA_DEFAULT_ENV": td,
                    "CONDA_PROMPT_MODIFIER": conda_prompt_modifier,
                    "__CONDA_SHLVL_1_ENV_ONE": "already_set_env_var",
                    "PKG_B_ENV": "berp",
                    "PKG_A_ENV": "yerp",
                    "ENV_ONE": "one",
                    "ENV_TWO": "you",
                    "ENV_THREE": "me",
                    "ENV_WITH_SAME_VALUE": "with_same_value",
                }
            ):
                activator = PosixActivator()
                builder = activator.build_deactivate()

                unset_vars = [
                    "CONDA_PREFIX_1",
                    "PKG_A_ENV",
                    "PKG_B_ENV",
                    "ENV_ONE",
                    "ENV_TWO",
                    "ENV_THREE",
                    "ENV_WITH_SAME_VALUE",
                ]
                assert builder["set_vars"] == {
                    "PS1": "(/old/prefix)",
                }
                export_vars = {
                    "CONDA_PREFIX": old_prefix,
                    "CONDA_SHLVL": 1,
                    "CONDA_DEFAULT_ENV": old_prefix,
                    "CONDA_PROMPT_MODIFIER": f"({old_prefix})",
                }
                export_path = {
                    "PATH": old_path,
                }
                export_vars, unset_vars = activator.add_export_unset_vars(
                    export_vars, unset_vars
                )
                export_vars["ENV_ONE"] = "already_set_env_var"
                assert builder["unset_vars"] == unset_vars
                assert builder["export_vars"] == export_vars
                assert builder["export_path"] == export_path
                assert builder["activate_scripts"] == ()
                assert builder["deactivate_scripts"] == ()


@pytest.fixture
def shell_wrapper_unit(reset_environ: None, path_factory: PathFactoryFixture) -> str:
    prefix = path_factory()
    history = prefix / "conda-meta" / "history"
    history.parent.mkdir(parents=True, exist_ok=True)
    history.touch()

    yield str(prefix)


def make_dot_d_files(prefix, extension):
    mkdir_p(join(prefix, "etc", "conda", "activate.d"))
    mkdir_p(join(prefix, "etc", "conda", "deactivate.d"))

    touch(join(prefix, "etc", "conda", "activate.d", "ignore.txt"))
    touch(join(prefix, "etc", "conda", "deactivate.d", "ignore.txt"))

    touch(join(prefix, "etc", "conda", "activate.d", f"activate1{extension}"))
    touch(join(prefix, "etc", "conda", "deactivate.d", f"deactivate1{extension}"))


@pytest.mark.parametrize(
    "paths",
    [
        pytest.param(None, id="None"),
        pytest.param("", id="empty string"),
        pytest.param((), id="empty tuple"),
        pytest.param("path/number/one", id="single path"),
        pytest.param(["path/number/one"], id="list with path"),
        pytest.param(("path/number/one", "path/two", "three"), id="tuple with paths"),
    ],
)
def test_native_path_to_unix(tmp_path: Path, paths: str | Iterable[str] | None):
    def assert_unix_path(path):
        return "\\" not in path and ":" not in path

    # convert all path stubs to full paths (localized to current OS)
    if not paths:
        pass
    elif isinstance(paths, str):
        paths = str(tmp_path / paths)
    else:
        paths = tuple(str(tmp_path / path) for path in paths)

    # test that we receive a unix path
    if isinstance(paths, str) and not paths:
        assert native_path_to_unix(paths) == "."
    elif not on_win:
        assert native_path_to_unix(paths) == paths
    elif paths is None:
        assert native_path_to_unix(paths) is None
    elif isinstance(paths, str):
        assert assert_unix_path(native_path_to_unix(paths))
    else:
        assert all(assert_unix_path(path) for path in native_path_to_unix(paths))


def test_posix_basic(shell_wrapper_unit: str):
    activator = PosixActivator()
    make_dot_d_files(shell_wrapper_unit, activator.script_extension)

    with captured() as c:
        rc = main_sourced("shell.posix", *activate_args, shell_wrapper_unit)
    assert not c.stderr
    assert rc == 0
    activate_data = c.stdout

    new_path_parts = activator._add_prefix_to_path(shell_wrapper_unit)
    conda_exe_export, conda_exe_unset = activator.get_scripts_export_unset_vars()

    e_activate_data = (
        dals(
            """
    PS1='%(ps1)s'
    %(conda_exe_unset)s
    export PATH='%(new_path)s'
    export CONDA_PREFIX='%(native_prefix)s'
    export CONDA_SHLVL='1'
    export CONDA_DEFAULT_ENV='%(native_prefix)s'
    export CONDA_PROMPT_MODIFIER='(%(native_prefix)s) '
    %(conda_exe_export)s
    . "%(activate1)s"
    """
        )
        % {
            "native_prefix": shell_wrapper_unit,
            "new_path": activator.pathsep_join(new_path_parts),
            "sys_executable": activator.path_conversion(sys.executable),
            "activate1": activator.path_conversion(
                join(shell_wrapper_unit, "etc", "conda", "activate.d", "activate1.sh")
            ),
            "ps1": "(%s) " % shell_wrapper_unit + os.environ.get("PS1", ""),
            "conda_exe_unset": conda_exe_unset,
            "conda_exe_export": conda_exe_export,
        }
    )
    import re

    assert activate_data == re.sub(r"\n\n+", "\n", e_activate_data)

    with env_vars(
        {
            "CONDA_PREFIX": shell_wrapper_unit,
            "CONDA_SHLVL": "1",
            "PATH": os.pathsep.join((*new_path_parts, os.environ["PATH"])),
        }
    ):
        activator = PosixActivator()
        with captured() as c:
            rc = main_sourced("shell.posix", *reactivate_args)
        assert not c.stderr
        assert rc == 0
        reactivate_data = c.stdout

        new_path_parts = activator._replace_prefix_in_path(
            shell_wrapper_unit, shell_wrapper_unit
        )
        e_reactivate_data = (
            dals(
                """
        . "%(deactivate1)s"
        PS1='%(ps1)s'
        export PATH='%(new_path)s'
        export CONDA_SHLVL='1'
        export CONDA_PROMPT_MODIFIER='(%(native_prefix)s) '
        . "%(activate1)s"
        """
            )
            % {
                "activate1": activator.path_conversion(
                    join(
                        shell_wrapper_unit, "etc", "conda", "activate.d", "activate1.sh"
                    )
                ),
                "deactivate1": activator.path_conversion(
                    join(
                        shell_wrapper_unit,
                        "etc",
                        "conda",
                        "deactivate.d",
                        "deactivate1.sh",
                    )
                ),
                "native_prefix": shell_wrapper_unit,
                "new_path": activator.pathsep_join(new_path_parts),
                "ps1": "(%s) " % shell_wrapper_unit + os.environ.get("PS1", ""),
            }
        )
        assert reactivate_data == re.sub(r"\n\n+", "\n", e_reactivate_data)

        with captured() as c:
            rc = main_sourced("shell.posix", *deactivate_args)
        assert not c.stderr
        assert rc == 0
        deactivate_data = c.stdout

        new_path = activator.pathsep_join(
            activator._remove_prefix_from_path(shell_wrapper_unit)
        )
        (
            conda_exe_export,
            conda_exe_unset,
        ) = activator.get_scripts_export_unset_vars()

        e_deactivate_data = (
            dals(
                """
        export PATH='%(new_path)s'
        . "%(deactivate1)s"
        %(conda_exe_unset)s
        unset CONDA_PREFIX
        unset CONDA_DEFAULT_ENV
        unset CONDA_PROMPT_MODIFIER
        PS1='%(ps1)s'
        export CONDA_SHLVL='0'
        %(conda_exe_export)s
        """
            )
            % {
                "new_path": new_path,
                "deactivate1": activator.path_conversion(
                    join(
                        shell_wrapper_unit,
                        "etc",
                        "conda",
                        "deactivate.d",
                        "deactivate1.sh",
                    )
                ),
                "ps1": os.environ.get("PS1", ""),
                "conda_exe_unset": conda_exe_unset,
                "conda_exe_export": conda_exe_export,
            }
        )
        assert deactivate_data == re.sub(r"\n\n+", "\n", e_deactivate_data)


@pytest.mark.skipif(not on_win, reason="cmd.exe only on Windows")
def test_cmd_exe_basic(shell_wrapper_unit: str):
    # NOTE :: We do not want dev mode here.
    context.dev = False
    activator = CmdExeActivator()
    make_dot_d_files(shell_wrapper_unit, activator.script_extension)

    with captured() as c:
        rc = main_sourced("shell.cmd.exe", "activate", shell_wrapper_unit)
    assert not c.stderr
    assert rc == 0
    activate_result = c.stdout

    with open(activate_result) as fh:
        activate_data = fh.read()
    rm_rf(activate_result)

    new_path_parts = activator._add_prefix_to_path(shell_wrapper_unit)
    conda_exe_export, conda_exe_unset = activator.get_scripts_export_unset_vars()

    e_activate_data = (
        dals(
            """
    @SET "PATH=%(new_path)s"
    @SET "CONDA_PREFIX=%(converted_prefix)s"
    @SET "CONDA_SHLVL=1"
    @SET "CONDA_DEFAULT_ENV=%(native_prefix)s"
    @SET "CONDA_PROMPT_MODIFIER=(%(native_prefix)s) "
    %(conda_exe_export)s
    @CALL "%(activate1)s"
    """
        )
        % {
            "converted_prefix": activator.path_conversion(shell_wrapper_unit),
            "native_prefix": shell_wrapper_unit,
            "new_path": activator.pathsep_join(new_path_parts),
            "sys_executable": activator.path_conversion(sys.executable),
            "activate1": activator.path_conversion(
                join(shell_wrapper_unit, "etc", "conda", "activate.d", "activate1.bat")
            ),
            "conda_exe_export": conda_exe_export,
        }
    )
    assert activate_data == e_activate_data

    with env_vars(
        {
            "CONDA_PREFIX": shell_wrapper_unit,
            "CONDA_SHLVL": "1",
            "PATH": os.pathsep.join((*new_path_parts, os.environ["PATH"])),
        }
    ):
        activator = CmdExeActivator()
        with captured() as c:
            assert main_sourced("shell.cmd.exe", "reactivate") == 0
        assert not c.stderr
        reactivate_result = c.stdout

        with open(reactivate_result) as fh:
            reactivate_data = fh.read()
        rm_rf(reactivate_result)

        new_path_parts = activator._replace_prefix_in_path(
            shell_wrapper_unit, shell_wrapper_unit
        )
        assert (
            reactivate_data
            == dals(
                """
        @CALL "%(deactivate1)s"
        @SET "PATH=%(new_path)s"
        @SET "CONDA_SHLVL=1"
        @SET "CONDA_PROMPT_MODIFIER=(%(native_prefix)s) "
        @CALL "%(activate1)s"
        """
            )
            % {
                "activate1": activator.path_conversion(
                    join(
                        shell_wrapper_unit,
                        "etc",
                        "conda",
                        "activate.d",
                        "activate1.bat",
                    )
                ),
                "deactivate1": activator.path_conversion(
                    join(
                        shell_wrapper_unit,
                        "etc",
                        "conda",
                        "deactivate.d",
                        "deactivate1.bat",
                    )
                ),
                "native_prefix": shell_wrapper_unit,
                "new_path": activator.pathsep_join(new_path_parts),
            }
        )

        with captured() as c:
            assert main_sourced("shell.cmd.exe", "deactivate") == 0
        assert not c.stderr
        deactivate_result = c.stdout

        with open(deactivate_result) as fh:
            deactivate_data = fh.read()
        rm_rf(deactivate_result)

        new_path = activator.pathsep_join(
            activator._remove_prefix_from_path(shell_wrapper_unit)
        )
        e_deactivate_data = (
            dals(
                """
        @SET "PATH=%(new_path)s"
        @CALL "%(deactivate1)s"
        @SET CONDA_PREFIX=
        @SET CONDA_DEFAULT_ENV=
        @SET CONDA_PROMPT_MODIFIER=
        @SET "CONDA_SHLVL=0"
        %(conda_exe_export)s
        """
            )
            % {
                "new_path": new_path,
                "deactivate1": activator.path_conversion(
                    join(
                        shell_wrapper_unit,
                        "etc",
                        "conda",
                        "deactivate.d",
                        "deactivate1.bat",
                    )
                ),
                "conda_exe_export": conda_exe_export,
            }
        )
        assert deactivate_data == e_deactivate_data


def test_csh_basic(shell_wrapper_unit: str):
    activator = CshActivator()
    make_dot_d_files(shell_wrapper_unit, activator.script_extension)

    with captured() as c:
        rc = main_sourced("shell.csh", *activate_args, shell_wrapper_unit)
    assert not c.stderr
    assert rc == 0
    activate_data = c.stdout

    new_path_parts = activator._add_prefix_to_path(shell_wrapper_unit)
    conda_exe_export, conda_exe_unset = activator.get_scripts_export_unset_vars()

    e_activate_data = (
        dals(
            """
    set prompt='%(prompt)s';
    setenv PATH "%(new_path)s";
    setenv CONDA_PREFIX "%(native_prefix)s";
    setenv CONDA_SHLVL "1";
    setenv CONDA_DEFAULT_ENV "%(native_prefix)s";
    setenv CONDA_PROMPT_MODIFIER "(%(native_prefix)s) ";
    %(conda_exe_export)s;
    source "%(activate1)s";
    """
        )
        % {
            "converted_prefix": activator.path_conversion(shell_wrapper_unit),
            "native_prefix": shell_wrapper_unit,
            "new_path": activator.pathsep_join(new_path_parts),
            "sys_executable": activator.path_conversion(sys.executable),
            "activate1": activator.path_conversion(
                join(shell_wrapper_unit, "etc", "conda", "activate.d", "activate1.csh")
            ),
            "prompt": "(%s) " % shell_wrapper_unit + os.environ.get("prompt", ""),
            "conda_exe_export": conda_exe_export,
        }
    )
    assert activate_data == e_activate_data

    with env_vars(
        {
            "CONDA_PREFIX": shell_wrapper_unit,
            "CONDA_SHLVL": "1",
            "PATH": os.pathsep.join((*new_path_parts, os.environ["PATH"])),
        }
    ):
        activator = CshActivator()
        with captured() as c:
            rc = main_sourced("shell.csh", *reactivate_args)
        assert not c.stderr
        assert rc == 0
        reactivate_data = c.stdout

        new_path_parts = activator._replace_prefix_in_path(
            shell_wrapper_unit, shell_wrapper_unit
        )
        e_reactivate_data = (
            dals(
                """
        source "%(deactivate1)s";
        set prompt='%(prompt)s';
        setenv PATH "%(new_path)s";
        setenv CONDA_SHLVL "1";
        setenv CONDA_PROMPT_MODIFIER "(%(native_prefix)s) ";
        source "%(activate1)s";
        """
            )
            % {
                "prompt": "(%s) " % shell_wrapper_unit + os.environ.get("prompt", ""),
                "new_path": activator.pathsep_join(new_path_parts),
                "activate1": activator.path_conversion(
                    join(
                        shell_wrapper_unit,
                        "etc",
                        "conda",
                        "activate.d",
                        "activate1.csh",
                    )
                ),
                "deactivate1": activator.path_conversion(
                    join(
                        shell_wrapper_unit,
                        "etc",
                        "conda",
                        "deactivate.d",
                        "deactivate1.csh",
                    )
                ),
                "native_prefix": shell_wrapper_unit,
            }
        )
        assert reactivate_data == e_reactivate_data
        with captured() as c:
            rc = main_sourced("shell.csh", *deactivate_args)
        assert not c.stderr
        assert rc == 0
        deactivate_data = c.stdout

        new_path = activator.pathsep_join(
            activator._remove_prefix_from_path(shell_wrapper_unit)
        )

        (
            conda_exe_export,
            conda_exe_unset,
        ) = activator.get_scripts_export_unset_vars()

        e_deactivate_data = (
            dals(
                """
        setenv PATH "%(new_path)s";
        source "%(deactivate1)s";
        unsetenv CONDA_PREFIX;
        unsetenv CONDA_DEFAULT_ENV;
        unsetenv CONDA_PROMPT_MODIFIER;
        set prompt='%(prompt)s';
        setenv CONDA_SHLVL "0";
        %(conda_exe_export)s;
        """
            )
            % {
                "new_path": new_path,
                "deactivate1": activator.path_conversion(
                    join(
                        shell_wrapper_unit,
                        "etc",
                        "conda",
                        "deactivate.d",
                        "deactivate1.csh",
                    )
                ),
                "prompt": os.environ.get("prompt", ""),
                "conda_exe_export": conda_exe_export,
            }
        )
        assert deactivate_data == e_deactivate_data


def test_xonsh_basic(shell_wrapper_unit: str):
    activator = XonshActivator()
    make_dot_d_files(shell_wrapper_unit, activator.script_extension)

    with captured() as c:
        rc = main_sourced("shell.xonsh", *activate_args, shell_wrapper_unit)
    assert not c.stderr
    assert rc == 0
    activate_data = c.stdout

    new_path_parts = activator._add_prefix_to_path(shell_wrapper_unit)
    conda_exe_export, conda_exe_unset = activator.get_scripts_export_unset_vars()
    e_activate_template = dals(
        """
    $PATH = '%(new_path)s'
    $CONDA_PREFIX = '%(native_prefix)s'
    $CONDA_SHLVL = '1'
    $CONDA_DEFAULT_ENV = '%(native_prefix)s'
    $CONDA_PROMPT_MODIFIER = '(%(native_prefix)s) '
    %(conda_exe_export)s
    %(sourcer)s "%(activate1)s"
    """
    )
    e_activate_info = {
        "converted_prefix": activator.path_conversion(shell_wrapper_unit),
        "native_prefix": shell_wrapper_unit,
        "new_path": activator.pathsep_join(new_path_parts),
        "sys_executable": activator.path_conversion(sys.executable),
        "conda_exe_export": conda_exe_export,
    }
    if on_win:
        e_activate_info["sourcer"] = "source-cmd --suppress-skip-message"
        e_activate_info["activate1"] = activator.path_conversion(
            join(shell_wrapper_unit, "etc", "conda", "activate.d", "activate1.bat")
        )
    else:
        e_activate_info["sourcer"] = "source-bash --suppress-skip-message"
        e_activate_info["activate1"] = activator.path_conversion(
            join(shell_wrapper_unit, "etc", "conda", "activate.d", "activate1.sh")
        )
    e_activate_data = e_activate_template % e_activate_info
    assert activate_data == e_activate_data

    with env_vars(
        {
            "CONDA_PREFIX": shell_wrapper_unit,
            "CONDA_SHLVL": "1",
            "PATH": os.pathsep.join((*new_path_parts, os.environ["PATH"])),
        }
    ):
        activator = XonshActivator()
        with captured() as c:
            rc = main_sourced("shell.xonsh", *reactivate_args)
        assert not c.stderr
        assert rc == 0
        reactivate_data = c.stdout

        new_path_parts = activator._replace_prefix_in_path(
            shell_wrapper_unit, shell_wrapper_unit
        )
        e_reactivate_template = dals(
            """
        %(sourcer)s "%(deactivate1)s"
        $PATH = '%(new_path)s'
        $CONDA_SHLVL = '1'
        $CONDA_PROMPT_MODIFIER = '(%(native_prefix)s) '
        %(sourcer)s "%(activate1)s"
        """
        )
        e_reactivate_info = {
            "new_path": activator.pathsep_join(new_path_parts),
            "native_prefix": shell_wrapper_unit,
        }
        if on_win:
            e_reactivate_info["sourcer"] = "source-cmd --suppress-skip-message"
            e_reactivate_info["activate1"] = activator.path_conversion(
                join(shell_wrapper_unit, "etc", "conda", "activate.d", "activate1.bat")
            )
            e_reactivate_info["deactivate1"] = activator.path_conversion(
                join(
                    shell_wrapper_unit,
                    "etc",
                    "conda",
                    "deactivate.d",
                    "deactivate1.bat",
                )
            )
        else:
            e_reactivate_info["sourcer"] = "source-bash --suppress-skip-message"
            e_reactivate_info["activate1"] = activator.path_conversion(
                join(shell_wrapper_unit, "etc", "conda", "activate.d", "activate1.sh")
            )
            e_reactivate_info["deactivate1"] = activator.path_conversion(
                join(
                    shell_wrapper_unit, "etc", "conda", "deactivate.d", "deactivate1.sh"
                )
            )
        e_reactivate_data = e_reactivate_template % e_reactivate_info
        assert reactivate_data == e_reactivate_data

        with captured() as c:
            rc = main_sourced("shell.xonsh", *deactivate_args)
        assert not c.stderr
        assert rc == 0
        deactivate_data = c.stdout

        new_path = activator.pathsep_join(
            activator._remove_prefix_from_path(shell_wrapper_unit)
        )
        (
            conda_exe_export,
            conda_exe_unset,
        ) = activator.get_scripts_export_unset_vars()
        e_deactivate_template = dals(
            """
        $PATH = '%(new_path)s'
        %(sourcer)s "%(deactivate1)s"
        del $CONDA_PREFIX
        del $CONDA_DEFAULT_ENV
        del $CONDA_PROMPT_MODIFIER
        $CONDA_SHLVL = '0'
        %(conda_exe_export)s
        """
        )
        e_deactivate_info = {
            "new_path": new_path,
            "conda_exe_export": conda_exe_export,
        }
        if on_win:
            e_deactivate_info["sourcer"] = "source-cmd --suppress-skip-message"
            e_deactivate_info["deactivate1"] = activator.path_conversion(
                join(
                    shell_wrapper_unit,
                    "etc",
                    "conda",
                    "deactivate.d",
                    "deactivate1.bat",
                )
            )
        else:
            e_deactivate_info["sourcer"] = "source-bash --suppress-skip-message"
            e_deactivate_info["deactivate1"] = activator.path_conversion(
                join(
                    shell_wrapper_unit, "etc", "conda", "deactivate.d", "deactivate1.sh"
                )
            )
        e_deactivate_data = e_deactivate_template % e_deactivate_info
        assert deactivate_data == e_deactivate_data


def test_fish_basic(shell_wrapper_unit: str):
    activator = FishActivator()
    make_dot_d_files(shell_wrapper_unit, activator.script_extension)

    with captured() as c:
        rc = main_sourced("shell.fish", *activate_args, shell_wrapper_unit)
    assert not c.stderr
    assert rc == 0
    activate_data = c.stdout

    new_path_parts = activator._add_prefix_to_path(shell_wrapper_unit)
    conda_exe_export, conda_exe_unset = activator.get_scripts_export_unset_vars()
    e_activate_data = (
        dals(
            """
    set -gx PATH "%(new_path)s";
    set -gx CONDA_PREFIX "%(native_prefix)s";
    set -gx CONDA_SHLVL "1";
    set -gx CONDA_DEFAULT_ENV "%(native_prefix)s";
    set -gx CONDA_PROMPT_MODIFIER "(%(native_prefix)s) ";
    %(conda_exe_export)s;
    source "%(activate1)s";
    """
        )
        % {
            "converted_prefix": activator.path_conversion(shell_wrapper_unit),
            "native_prefix": shell_wrapper_unit,
            "new_path": activator.pathsep_join(new_path_parts),
            "sys_executable": activator.path_conversion(sys.executable),
            "activate1": activator.path_conversion(
                join(shell_wrapper_unit, "etc", "conda", "activate.d", "activate1.fish")
            ),
            "conda_exe_export": conda_exe_export,
        }
    )
    assert activate_data == e_activate_data

    with env_vars(
        {
            "CONDA_PREFIX": shell_wrapper_unit,
            "CONDA_SHLVL": "1",
            "PATH": os.pathsep.join((*new_path_parts, os.environ["PATH"])),
        }
    ):
        activator = FishActivator()
        with captured() as c:
            rc = main_sourced("shell.fish", *reactivate_args)
        assert not c.stderr
        assert rc == 0
        reactivate_data = c.stdout

        new_path_parts = activator._replace_prefix_in_path(
            shell_wrapper_unit, shell_wrapper_unit
        )
        e_reactivate_data = (
            dals(
                """
        source "%(deactivate1)s";
        set -gx PATH "%(new_path)s";
        set -gx CONDA_SHLVL "1";
        set -gx CONDA_PROMPT_MODIFIER "(%(native_prefix)s) ";
        source "%(activate1)s";
        """
            )
            % {
                "new_path": activator.pathsep_join(new_path_parts),
                "activate1": activator.path_conversion(
                    join(
                        shell_wrapper_unit,
                        "etc",
                        "conda",
                        "activate.d",
                        "activate1.fish",
                    )
                ),
                "deactivate1": activator.path_conversion(
                    join(
                        shell_wrapper_unit,
                        "etc",
                        "conda",
                        "deactivate.d",
                        "deactivate1.fish",
                    )
                ),
                "native_prefix": shell_wrapper_unit,
            }
        )
        assert reactivate_data == e_reactivate_data

        with captured() as c:
            rc = main_sourced("shell.fish", *deactivate_args)
        assert not c.stderr
        assert rc == 0
        deactivate_data = c.stdout

        new_path = activator.pathsep_join(
            activator._remove_prefix_from_path(shell_wrapper_unit)
        )
        (
            conda_exe_export,
            conda_exe_unset,
        ) = activator.get_scripts_export_unset_vars()
        e_deactivate_data = (
            dals(
                """
        set -gx PATH "%(new_path)s";
        source "%(deactivate1)s";
        set -e CONDA_PREFIX;
        set -e CONDA_DEFAULT_ENV;
        set -e CONDA_PROMPT_MODIFIER;
        set -gx CONDA_SHLVL "0";
        %(conda_exe_export)s;
        """
            )
            % {
                "new_path": new_path,
                "deactivate1": activator.path_conversion(
                    join(
                        shell_wrapper_unit,
                        "etc",
                        "conda",
                        "deactivate.d",
                        "deactivate1.fish",
                    )
                ),
                "conda_exe_export": conda_exe_export,
            }
        )
        assert deactivate_data == e_deactivate_data


def test_powershell_basic(shell_wrapper_unit: str):
    activator = PowerShellActivator()
    make_dot_d_files(shell_wrapper_unit, activator.script_extension)

    with captured() as c:
        rc = main_sourced("shell.powershell", *activate_args, shell_wrapper_unit)
    assert not c.stderr
    assert rc == 0
    activate_data = c.stdout

    new_path_parts = activator._add_prefix_to_path(shell_wrapper_unit)
    conda_exe_export, conda_exe_unset = activator.get_scripts_export_unset_vars()
    e_activate_data = (
        dals(
            """
    $Env:PATH = "%(new_path)s"
    $Env:CONDA_PREFIX = "%(prefix)s"
    $Env:CONDA_SHLVL = "1"
    $Env:CONDA_DEFAULT_ENV = "%(prefix)s"
    $Env:CONDA_PROMPT_MODIFIER = "(%(prefix)s) "
    %(conda_exe_export)s
    . "%(activate1)s"
    """
        )
        % {
            "prefix": shell_wrapper_unit,
            "new_path": activator.pathsep_join(new_path_parts),
            "sys_executable": sys.executable,
            "activate1": join(
                shell_wrapper_unit, "etc", "conda", "activate.d", "activate1.ps1"
            ),
            "conda_exe_export": conda_exe_export,
        }
    )
    assert activate_data == e_activate_data

    with env_vars(
        {
            "CONDA_PREFIX": shell_wrapper_unit,
            "CONDA_SHLVL": "1",
            "PATH": os.pathsep.join((*new_path_parts, os.environ["PATH"])),
        }
    ):
        activator = PowerShellActivator()
        with captured() as c:
            rc = main_sourced("shell.powershell", *reactivate_args)
        assert not c.stderr
        assert rc == 0
        reactivate_data = c.stdout

        new_path_parts = activator._replace_prefix_in_path(
            shell_wrapper_unit, shell_wrapper_unit
        )
        assert (
            reactivate_data
            == dals(
                """
        . "%(deactivate1)s"
        $Env:PATH = "%(new_path)s"
        $Env:CONDA_SHLVL = "1"
        $Env:CONDA_PROMPT_MODIFIER = "(%(prefix)s) "
        . "%(activate1)s"
        """
            )
            % {
                "activate1": join(
                    shell_wrapper_unit, "etc", "conda", "activate.d", "activate1.ps1"
                ),
                "deactivate1": join(
                    shell_wrapper_unit,
                    "etc",
                    "conda",
                    "deactivate.d",
                    "deactivate1.ps1",
                ),
                "prefix": shell_wrapper_unit,
                "new_path": activator.pathsep_join(new_path_parts),
            }
        )

        with captured() as c:
            rc = main_sourced("shell.powershell", *deactivate_args)
        assert not c.stderr
        assert rc == 0
        deactivate_data = c.stdout

        new_path = activator.pathsep_join(
            activator._remove_prefix_from_path(shell_wrapper_unit)
        )

        assert (
            deactivate_data
            == dals(
                """
        $Env:PATH = "%(new_path)s"
        . "%(deactivate1)s"
        $Env:CONDA_PREFIX = ""
        $Env:CONDA_DEFAULT_ENV = ""
        $Env:CONDA_PROMPT_MODIFIER = ""
        $Env:CONDA_SHLVL = "0"
        %(conda_exe_export)s
        """
            )
            % {
                "new_path": new_path,
                "deactivate1": join(
                    shell_wrapper_unit,
                    "etc",
                    "conda",
                    "deactivate.d",
                    "deactivate1.ps1",
                ),
                "conda_exe_export": conda_exe_export,
            }
        )


def test_unicode(shell_wrapper_unit: str):
    shell = "shell.posix"
    prompt = "PS1"
    prompt_value = "%{\xc2\xbb".encode(sys.getfilesystemencoding())
    with env_vars({prompt: prompt_value}):
        # use a file as output stream to simulate PY2 default stdout
        with tempdir() as td:
            with open(join(td, "stdout"), "w") as stdout:
                with captured(stdout=stdout):
                    main_sourced(shell, *activate_args, shell_wrapper_unit)


def test_json_basic(shell_wrapper_unit: str):
    activator = _build_activator_cls("posix+json")()
    make_dot_d_files(shell_wrapper_unit, activator.script_extension)

    with captured() as c:
        rc = main_sourced("shell.posix+json", *activate_args, shell_wrapper_unit)
    assert not c.stderr
    assert rc == 0
    activate_data = c.stdout

    new_path_parts = activator._add_prefix_to_path(shell_wrapper_unit)
    conda_exe_export, conda_exe_unset = activator.get_scripts_export_unset_vars()
    e_activate_data = {
        "path": {
            "PATH": list(new_path_parts),
        },
        "vars": {
            "export": dict(
                CONDA_PREFIX=shell_wrapper_unit,
                CONDA_SHLVL=1,
                CONDA_DEFAULT_ENV=shell_wrapper_unit,
                CONDA_PROMPT_MODIFIER="(%s) " % shell_wrapper_unit,
                **conda_exe_export,
            ),
            "set": {
                "PS1": "(%s) " % shell_wrapper_unit,
            },
            "unset": [],
        },
        "scripts": {
            "activate": [
                activator.path_conversion(
                    join(
                        shell_wrapper_unit, "etc", "conda", "activate.d", "activate1.sh"
                    )
                ),
            ],
            "deactivate": [],
        },
    }
    assert json.loads(activate_data) == e_activate_data

    with env_vars(
        {
            "CONDA_PREFIX": shell_wrapper_unit,
            "CONDA_SHLVL": "1",
            "PATH": os.pathsep.join((*new_path_parts, os.environ["PATH"])),
        }
    ):
        activator = _build_activator_cls("posix+json")()
        with captured() as c:
            rc = main_sourced("shell.posix+json", *reactivate_args)
        assert not c.stderr
        assert rc == 0
        reactivate_data = c.stdout

        new_path_parts = activator._replace_prefix_in_path(
            shell_wrapper_unit, shell_wrapper_unit
        )
        e_reactivate_data = {
            "path": {
                "PATH": list(new_path_parts),
            },
            "vars": {
                "export": {
                    "CONDA_SHLVL": 1,
                    "CONDA_PROMPT_MODIFIER": "(%s) " % shell_wrapper_unit,
                },
                "set": {
                    "PS1": "(%s) " % shell_wrapper_unit,
                },
                "unset": [],
            },
            "scripts": {
                "activate": [
                    activator.path_conversion(
                        join(
                            shell_wrapper_unit,
                            "etc",
                            "conda",
                            "activate.d",
                            "activate1.sh",
                        )
                    ),
                ],
                "deactivate": [
                    activator.path_conversion(
                        join(
                            shell_wrapper_unit,
                            "etc",
                            "conda",
                            "deactivate.d",
                            "deactivate1.sh",
                        )
                    ),
                ],
            },
        }
        assert json.loads(reactivate_data) == e_reactivate_data

        with captured() as c:
            rc = main_sourced("shell.posix+json", *deactivate_args)
        assert not c.stderr
        assert rc == 0
        deactivate_data = c.stdout

        new_path = activator.pathsep_join(
            activator._remove_prefix_from_path(shell_wrapper_unit)
        )
        (
            conda_exe_export,
            conda_exe_unset,
        ) = activator.get_scripts_export_unset_vars()
        e_deactivate_data = {
            "path": {
                "PATH": list(new_path),
            },
            "vars": {
                "export": dict(CONDA_SHLVL=0, **conda_exe_export),
                "set": {
                    "PS1": "",
                },
                "unset": [
                    "CONDA_PREFIX",
                    "CONDA_DEFAULT_ENV",
                    "CONDA_PROMPT_MODIFIER",
                ],
            },
            "scripts": {
                "activate": [],
                "deactivate": [
                    activator.path_conversion(
                        join(
                            shell_wrapper_unit,
                            "etc",
                            "conda",
                            "deactivate.d",
                            "deactivate1.sh",
                        )
                    ),
                ],
            },
        }
        assert json.loads(deactivate_data) == e_deactivate_data


class InteractiveShell:
    activator = None
    init_command = None
    print_env_var = None
    from conda.utils import quote_for_shell

    exe_quoted = quote_for_shell(
        sys.executable.replace("\\", "/") if on_win else sys.executable
    )
    shells = {
        "posix": {
            "activator": "posix",
            # 'init_command': 'env | sort && mount && which {0} && {0} -V && echo "$({0} -m conda shell.posix hook)" && eval "$({0} -m conda shell.posix hook)"'.format('/c/Users/rdonnelly/mc/python.exe'), # sys.executable.replace('\\', '/')),
            # 'init_command': 'env | sort && echo "$({0} -m conda shell.posix hook)" && eval "$({0} -m conda shell.posix hook)"'.format(self.
            #    '/c/Users/rdonnelly/mc/python.exe'),  # sys.executable.replace('\\', '/')),
            "init_command": (
                'env | sort && echo "$({0} -m conda shell.posix hook {1})" && '
                'eval "$({0} -m conda shell.posix hook {1})" && env | sort'.format(
                    exe_quoted, dev_arg
                )
            ),
            "print_env_var": 'echo "$%s"',
        },
        "bash": {
            # MSYS2's login scripts handle mounting the filesystem. Without it, /c is /cygdrive.
            "args": ("-l",) if on_win else (),
            "base_shell": "posix",  # inheritance implemented in __init__
        },
        "dash": {
            "base_shell": "posix",  # inheritance implemented in __init__
        },
        "zsh": {
            "base_shell": "posix",  # inheritance implemented in __init__
            "init_command": (
                f'env | sort && eval "$({exe_quoted} -m conda shell.zsh hook {dev_arg})"'
            ),
        },
        # It should be noted here that we use the latest hook with whatever conda.exe is installed
        # in sys.prefix (and we will activate all of those PATH entries).  We will set PYTHONPATH
        # though, so there is that.  What I'm getting at is that this is a huge mixup and a mess.
        "cmd.exe": {
            "activator": "cmd.exe",
            # For non-dev-mode you'd have:
            #            'init_command': 'set "CONDA_SHLVL=" '
            #                            '&& @CALL {}\\shell\\condabin\\conda_hook.bat {} '
            #                            '&& set CONDA_EXE={}'
            #                            '&& set _CE_M='
            #                            '&& set _CE_CONDA='
            #                            .format(CONDA_PACKAGE_ROOT, dev_arg,
            #                                    join(sys.prefix, "Scripts", "conda.exe")),
            "init_command": 'set "CONDA_SHLVL=" '
            "&& @CALL {}\\shell\\condabin\\conda_hook.bat {}"
            "&& set CONDA_EXE={}"
            "&& set _CE_M=-m"
            "&& set _CE_CONDA=conda".format(
                CONDA_PACKAGE_ROOT, dev_arg, sys.executable
            ),
            "print_env_var": "@echo %%%s%%",
        },
        "csh": {
            "activator": "csh",
            # Trying to use -x with `tcsh` on `macOS` results in some problems:
            # This error from `PyCharm`:
            # BrokenPipeError: [Errno 32] Broken pipe (writing to self.proc.stdin).
            # .. and this one from the `macOS` terminal:
            # pexpect.exceptions.EOF: End Of File (EOF).
            # 'args': ('-x',),
            "init_command": 'set _CONDA_EXE="{CPR}/shell/bin/conda"; '
            "source {CPR}/shell/etc/profile.d/conda.csh; ".format(
                CPR=CONDA_PACKAGE_ROOT
            ),
            "print_env_var": 'echo "$%s"',
        },
        "tcsh": {
            "base_shell": "csh",
        },
        "fish": {
            "activator": "fish",
            "init_command": f"eval ({exe_quoted} -m conda shell.fish hook {dev_arg})",
            "print_env_var": "echo $%s",
        },
        # We don't know if the PowerShell executable is called
        # powershell, pwsh, or pwsh-preview.
        "powershell": {
            "activator": "powershell",
            "args": ("-NoProfile", "-NoLogo"),
            "init_command": "{} -m conda shell.powershell hook --dev | Out-String | Invoke-Expression".format(
                sys.executable
            ),
            "print_env_var": "$Env:%s",
            "exit_cmd": "exit",
        },
        "pwsh": {"base_shell": "powershell"},
        "pwsh-preview": {"base_shell": "powershell"},
    }

    def __init__(self, shell_name):
        self.shell_name = shell_name
        base_shell = self.shells[shell_name].get("base_shell")
        shell_vals = self.shells.get(base_shell, {}).copy()
        shell_vals.update(self.shells[shell_name])
        for key, value in shell_vals.items():
            setattr(self, key, value)
        self.activator = activator_map[shell_vals["activator"]]()
        self.exit_cmd = self.shells[shell_name].get("exit_cmd", None)

    def __enter__(self):
        from pexpect.popen_spawn import PopenSpawn

        # remove all CONDA_ env vars
        # this ensures that PATH is shared with any msys2 bash shell, rather than starting fresh
        os.environ["MSYS2_PATH_TYPE"] = "inherit"
        os.environ["CHERE_INVOKING"] = "1"
        env = {str(k): str(v) for k, v in os.environ.items()}
        remove_these = {var_name for var_name in env if var_name.startswith("CONDA_")}
        for var_name in remove_these:
            del env[var_name]
        from conda.utils import quote_for_shell

        # 1. shell='cmd.exe' is deliberate. We are not, at this time, running bash, we
        #    are launching it (from `cmd.exe` most likely).
        # 2. For some reason, passing just self.shell_name (which is `bash`) runs WSL
        #    bash instead of MSYS2's, even when MSYS2 appears before System32 on PATH.
        shell_found = which(self.shell_name) or self.shell_name
        args = list(self.args) if hasattr(self, "args") else []

        p = PopenSpawn(
            quote_for_shell(shell_found, *args),
            timeout=30,
            maxread=5000,
            searchwindowsize=None,
            logfile=sys.stdout,
            cwd=os.getcwd(),
            env=env,
            encoding="utf-8",
            codec_errors="strict",
        )

        # set state for context
        joiner = (
            os.pathsep.join
            if self.shell_name == "fish"
            else self.activator.pathsep_join
        )
        PATH = joiner(
            self.activator.path_conversion(
                (
                    *self.activator._get_starting_path_list(),
                    dirname(which(self.shell_name)),
                )
            )
        )
        self.original_path = PATH
        env = {
            "CONDA_AUTO_ACTIVATE_BASE": "false",
            "PYTHONPATH": self.activator.path_conversion(CONDA_SOURCE_ROOT),
            "PATH": PATH,
        }
        for ev in (
            "CONDA_TEST_SAVE_TEMPS",
            "CONDA_TEST_TMPDIR",
            "CONDA_TEST_USER_ENVIRONMENTS_TXT_FILE",
        ):
            if ev in os.environ:
                env[ev] = os.environ[ev]

        for name, val in env.items():
            p.sendline(self.activator.export_var_tmpl % (name, val))

        if self.init_command:
            p.sendline(self.init_command)
        self.p = p
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            print(f"Exception encountered: {exc_val}")
        if self.p:
            if self.exit_cmd:
                self.sendline(self.exit_cmd)
            import signal

            self.p.kill(signal.SIGINT)

    def sendline(self, s):
        return self.p.sendline(s)

    def expect(self, pattern, timeout=-1, searchwindowsize=-1, async_=False):
        return self.p.expect(pattern, timeout, searchwindowsize, async_)

    def assert_env_var(self, env_var, value, use_exact=False):
        # value is actually a regex
        self.sendline(self.print_env_var % env_var)
        try:
            if use_exact:
                self.p.expect_exact(value)
                self.expect(".*\n")
            else:
                self.expect("%s\n" % value)
        except:
            print(self.p.before)
            print(self.p.after)
            raise

    def get_env_var(self, env_var, default=None):
        if self.shell_name == "cmd.exe":
            self.sendline("@echo %%%s%%" % env_var)
            self.expect("@echo %%%s%%\r\n([^\r]*)\r" % env_var)
            value = self.p.match.groups()[0]
        elif self.shell_name in ("powershell", "pwsh"):
            self.sendline(self.print_env_var % env_var)
            if platform.system() == "Windows":
                # The \r\n\( is the newline after the env var and the start of the prompt.
                # If we knew the active env we could add that in as well as the closing )
                self.expect(rf"\$Env:{env_var}\r\n([^\r]*)(\r\n).*")
                value = self.p.match.groups()[0]
            else:
                self.expect(f"\\$Env:{env_var}\n")
                value = self.p.readline()
        else:
            self.sendline("echo get_var_start")
            self.sendline(self.print_env_var % env_var)
            self.sendline("echo get_var_end")
            self.expect("get_var_start\n")
            value = self.p.readline()
            self.expect("get_var_end")
        if value is None:
            return default
        return ensure_text_type(value).strip()


def which_powershell():
    r"""
    Since we don't know whether PowerShell is installed as powershell, pwsh, or pwsh-preview,
    it's helpful to have a utility function that returns the name of the best PowerShell
    executable available, or `None` if there's no PowerShell installed.

    If PowerShell is found, this function returns both the kind of PowerShell install
    found and a path to its main executable.
    E.g.: ('pwsh', r'C:\Program Files\PowerShell\6.0.2\pwsh.exe)
    """
    if on_win:
        posh = which("powershell.exe")
        if posh:
            return "powershell", posh

    posh = which("pwsh")
    if posh:
        return "pwsh", posh

    posh = which("pwsh-preview")
    if posh:
        return "pwsh-preview", posh


@pytest.fixture
def shell_wrapper_integration(path_factory: PathFactoryFixture) -> tuple[str, str, str]:
    prefix = path_factory(
        prefix=uuid4().hex[:4], name=SPACER_CHARACTER, suffix=uuid4().hex[:4]
    )
    history = prefix / "conda-meta" / "history"
    history.parent.mkdir(parents=True, exist_ok=True)
    history.touch()

    prefix2 = prefix / "envs" / "charizard"
    history2 = prefix2 / "conda-meta" / "history"
    history2.parent.mkdir(parents=True, exist_ok=True)
    history2.touch()

    prefix3 = prefix / "envs" / "venusaur"
    history3 = prefix3 / "conda-meta" / "history"
    history3.parent.mkdir(parents=True, exist_ok=True)
    history3.touch()

    yield str(prefix), str(prefix2), str(prefix3)


def basic_posix(shell, prefix, prefix2, prefix3):
    if shell.shell_name in ("zsh", "dash"):
        conda_is_a_function = "conda is a shell function"
    else:
        conda_is_a_function = "conda is a function"

    activate = f" activate {dev_arg} "
    deactivate = f" deactivate {dev_arg} "
    install = f" install {dev_arg} "

    activator = PosixActivator()
    num_paths_added = len(tuple(activator._get_path_dirs(prefix)))
    prefix_p = activator.path_conversion(prefix)
    prefix2_p = activator.path_conversion(prefix2)
    activator.path_conversion(prefix3)

    PATH0 = shell.get_env_var("PATH", "")
    assert any(p.endswith("condabin") for p in PATH0.split(":"))

    # calling bash -l, as we do for MSYS2, may cause conda activation.
    shell.sendline("conda deactivate")
    shell.sendline("conda deactivate")
    shell.sendline("conda deactivate")
    shell.sendline("conda deactivate")
    shell.expect(".*\n")

    shell.assert_env_var("CONDA_SHLVL", "0")
    PATH0 = shell.get_env_var("PATH", "")
    assert len([p for p in PATH0.split(":") if p.endswith("condabin")]) > 0
    # Remove sys.prefix from PATH. It interferes with path entry count tests.
    # We can no longer check this since we'll replace e.g. between 1 and N path
    # entries with N of them in _replace_prefix_in_path() now. It is debatable
    # whether it should be here at all too.
    if PATH0.startswith(activator.path_conversion(sys.prefix) + ":"):
        PATH0 = PATH0[len(activator.path_conversion(sys.prefix)) + 1 :]
        shell.sendline(f'export PATH="{PATH0}"')
        PATH0 = shell.get_env_var("PATH", "")
    shell.sendline("type conda")
    shell.expect(conda_is_a_function)

    _CE_M = shell.get_env_var("_CE_M")
    _CE_CONDA = shell.get_env_var("_CE_CONDA")

    shell.sendline("conda --version")
    shell.p.expect_exact("conda " + conda_version)

    shell.sendline("conda" + activate + "base")

    shell.sendline("type conda")
    shell.expect(conda_is_a_function)

    CONDA_EXE2 = shell.get_env_var("CONDA_EXE")
    _CE_M2 = shell.get_env_var("_CE_M")

    shell.assert_env_var("PS1", "(base).*")
    shell.assert_env_var("CONDA_SHLVL", "1")
    PATH1 = shell.get_env_var("PATH", "")
    assert len(PATH0.split(":")) + num_paths_added == len(PATH1.split(":"))

    CONDA_EXE = shell.get_env_var("CONDA_EXE")
    _CE_M = shell.get_env_var("_CE_M")
    _CE_CONDA = shell.get_env_var("_CE_CONDA")

    log.debug("activating ..")
    shell.sendline("conda" + activate + '"%s"' % prefix_p)

    shell.sendline("type conda")
    shell.expect(conda_is_a_function)

    CONDA_EXE2 = shell.get_env_var("CONDA_EXE")
    _CE_M2 = shell.get_env_var("_CE_M")
    _CE_CONDA2 = shell.get_env_var("_CE_CONDA")
    assert (
        CONDA_EXE == CONDA_EXE2
    ), "CONDA_EXE changed by activation procedure\n:From\n{}\nto:\n{}".format(
        CONDA_EXE, CONDA_EXE2
    )
    assert (
        _CE_M2 == _CE_M2
    ), f"_CE_M changed by activation procedure\n:From\n{_CE_M}\nto:\n{_CE_M2}"
    assert (
        _CE_CONDA == _CE_CONDA2
    ), "_CE_CONDA changed by activation procedure\n:From\n{}\nto:\n{}".format(
        _CE_CONDA, _CE_CONDA2
    )

    shell.sendline("env | sort")
    # When CONDA_SHLVL==2 fails it usually means that conda activate failed. We that fails it is
    # usually because you forgot to pass `--dev` to the *previous* activate so CONDA_EXE changed
    # from python to conda, which is then found on PATH instead of using the dev sources. When it
    # goes to use this old conda to generate the activation script for the newly activated env.
    # it is running the old code (or at best, a mix of new code and old scripts).
    shell.assert_env_var("CONDA_SHLVL", "2")
    CONDA_PREFIX = shell.get_env_var("CONDA_PREFIX", "")
    # We get C: vs c: differences on Windows.
    # Also, self.prefix instead of prefix_p is deliberate (maybe unfortunate?)
    assert CONDA_PREFIX.lower() == prefix.lower()
    PATH2 = shell.get_env_var("PATH", "")
    assert len(PATH0.split(":")) + num_paths_added == len(PATH2.split(":"))

    shell.sendline("env | sort | grep CONDA")
    shell.expect("CONDA_")
    shell.sendline('echo "PATH=$PATH"')
    shell.expect("PATH=")
    shell.sendline("conda" + activate + '"%s"' % prefix2_p)
    shell.sendline("env | sort | grep CONDA")
    shell.expect("CONDA_")
    shell.sendline('echo "PATH=$PATH"')
    shell.expect("PATH=")
    shell.assert_env_var("PS1", "(charizard).*")
    shell.assert_env_var("CONDA_SHLVL", "3")
    PATH3 = shell.get_env_var("PATH")
    assert len(PATH0.split(":")) + num_paths_added == len(PATH3.split(":"))

    CONDA_EXE2 = shell.get_env_var("CONDA_EXE")
    _CE_M2 = shell.get_env_var("_CE_M")
    _CE_CONDA2 = shell.get_env_var("_CE_CONDA")
    assert (
        CONDA_EXE == CONDA_EXE2
    ), "CONDA_EXE changed by stacked activation procedure\n:From\n{}\nto:\n{}".format(
        CONDA_EXE, CONDA_EXE2
    )
    assert (
        _CE_M2 == _CE_M2
    ), "_CE_M changed by stacked activation procedure\n:From\n{}\nto:\n{}".format(
        _CE_M, _CE_M2
    )
    assert (
        _CE_CONDA == _CE_CONDA2
    ), "_CE_CONDA stacked changed by activation procedure\n:From\n{}\nto:\n{}".format(
        _CE_CONDA, _CE_CONDA2
    )

    shell.sendline("conda" + install + f"-yq hdf5={HDF5_VERSION}")
    shell.expect("Executing transaction: ...working... done.*\n", timeout=120)
    shell.assert_env_var("?", "0", use_exact=True)

    shell.sendline("h5stat --version")
    shell.expect(rf".*h5stat: Version {HDF5_VERSION}.*")

    # TODO: assert that reactivate worked correctly

    shell.sendline("type conda")
    shell.expect(conda_is_a_function)

    shell.sendline(f"conda run {dev_arg} h5stat --version")
    shell.expect(rf".*h5stat: Version {HDF5_VERSION}.*")

    # regression test for #6840
    shell.sendline("conda" + install + "--blah")
    shell.assert_env_var("?", "2", use_exact=True)
    shell.sendline("conda list --blah")
    shell.assert_env_var("?", "2", use_exact=True)

    shell.sendline("conda" + deactivate)
    shell.assert_env_var("CONDA_SHLVL", "2")
    PATH = shell.get_env_var("PATH")
    assert len(PATH0.split(":")) + num_paths_added == len(PATH.split(":"))

    shell.sendline("conda" + deactivate)
    shell.assert_env_var("CONDA_SHLVL", "1")
    PATH = shell.get_env_var("PATH")
    assert len(PATH0.split(":")) + num_paths_added == len(PATH.split(":"))

    shell.sendline("conda" + deactivate)
    shell.assert_env_var("CONDA_SHLVL", "0")
    PATH = shell.get_env_var("PATH")
    assert len(PATH0.split(":")) == len(PATH.split(":"))
    if on_win:
        assert PATH0.lower() == PATH.lower()
    else:
        assert PATH0 == PATH

    shell.sendline(shell.print_env_var % "PS1")
    shell.expect(".*\n")
    assert "CONDA_PROMPT_MODIFIER" not in str(shell.p.after)

    shell.sendline("conda" + deactivate)
    shell.assert_env_var("CONDA_SHLVL", "0")

    # When fully deactivated, CONDA_EXE, _CE_M and _CE_CONDA must be retained
    # because the conda shell scripts use them and if they are unset activation
    # is not possible.
    CONDA_EXED = shell.get_env_var("CONDA_EXE")
    assert CONDA_EXED, (
        "A fully deactivated conda shell must retain CONDA_EXE (and _CE_M and _CE_CONDA in dev)\n"
        "  as the shell scripts refer to them."
    )

    PATH0 = shell.get_env_var("PATH")

    shell.sendline("conda" + activate + '"%s"' % prefix2_p)
    shell.assert_env_var("CONDA_SHLVL", "1")
    PATH1 = shell.get_env_var("PATH")
    assert len(PATH0.split(":")) + num_paths_added == len(PATH1.split(":"))

    shell.sendline("conda" + activate + '"%s" --stack' % prefix3)
    shell.assert_env_var("CONDA_SHLVL", "2")
    PATH2 = shell.get_env_var("PATH")
    assert "charizard" in PATH2
    assert "venusaur" in PATH2
    assert len(PATH0.split(":")) + num_paths_added * 2 == len(PATH2.split(":"))

    shell.sendline("conda" + activate + '"%s"' % prefix_p)
    shell.assert_env_var("CONDA_SHLVL", "3")
    PATH3 = shell.get_env_var("PATH")
    assert "charizard" in PATH3
    assert "venusaur" not in PATH3
    assert len(PATH0.split(":")) + num_paths_added * 2 == len(PATH3.split(":"))

    shell.sendline("conda" + deactivate)
    shell.assert_env_var("CONDA_SHLVL", "2")
    PATH4 = shell.get_env_var("PATH")
    assert "charizard" in PATH4
    assert "venusaur" in PATH4
    if on_win:
        assert PATH4.lower() == PATH2.lower()
    else:
        assert PATH4 == PATH2

    shell.sendline("conda" + deactivate)
    shell.assert_env_var("CONDA_SHLVL", "1")
    PATH5 = shell.get_env_var("PATH")
    if on_win:
        assert PATH1.lower() == PATH5.lower()
    else:
        assert PATH1 == PATH5

    # Test auto_stack
    shell.sendline("conda config --env --set auto_stack 1")

    shell.sendline("conda" + activate + '"%s"' % prefix3)
    shell.assert_env_var("CONDA_SHLVL", "2")
    PATH2 = shell.get_env_var("PATH")
    assert "charizard" in PATH2
    assert "venusaur" in PATH2
    assert len(PATH0.split(":")) + num_paths_added * 2 == len(PATH2.split(":"))

    shell.sendline("conda" + activate + '"%s"' % prefix_p)
    shell.assert_env_var("CONDA_SHLVL", "3")
    PATH3 = shell.get_env_var("PATH")
    assert "charizard" in PATH3
    assert "venusaur" not in PATH3
    assert len(PATH0.split(":")) + num_paths_added * 2 == len(PATH3.split(":"))


def basic_csh(shell, prefix, prefix2, prefix3):
    shell.sendline("conda --version")
    shell.p.expect_exact("conda " + conda_version)
    shell.assert_env_var("CONDA_SHLVL", "0")
    shell.sendline("conda activate base")
    shell.assert_env_var("prompt", "(base).*")
    shell.assert_env_var("CONDA_SHLVL", "1")
    shell.sendline('conda activate "%s"' % prefix)
    shell.assert_env_var("CONDA_SHLVL", "2")
    shell.assert_env_var("CONDA_PREFIX", prefix, True)
    shell.sendline("conda deactivate")
    shell.assert_env_var("CONDA_SHLVL", "1")
    shell.sendline("conda deactivate")
    shell.assert_env_var("CONDA_SHLVL", "0")

    assert "CONDA_PROMPT_MODIFIER" not in str(shell.p.after)

    shell.sendline("conda deactivate")
    shell.assert_env_var("CONDA_SHLVL", "0")


@pytest.mark.flaky(reruns=5)
@pytest.mark.skipif(bash_unsupported(), reason=bash_unsupported_because())
@pytest.mark.integration
def test_bash_basic_integration(shell_wrapper_integration: tuple[str, str, str]):
    with InteractiveShell("bash") as shell:
        basic_posix(shell, *shell_wrapper_integration)


@pytest.mark.skipif(not which("dash") or on_win, reason="dash not installed")
@pytest.mark.integration
def test_dash_basic_integration(shell_wrapper_integration: tuple[str, str, str]):
    with InteractiveShell("dash") as shell:
        basic_posix(shell, *shell_wrapper_integration)


@pytest.mark.skipif(not which("zsh"), reason="zsh not installed")
@pytest.mark.integration
def test_zsh_basic_integration(shell_wrapper_integration: tuple[str, str, str]):
    with InteractiveShell("zsh") as shell:
        basic_posix(shell, *shell_wrapper_integration)


@pytest.mark.skipif(not which("csh"), reason="csh not installed")
@pytest.mark.xfail(
    reason="pure csh doesn't support argument passing to sourced scripts"
)
@pytest.mark.integration
def test_csh_basic_integration(shell_wrapper_integration: tuple[str, str, str]):
    with InteractiveShell("csh") as shell:
        basic_csh(shell, *shell_wrapper_integration)


@pytest.mark.skipif(not which("tcsh"), reason="tcsh not installed")
@pytest.mark.xfail(reason="punting until we officially enable support for tcsh")
@pytest.mark.integration
def test_tcsh_basic_integration(shell_wrapper_integration: tuple[str, str, str]):
    with InteractiveShell("tcsh") as shell:
        basic_csh(shell, *shell_wrapper_integration)


@pytest.mark.skipif(not which("fish"), reason="fish not installed")
@pytest.mark.xfail(reason="fish and pexpect don't seem to work together?")
@pytest.mark.integration
def test_fish_basic_integration(shell_wrapper_integration: tuple[str, str, str]):
    prefix, _, _ = shell_wrapper_integration

    with InteractiveShell("fish") as shell:
        shell.sendline("env | sort")
        # We should be seeing environment variable output to terminal with this line, but
        # we aren't.  Haven't experienced this problem yet with any other shell...

        shell.assert_env_var("CONDA_SHLVL", "0")
        shell.sendline("conda activate base")
        shell.assert_env_var("CONDA_SHLVL", "1")
        shell.sendline('conda activate "%s"' % prefix)
        shell.assert_env_var("CONDA_SHLVL", "2")
        shell.assert_env_var("CONDA_PREFIX", prefix, True)
        shell.sendline("conda deactivate")
        shell.assert_env_var("CONDA_SHLVL", "1")
        shell.sendline("conda deactivate")
        shell.assert_env_var("CONDA_SHLVL", "0")

        shell.sendline(shell.print_env_var % "PS1")
        shell.expect(".*\n")
        assert "CONDA_PROMPT_MODIFIER" not in str(shell.p.after)

        shell.sendline("conda deactivate")
        shell.assert_env_var("CONDA_SHLVL", "0")


@pytest.mark.skipif(not which_powershell(), reason="PowerShell not installed")
@pytest.mark.integration
def test_powershell_basic_integration(shell_wrapper_integration: tuple[str, str, str]):
    prefix, charizard, venusaur = shell_wrapper_integration

    posh_kind, posh_path = which_powershell()
    print(f"## [PowerShell integration] Using {posh_path}.")
    with InteractiveShell(posh_kind) as shell:
        print("## [PowerShell integration] Starting test.")
        shell.sendline("(Get-Command conda).CommandType")
        shell.p.expect_exact("Alias")
        shell.sendline("(Get-Command conda).Definition")
        shell.p.expect_exact("Invoke-Conda")
        shell.sendline("(Get-Command Invoke-Conda).Definition")

        print("## [PowerShell integration] Activating.")
        shell.sendline('conda activate "%s"' % charizard)
        shell.assert_env_var("CONDA_SHLVL", "1\r?")
        PATH = shell.get_env_var("PATH")
        assert "charizard" in PATH
        shell.sendline("conda --version")
        shell.p.expect_exact("conda " + conda_version)
        shell.sendline('conda activate "%s"' % prefix)
        shell.assert_env_var("CONDA_SHLVL", "2\r?")
        shell.assert_env_var("CONDA_PREFIX", prefix, True)

        shell.sendline("conda deactivate")
        PATH = shell.get_env_var("PATH")
        assert "charizard" in PATH
        shell.sendline('conda activate -stack "%s"' % venusaur)
        PATH = shell.get_env_var("PATH")
        assert "venusaur" in PATH
        assert "charizard" in PATH

        print("## [PowerShell integration] Installing.")
        shell.sendline(f"conda install -yq hdf5={HDF5_VERSION}")
        shell.expect("Executing transaction: ...working... done.*\n", timeout=100)
        shell.sendline("$LASTEXITCODE")
        shell.expect("0")
        # TODO: assert that reactivate worked correctly

        print("## [PowerShell integration] Checking installed version.")
        shell.sendline("h5stat --version")
        shell.expect(rf".*h5stat: Version {HDF5_VERSION}.*")

        # conda run integration test
        print("## [PowerShell integration] Checking conda run.")
        shell.sendline(f"conda run {dev_arg} h5stat --version")
        shell.expect(rf".*h5stat: Version {HDF5_VERSION}.*")

        print("## [PowerShell integration] Deactivating")
        shell.sendline("conda deactivate")
        shell.assert_env_var("CONDA_SHLVL", "1\r?")
        shell.sendline("conda deactivate")
        shell.assert_env_var("CONDA_SHLVL", "0\r?")
        shell.sendline("conda deactivate")
        shell.assert_env_var("CONDA_SHLVL", "0\r?")


@pytest.mark.skipif(
    not which_powershell() or not on_win, reason="Windows, PowerShell specific test"
)
@pytest.mark.integration
def test_powershell_PATH_management(shell_wrapper_integration: tuple[str, str, str]):
    prefix, _, _ = shell_wrapper_integration

    posh_kind, posh_path = which_powershell()
    print(f"## [PowerShell activation PATH management] Using {posh_path}.")
    with InteractiveShell(posh_kind) as shell:
        prefix = join(prefix, "envs", "test")
        print("## [PowerShell activation PATH management] Starting test.")
        shell.sendline("(Get-Command conda).CommandType")
        shell.p.expect_exact("Alias")
        shell.sendline("(Get-Command conda).Definition")
        shell.p.expect_exact("Invoke-Conda")
        shell.sendline("(Get-Command Invoke-Conda).Definition")
        shell.p.expect(".*\n")

        shell.sendline("conda deactivate")
        shell.sendline("conda deactivate")

        PATH0 = shell.get_env_var("PATH", "")
        print(f"PATH is {PATH0.split(os.pathsep)}")
        shell.sendline("(Get-Command conda).CommandType")
        shell.p.expect_exact("Alias")
        shell.sendline(f'conda create -yqp "{prefix}" bzip2')
        shell.expect("Executing transaction: ...working... done.*\n")


@pytest.mark.skipif(not which("cmd.exe"), reason="cmd.exe not installed")
@pytest.mark.integration
def test_cmd_exe_basic_integration(shell_wrapper_integration: tuple[str, str, str]):
    prefix, charizard, _ = shell_wrapper_integration

    conda_bat = join(CONDA_PACKAGE_ROOT, "shell", "condabin", "conda.bat")
    with env_vars(
        {
            "PATH": "C:\\Windows\\system32;C:\\Windows;C:\\Windows\\System32\\Wbem;C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\"
        },
        stack_callback=conda_tests_ctxt_mgmt_def_pol,
    ):
        with InteractiveShell("cmd.exe") as shell:
            shell.expect(".*\n")

            shell.assert_env_var("_CE_CONDA", "conda\r")
            shell.assert_env_var("_CE_M", "-m\r")
            shell.assert_env_var("CONDA_EXE", escape(sys.executable) + "\r")

            # We use 'PowerShell' here because 'where conda' returns all of them and
            # p.expect_exact does not do what you would think it does given its name.
            shell.sendline(
                'powershell -NoProfile -c ("get-command conda | Format-List Source")'
            )
            shell.p.expect_exact("Source : " + conda_bat)

            shell.sendline("chcp")
            shell.expect(".*\n")

            PATH0 = shell.get_env_var("PATH", "").split(os.pathsep)
            print(PATH0)
            shell.sendline('conda activate --dev "%s"' % charizard)

            shell.sendline("chcp")
            shell.expect(".*\n")
            shell.assert_env_var("CONDA_SHLVL", "1\r")

            PATH1 = shell.get_env_var("PATH", "").split(os.pathsep)
            print(PATH1)
            shell.sendline(
                'powershell -NoProfile -c ("get-command conda | Format-List Source")'
            )
            shell.p.expect_exact("Source : " + conda_bat)

            shell.assert_env_var("_CE_CONDA", "conda\r")
            shell.assert_env_var("_CE_M", "-m\r")
            shell.assert_env_var("CONDA_EXE", escape(sys.executable) + "\r")
            shell.assert_env_var("CONDA_PREFIX", charizard, True)
            PATH2 = shell.get_env_var("PATH", "").split(os.pathsep)
            print(PATH2)

            shell.sendline(
                'powershell -NoProfile -c ("get-command conda -All | Format-List Source")'
            )
            shell.p.expect_exact("Source : " + conda_bat)

            shell.sendline('conda activate --dev "%s"' % prefix)
            shell.assert_env_var("_CE_CONDA", "conda\r")
            shell.assert_env_var("_CE_M", "-m\r")
            shell.assert_env_var("CONDA_EXE", escape(sys.executable) + "\r")
            shell.assert_env_var("CONDA_SHLVL", "2\r")
            shell.assert_env_var("CONDA_PREFIX", prefix, True)

            # TODO: Make a dummy package and release it (somewhere?)
            #       should be a relatively light package, but also
            #       one that has activate.d or deactivate.d scripts.
            #       More imporant than size or script though, it must
            #       not require an old or incompatible version of any
            #       library critical to the correct functioning of
            #       Python (e.g. OpenSSL).
            shell.sendline(f"conda install -yq hdf5={HDF5_VERSION}")
            shell.expect("Executing transaction: ...working... done.*\n", timeout=100)
            shell.assert_env_var("errorlevel", "0", True)
            # TODO: assert that reactivate worked correctly

            shell.sendline("h5stat --version")
            shell.expect(rf".*h5stat: Version {HDF5_VERSION}.*")

            # conda run integration test
            shell.sendline(f"conda run {dev_arg} h5stat --version")

            shell.expect(rf".*h5stat: Version {HDF5_VERSION}.*")

            shell.sendline("conda deactivate --dev")
            shell.assert_env_var("CONDA_SHLVL", "1\r")
            shell.sendline("conda deactivate --dev")
            shell.assert_env_var("CONDA_SHLVL", "0\r")
            shell.sendline("conda deactivate --dev")
            shell.assert_env_var("CONDA_SHLVL", "0\r")


@pytest.mark.skipif(bash_unsupported(), reason=bash_unsupported_because())
@pytest.mark.integration
def test_bash_activate_error(shell_wrapper_integration: tuple[str, str, str]):
    context.dev = True
    with InteractiveShell("bash") as shell:
        shell.sendline("export CONDA_SHLVL=unaffected")
        if on_win:
            shell.sendline("uname -o")
            shell.expect("(Msys|Cygwin)")
        shell.sendline("conda activate environment-not-found-doesnt-exist")
        shell.expect(
            "Could not find conda environment: environment-not-found-doesnt-exist"
        )
        shell.assert_env_var("CONDA_SHLVL", "unaffected")

        shell.sendline("conda activate -h blah blah")
        shell.expect("usage: conda activate")


@pytest.mark.skipif(not which("cmd.exe"), reason="cmd.exe not installed")
@pytest.mark.integration
def test_cmd_exe_activate_error(shell_wrapper_integration: tuple[str, str, str]):
    context.dev = True
    with InteractiveShell("cmd.exe") as shell:
        shell.sendline("set")
        shell.expect(".*")
        shell.sendline("conda activate --dev environment-not-found-doesnt-exist")
        shell.expect(
            "Could not find conda environment: environment-not-found-doesnt-exist"
        )
        shell.expect(".*")
        shell.assert_env_var("errorlevel", "1\r")

        shell.sendline("conda activate -h blah blah")
        shell.expect("usage: conda activate")


@pytest.mark.flaky(reruns=5)
@pytest.mark.skipif(bash_unsupported(), reason=bash_unsupported_because())
@pytest.mark.integration
def test_legacy_activate_deactivate_bash(
    shell_wrapper_integration: tuple[str, str, str]
):
    prefix, prefix2, prefix3 = shell_wrapper_integration

    with InteractiveShell("bash") as shell:
        # calling bash -l, as we do for MSYS2, may cause conda activation.
        shell.sendline("conda deactivate")
        shell.sendline("conda deactivate")
        shell.sendline("conda deactivate")
        shell.sendline("conda deactivate")
        shell.expect(".*\n")

        activator = PosixActivator()
        CONDA_PACKAGE_ROOT_p = activator.path_conversion(CONDA_PACKAGE_ROOT)
        prefix2_p = activator.path_conversion(prefix2)
        prefix3_p = activator.path_conversion(prefix3)
        shell.sendline("export _CONDA_ROOT='%s/shell'" % CONDA_PACKAGE_ROOT_p)
        shell.sendline(
            f'source "${{_CONDA_ROOT}}/bin/activate" {dev_arg} "{prefix2_p}"'
        )
        PATH0 = shell.get_env_var("PATH")
        assert "charizard" in PATH0

        shell.sendline("type conda")
        shell.expect("conda is a function")

        shell.sendline("conda --version")
        shell.p.expect_exact("conda " + conda_version)

        shell.sendline(
            f'source "${{_CONDA_ROOT}}/bin/activate" {dev_arg} "{prefix3_p}"'
        )

        PATH1 = shell.get_env_var("PATH")
        assert "venusaur" in PATH1

        shell.sendline('source "${_CONDA_ROOT}/bin/deactivate"')
        PATH2 = shell.get_env_var("PATH")
        assert "charizard" in PATH2

        shell.sendline('source "${_CONDA_ROOT}/bin/deactivate"')
        shell.assert_env_var("CONDA_SHLVL", "0")


@pytest.mark.skipif(not which("cmd.exe"), reason="cmd.exe not installed")
@pytest.mark.integration
def test_legacy_activate_deactivate_cmd_exe(
    shell_wrapper_integration: tuple[str, str, str]
):
    prefix, prefix2, prefix3 = shell_wrapper_integration

    with InteractiveShell("cmd.exe") as shell:
        shell.sendline("echo off")

        conda__ce_conda = shell.get_env_var("_CE_CONDA")
        assert conda__ce_conda == "conda"

        PATH = "%s\\shell\\Scripts;%%PATH%%" % CONDA_PACKAGE_ROOT

        shell.sendline("SET PATH=" + PATH)

        shell.sendline('activate --dev "%s"' % prefix2)
        shell.expect(".*\n")

        conda_shlvl = shell.get_env_var("CONDA_SHLVL")
        assert conda_shlvl == "1", conda_shlvl

        PATH = shell.get_env_var("PATH")
        assert "charizard" in PATH

        conda__ce_conda = shell.get_env_var("_CE_CONDA")
        assert conda__ce_conda == "conda"

        shell.sendline("conda --version")
        shell.p.expect_exact("conda " + conda_version)

        shell.sendline('activate.bat --dev "%s"' % prefix3)
        PATH = shell.get_env_var("PATH")
        assert "venusaur" in PATH

        shell.sendline("deactivate.bat --dev")
        PATH = shell.get_env_var("PATH")
        assert "charizard" in PATH

        shell.sendline("deactivate --dev")
        conda_shlvl = shell.get_env_var("CONDA_SHLVL")
        assert conda_shlvl == "0", conda_shlvl


@pytest.fixture(scope="module")
def prefix():
    tempdirdir = gettempdir()

    root_dirname = str(uuid4())[:4] + SPACER_CHARACTER + str(uuid4())[:4]
    root = join(tempdirdir, root_dirname)
    mkdir_p(join(root, "conda-meta"))
    assert isdir(root)
    touch(join(root, "conda-meta", "history"))

    prefix = join(root, "envs", "charizard")
    mkdir_p(join(prefix, "conda-meta"))
    touch(join(prefix, "conda-meta", "history"))

    yield prefix

    rm_rf(root)


@pytest.mark.integration
@pytest.mark.parametrize(
    ["shell"],
    [
        pytest.param(
            "bash",
            marks=pytest.mark.skipif(
                bash_unsupported(), reason=bash_unsupported_because()
            ),
        ),
        pytest.param(
            "cmd.exe",
            marks=pytest.mark.skipif(
                not which("cmd.exe"), reason="cmd.exe not installed"
            ),
        ),
    ],
)
def test_activate_deactivate_modify_path(
    test_recipes_channel: None,
    shell,
    prefix,
    conda_cli: CondaCLIFixture,
):
    original_path = os.environ.get("PATH")
    conda_cli(
        "install",
        *("--prefix", prefix),
        "activate_deactivate_package",
        "--use-local",
        "--yes",
    )

    with InteractiveShell(shell) as sh:
        sh.sendline('conda activate "%s"' % prefix)
        activated_env_path = sh.get_env_var("PATH")
        sh.sendline("conda deactivate")

    assert "teststringfromactivate/bin/test" in activated_env_path
    assert original_path == os.environ.get("PATH")


@pytest.fixture
def create_stackable_envs(tmp_env: TmpEnvFixture):
    # generate stackable environments, two with curl and one without curl
    which = f"{'where' if on_win else 'which -a'} curl"

    class Env:
        def __init__(self, prefix=None, paths=None):
            self.prefix = Path(prefix) if prefix else None

            if not paths:
                if on_win:
                    path = self.prefix / "Library" / "bin" / "curl.exe"
                else:
                    path = self.prefix / "bin" / "curl"

                paths = (path,) if path.exists() else ()
            self.paths = paths

    sys = _run_command(
        "conda config --set auto_activate_base false",
        which,
    )

    with tmp_env("curl") as base, tmp_env("curl") as haspkg, tmp_env() as notpkg:
        yield which, {
            "sys": Env(paths=sys),
            "base": Env(prefix=base),
            "has": Env(prefix=haspkg),
            "not": Env(prefix=notpkg),
        }


def _run_command(*lines):
    # create a custom run command since this is specific to the shell integration
    if on_win:
        join = " && ".join
        source = f"{Path(context.root_prefix, 'condabin', 'conda_hook.bat')}"
    else:
        join = "\n".join
        source = f". {Path(context.root_prefix, 'etc', 'profile.d', 'conda.sh')}"

    marker = uuid4().hex
    script = join((source, *(["conda deactivate"] * 5), f"echo {marker}", *lines))
    output = check_output(script, shell=True).decode().splitlines()
    output = list(map(str.strip, output))
    output = output[output.index(marker) + 1 :]  # trim setup output

    return [Path(path) for path in filter(None, output)]


# see https://github.com/conda/conda/pull/11257#issuecomment-1050531320
@pytest.mark.integration
@pytest.mark.parametrize(
    ("auto_stack", "stack", "run", "expected"),
    [
        # no environments activated
        (0, "", "base", "base,sys"),
        (0, "", "has", "has,sys"),
        (0, "", "not", "sys"),
        # one environment activated, no stacking
        (0, "base", "base", "base,sys"),
        (0, "base", "has", "has,sys"),
        (0, "base", "not", "sys"),
        (0, "has", "base", "base,sys"),
        (0, "has", "has", "has,sys"),
        (0, "has", "not", "sys"),
        (0, "not", "base", "base,sys"),
        (0, "not", "has", "has,sys"),
        (0, "not", "not", "sys"),
        # one environment activated, stacking allowed
        (5, "base", "base", "base,sys"),
        (5, "base", "has", "has,base,sys"),
        (5, "base", "not", "base,sys"),
        (5, "has", "base", "base,has,sys"),
        (5, "has", "has", "has,sys"),
        (5, "has", "not", "has,sys"),
        (5, "not", "base", "base,sys"),
        (5, "not", "has", "has,sys"),
        (5, "not", "not", "sys"),
        # two environments activated, stacking allowed
        (5, "base,has", "base", "base,has,sys" if on_win else "base,has,base,sys"),
        (5, "base,has", "has", "has,base,sys"),
        (5, "base,has", "not", "has,base,sys"),
        (5, "base,not", "base", "base,sys" if on_win else "base,base,sys"),
        (5, "base,not", "has", "has,base,sys"),
        (5, "base,not", "not", "base,sys"),
    ],
)
def test_stacking(create_stackable_envs, auto_stack, stack, run, expected):
    which, envs = create_stackable_envs
    stack = filter(None, stack.split(","))
    expected = filter(None, expected.split(","))
    expected = list(chain.from_iterable(envs[env.strip()].paths for env in expected))
    assert (
        _run_command(
            f"conda config --set auto_stack {auto_stack}",
            *(f'conda activate "{envs[env.strip()].prefix}"' for env in stack),
            f'conda run -p "{envs[run.strip()].prefix}" {which}',
        )
        == expected
    )
