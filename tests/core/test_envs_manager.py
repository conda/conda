# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import os
from logging import getLogger
from os.path import isdir, join
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from conda.auxlib.collection import AttrDict
from conda.base.constants import PREFIX_MAGIC_FILE
from conda.base.context import conda_tests_ctxt_mgmt_def_pol, context, reset_context
from conda.common.compat import on_win
from conda.common.io import env_var
from conda.common.path import expand, paths_equal
from conda.core.envs_manager import (
    _clean_environments_txt,
    get_user_environments_txt_file,
    list_all_known_prefixes,
    register_env,
    set_environment_no_site_packages,
    unregister_env,
)
from conda.gateways.disk import mkdir_p
from conda.gateways.disk.read import yield_lines
from conda.gateways.disk.update import touch

log = getLogger(__name__)


def test_register_unregister_location_env(tmp_path: Path):
    user_environments_txt_file = get_user_environments_txt_file()
    if (
        not os.path.exists(user_environments_txt_file)
        or user_environments_txt_file == os.devnull
    ):
        pytest.skip(
            f"user environments.txt file {user_environments_txt_file} does not exist"
        )

    gascon_location = join(tmp_path, "gascon")
    touch(join(gascon_location, PREFIX_MAGIC_FILE), mkdir=True)
    assert gascon_location not in list_all_known_prefixes()

    touch(user_environments_txt_file, mkdir=True, sudo_safe=True)
    with env_var(
        "CONDA_REGISTER_ENVS",
        "true",
        stack_callback=conda_tests_ctxt_mgmt_def_pol,
    ):
        register_env(gascon_location)
    assert gascon_location in yield_lines(user_environments_txt_file)
    assert (
        len(
            tuple(
                x
                for x in yield_lines(user_environments_txt_file)
                if paths_equal(gascon_location, x)
            )
        )
        == 1
    )

    register_env(gascon_location)  # should be completely idempotent
    assert (
        len(
            tuple(
                x
                for x in yield_lines(user_environments_txt_file)
                if x == gascon_location
            )
        )
        == 1
    )

    unregister_env(gascon_location)
    assert gascon_location not in list_all_known_prefixes()
    unregister_env(gascon_location)  # should be idempotent
    assert gascon_location not in list_all_known_prefixes()


def test_prefix_cli_flag(tmp_path: Path):
    envs_dirs = (
        join(tmp_path, "first-envs-dir"),
        join(tmp_path, "seconds-envs-dir"),
    )
    with env_var(
        "CONDA_ENVS_DIRS",
        os.pathsep.join(envs_dirs),
        stack_callback=conda_tests_ctxt_mgmt_def_pol,
    ):
        # even if prefix doesn't exist, it can be a target prefix
        reset_context((), argparse_args=AttrDict(prefix="./blarg", func="create"))
        target_prefix = join(os.getcwd(), "blarg")
        assert context.target_prefix == target_prefix
        assert not isdir(target_prefix)


def test_rewrite_environments_txt_file(tmp_path: Path):
    mkdir_p(join(tmp_path, "conda-meta"))
    touch(join(tmp_path, "conda-meta", "history"))
    doesnt_exist = join(tmp_path, "blarg")
    environments_txt_path = join(tmp_path, "environments.txt")
    with open(environments_txt_path, "w") as fh:
        fh.write(f"{tmp_path}\n")
        fh.write(f"{doesnt_exist}\n")
    cleaned_1 = _clean_environments_txt(environments_txt_path)
    assert cleaned_1 == (str(tmp_path),)
    with patch("conda.core.envs_manager._rewrite_environments_txt") as _rewrite_patch:
        cleaned_2 = _clean_environments_txt(environments_txt_path)
        assert cleaned_2 == (str(tmp_path),)
        assert _rewrite_patch.call_count == 0


