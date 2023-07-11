# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import os
import uuid
from argparse import Namespace
from pathlib import Path, PurePath
from typing import Iterable

import pytest
from pytest import MonkeyPatch

from conda import plugins
from conda.base.constants import ROOT_ENV_NAME
from conda.base.context import conda_tests_ctxt_mgmt_def_pol, context
from conda.common.io import env_vars
from conda.exceptions import (
    CondaEnvException,
    DirectoryNotACondaEnvironmentError,
    EnvironmentNameNotFound,
)
from conda.plugins.shells.shell_cli import execute, get_parsed_args
from conda.testing import (
    CondaCLIFixture,
    TmpEnvFixture,
    conda_cli,
    path_factory,
    tmp_env,
)
from conda.testing.helpers import run_inprocess_conda_command as run
from conda.testing.integration import make_temp_env
from tests.plugins.conftest import plugin_manager


class ShellPlugin:
    """
    Yield the shell subcommand hook.
    Method: conda_subcommands
    """

    def conda_subcommands():
        yield plugins.CondaSubcommand(
            name="shell",
            summary="Run plugins used for activate, deactivate, and reactivate",
            action=execute,
        )


@pytest.fixture
def conda_shell(plugin_manager) -> plugin_manager:
    """Load shell plugin and entry point"""
    plugin_manager.load_plugins(ShellPlugin)
    plugin_manager.load_entrypoints("subcommands")
    return plugin_manager


@pytest.fixture
def env_one(conda_cli: CondaCLIFixture) -> Iterable[str]:
    """Create environment with no packages"""
    # Setup
    name = uuid.uuid4().hex
    conda_cli("create", "--name", name, "--yes")

    yield name

    # Teardown
    conda_cli("remove", "--all", "--yes", "--name", name)


@pytest.fixture
def env_two_gdal(conda_cli: CondaCLIFixture) -> Iterable[str]:
    """Create environment with gdal package"""
    # Setup
    name = uuid.uuid4().hex
    conda_cli("create", "--name", name, "gdal", "--yes")

    yield name

    # Teardown
    conda_cli("remove", "--all", "--yes", "--name", name)


VALIDATE_GET_PARSED_ARGS_TEST_CASES = (
    (["activate"], ("activate", False, False, None)),
    (["activate", "test_env"], ("activate", False, False, "test_env")),
    (["reactivate"], ("reactivate", False, None, None)),
    (["reactivate", "--dev"], ("reactivate", True, None, None)),
    (["deactivate"], ("deactivate", False, None, None)),
    (["deactivate", "--dev"], ("deactivate", True, None, None)),
    (["activate", "--dev", "test_env"], ("activate", True, False, "test_env")),
    (
        ["activate", "--dev", "--stack", "test_env"],
        ("activate", True, True, "test_env"),
    ),
    (["activate", "--dev", "--no-stack", "base"], ("activate", True, False, "base")),
    (["activate", "--stack", "base"], ("activate", False, True, "base")),
    (["activate", "--no-stack", "test_env"], ("activate", False, False, "test_env")),
)


@pytest.mark.parametrize("a, expected", VALIDATE_GET_PARSED_ARGS_TEST_CASES)
def test_get_parsed_args(a: list, expected: tuple):
    """Test that the correct Namespace is returned for the given arguments"""
    ns = get_parsed_args(a)

    assert ns.command == expected[0]
    assert ns.dev == expected[1]
    assert getattr(ns, "stack", None) == expected[2]
    assert getattr(ns, "env", None) == expected[3]


VALIDATE_GET_PARSED_ARGS_ERROR_TEST_CASES = (
    (["katherine"], "invalid choice: 'katherine'"),
    (["--dev", "reactivate"], "unrecognized arguments"),
)


@pytest.mark.parametrize("a, expected", VALIDATE_GET_PARSED_ARGS_ERROR_TEST_CASES)
def test_get_parsed_args_error(a: list, expected: tuple, capsys):
    with pytest.raises(SystemExit):
        get_parsed_args(a)
    captured = capsys.readouterr()
    assert expected in captured.err


def test_get_parsed_args_help_flag(capsys):
    with pytest.raises(SystemExit):
        get_parsed_args(["-h"])
    captured = capsys.readouterr()
    assert "Process conda activate, deactivate, and reactivate" in captured.out


# sysexit with code 2 instead of 0
# help output coming up in stderr instead of stdout
# based on output the name of the function ("test_shell_show_help") is somehow being
# processed as the command instead of the help flag: seems to actually be the name
# of the temp directory
def test_shell_show_help(conda_cli: conda_cli, capsys):
    """Make sure that we are able to run ``conda shell`` command with the --help flag"""
    with pytest.raises(SystemExit) as err:
        conda_cli("shell", "-h")

    print(err)
    captured = capsys.readouterr()
    assert "Process conda activate, deactivate, and reactivate" in captured.out
    assert err.value.code == 0


# getting 'invalid choice' error message
# name of temp directory is being processed as the command instead of "activate"
def test_shell_activate_cli_env(conda_cli, env_one):
    """Make sure that we are able to call the ``conda shell activate`` command"""
    out, err, code = conda_cli("shell", "activate", env_one)

    assert not err
    assert not code


# getting 'invalid choice' error message
# path to directory with conda code is being processed as the command instead of "activate"
# still happens with 1-3 arguments between "shell" and "activate"
def test_shell_activate_cli(conda_cli):
    """Make sure that we are able to call the ``conda shell activate`` command"""
    out, err, code = conda_cli("shell", "activate")

    assert not err
    assert not code


# issue initializing context
def test_shell_activate_with_clean_env(env_one, monkeypatch):
    """Make sure that we are able to call `conda shell activate`` command for a specific environment"""

    run(f"conda shell activate --dev {env_one}")
    out, err, code = run(f"conda info")

    assert env_one in out
    assert not err
    assert not code
    assert PurePath(os.environ["CONDA_PREFIX"]).name == env_one


# issue initializing context
def test_shell_deactivate_cli(env_one):
    """Make sure that we are able to call the ``conda shell deactivate`` command"""

    # activate temp env
    run(f"conda shell activate --dev {env_one}")
    assert os.environ["CONDA_PREFIX"] == env_one

    # testing deactivate
    run(f"conda shell deactivate --dev")
    out1, err1, code1 = run(f"conda info")

    assert "devenv" in out1
    assert not err1  # no error message
    assert not code1  # successful exit code
    assert "devenv" in PurePath(os.environ["CONDA_PREFIX"]).name


# how do we test reactivate???
def test_shell_reactivate_cli():
    """Make sure that we are able to call the ``conda shell reactivate`` command"""

    run(f"conda shell reactivate --dev")
    out, err, code = run(f"conda info")

    assert "devenv" in out
    assert not err  # no error message
    assert not code  # successful exit code


def test_shell_other_cli_command_error():
    """Make sure that a different cli command generates an error"""
    with pytest.raises(Exception, match="invalid choice: 'puppy'"):
        run(f"conda shell puppy")


def test_shell_cli_show_help():
    """Make sure that we are able to run ``conda shell`` command with the --help flag"""

    out, err, code = run(f"conda shell -h")

    assert "Process conda activate, deactivate, and reactivate" in out
    assert not err  # no error message
    assert not code  # successful exit code