@patch("conda.core.envs_manager.context")
@patch("conda.core.envs_manager.get_user_environments_txt_file")
@patch("conda.core.envs_manager._clean_environments_txt")
def test_list_all_known_prefixes_with_permission_error(
    mock_clean_env, mock_get_user_env, mock_context, tmp_path
):
    # Mock context
    myenv_dir = tmp_path / "envs"
    myenv_dir.mkdir()
    mock_context.envs_dirs = str(myenv_dir)
    mock_context.root_prefix = "root_prefix"
    # Mock get_user_environments_txt_file to return a file
    env_txt_file = tmp_path / "environment.txt"
    touch(env_txt_file)
    mock_get_user_env.return_value = env_txt_file
    # Mock _clean_environments_txt to raise PermissionError
    mock_clean_env.side_effect = PermissionError()
    all_env_paths = list_all_known_prefixes()
    # On Windows, all_env_paths can contain more paths (like '\\Miniconda')
    assert "root_prefix" in all_env_paths


@pytest.mark.skipif(on_win, reason="test is invalid on windows")
@patch("conda.core.envs_manager.context")
@patch("conda.core.envs_manager._clean_environments_txt")
@patch("pwd.getpwall")
@patch("conda.core.envs_manager.is_admin")
def test_list_all_known_prefixes_with_none_values_error(
    mock_is_admin, mock_getpwall, mock_clean_env, mock_context, tmp_path
):
    """
    Regression test for a bug first indentified in this issue: https://github.com/conda/conda/issues/12063

    Tests to make sure that `None` values are filtered out of the `search_dirs` variable in the
    `list_all_known_prefixes` function.
    """
    mock_is_admin.return_value = True
    mock_getpwall.return_value = [
        SimpleNamespace(pw_dir=expand("~")),
        SimpleNamespace(pw_dir=None),
    ]
    mock_clean_env.return_value = []
    mock_env_dir = tmp_path / "envs"
    mock_env_dir.mkdir()
    mock_context.envs_dirs = str(mock_env_dir)
    mock_context.root_prefix = str(tmp_path)

    results = list_all_known_prefixes()

    assert results == [mock_context.root_prefix]


def test_register_env_directory_creation_error(mocker):
    """
    Test for the error case when we are unable to create
    """
    mock_context = mocker.patch("conda.core.envs_manager.context")
    mock_makedirs = mocker.patch("conda.core.envs_manager.os.makedirs")
    mock_log = mocker.patch("conda.core.envs_manager.log")
    mocker.patch("conda.core.envs_manager.open")

    mock_context.register_envs = True
    mock_makedirs.side_effect = OSError("test")

    value = register_env("test")
    conda_dir = os.path.dirname(get_user_environments_txt_file())

    assert value is None
    assert len(mock_log.warn.mock_calls) == 1

    mock_call, *_ = mock_log.warn.mock_calls

    assert f"Could not create {conda_dir}" in mock_call.args[0]


def test_set_environment_no_site_packages(tmpdir):
    """
    Ensure that the ``pyvenv.cfg`` file is created in the expected location with the expected
    file contents.
    """
    set_environment_no_site_packages(tmpdir)

    config_file = tmpdir / "pyvenv.cfg"

    assert config_file.exists()
    assert config_file.open().read() == "include-system-site-packages = false\n"


def test_set_environment_no_site_packages_remove(tmpdir):
    """
    Ensure that the ``pyvenv.cfg`` is removed when remove = True is passed.
    """
    config_file = tmpdir / "pyvenv.cfg"
    config_file.open("w").write("include-system-site-packages = false\n")

    set_environment_no_site_packages(tmpdir, remove=True)

    config_file = tmpdir / "pyvenv.cfg"

    assert not config_file.exists()


def test_set_environment_no_site_packages_error(mocker, tmpdir):
    """
    Ensure we call the logger when an error is encountered. This will happen on
    the ``path.unlink`` call
    """
    path_mock = mocker.patch("conda.core.envs_manager.Path")
    log_mock = mocker.patch("conda.core.envs_manager.log")
    path_mock().unlink.side_effect = OSError("test")

    config_file = tmpdir / "pyvenv.cfg"
    config_file.open("w").write("include-system-site-packages = false\n")

    set_environment_no_site_packages(tmpdir, remove=True)

    assert log_mock.info.mock_calls == [
        mocker.call(
            'Unable to set "no-python-site-packages" for environment. Reason: test'
        )
    ]
