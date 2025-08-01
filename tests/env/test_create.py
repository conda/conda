# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest

from conda.base.context import context, reset_context
from conda.common.compat import on_win
from conda.core.prefix_data import PrefixData
from conda.exceptions import CondaValueError
from conda.testing.integration import package_is_installed

from . import remote_support_file, support_file

if TYPE_CHECKING:
    from pytest import MonkeyPatch

    from conda.testing.fixtures import (
        CondaCLIFixture,
        PathFactoryFixture,
        TmpEnvFixture,
    )


def get_env_vars(prefix):
    pd = PrefixData(prefix)

    env_vars = pd.get_environment_env_vars()

    return env_vars


@pytest.mark.integration
def test_create_update(
    conda_cli: CondaCLIFixture,
    monkeypatch: MonkeyPatch,
    tmp_envs_dir: Path,
):
    env_name = uuid4().hex[:8]
    prefix = tmp_envs_dir / env_name

    conda_cli(
        *("env", "create"),
        *("--name", env_name),
        *("--file", support_file("example/environment_pinned.yml")),
    )
    assert prefix.exists()
    assert package_is_installed(prefix, "python")
    assert package_is_installed(prefix, "flask=2.0.2")

    env_vars = get_env_vars(prefix)
    assert env_vars["FIXED"] == "fixed"
    assert env_vars["CHANGES"] == "original_value"
    assert env_vars["GETS_DELETED"] == "not_actually_removed_though"
    assert "NEW_VAR" not in env_vars

    stdout, stderr, err = conda_cli(
        *("env", "update"),
        *("--name", env_name),
        *("--file", support_file("example/environment_pinned_updated.yml")),
    )
    PrefixData._cache_.clear()
    assert package_is_installed(prefix, "flask=2.0.3")
    assert not package_is_installed(prefix, "flask=2.0.2")

    env_vars = get_env_vars(prefix)
    assert env_vars["FIXED"] == "fixed"
    assert env_vars["CHANGES"] == "updated_value"
    assert env_vars["NEW_VAR"] == "new_var"

    # This ends up sticking around since there is no real way of knowing that an environment
    # variable _used_ to be in the variables dict, but isn't any more.
    assert env_vars["GETS_DELETED"] == "not_actually_removed_though"


@pytest.mark.skip(reason="Need to find an appropriate server to test this on.")
@pytest.mark.integration
def test_create_host_port(
    monkeypatch: MonkeyPatch,
    conda_cli: CondaCLIFixture,
    tmp_envs_dir: Path,
):
    env_name = uuid4().hex[:8]
    prefix = tmp_envs_dir / env_name

    conda_cli(
        *("env", "create"),
        *("--name", env_name),
        *("--file", support_file("example/environment_host_port.yml")),
    )
    assert prefix.exists()
    assert package_is_installed(prefix, "python")
    assert package_is_installed(prefix, "flask=2.0.3")


@pytest.mark.integration
def test_create_advanced_pip(
    monkeypatch: MonkeyPatch,
    conda_cli: CondaCLIFixture,
    tmp_envs_dir: Path,
    support_file_isolated,
):
    env_name = uuid4().hex[:8]
    prefix = tmp_envs_dir / env_name

    # avoid pip touching support_file paths inside source checkout
    environment_yml = support_file_isolated(Path("advanced-pip", "environment.yml"))

    stdout, stderr, _ = conda_cli(
        *("env", "create"),
        *("--name", env_name),
        *("--file", str(environment_yml)),
    )

    PrefixData._cache_.clear()
    assert prefix.exists()
    assert package_is_installed(prefix, "python")
    assert package_is_installed(prefix, "argh")
    assert package_is_installed(prefix, "module-to-install-in-editable-mode")
    assert package_is_installed(prefix, "six")
    assert package_is_installed(prefix, "xmltodict=0.10.2")


@pytest.mark.integration
def test_create_empty_env(
    monkeypatch: MonkeyPatch,
    conda_cli: CondaCLIFixture,
    tmp_envs_dir: Path,
):
    env_name = uuid4().hex[:8]
    prefix = tmp_envs_dir / env_name

    conda_cli(
        *("env", "create"),
        *("--name", env_name),
        *("--file", support_file("empty_env.yml")),
    )
    assert prefix.exists()


@pytest.mark.integration
def test_create_env_default_packages(
    monkeypatch: MonkeyPatch,
    conda_cli: CondaCLIFixture,
    tmp_envs_dir: Path,
):
    # use "cheap" packages with no dependencies
    monkeypatch.setenv("CONDA_CREATE_DEFAULT_PACKAGES", "favicon,zlib")
    reset_context()
    assert context.create_default_packages == ("favicon", "zlib")

    env_name = uuid4().hex[:8]
    prefix = tmp_envs_dir / env_name

    conda_cli(
        *("env", "create"),
        *("--name", env_name),
        *("--file", support_file("env_with_dependencies.yml")),
    )
    assert prefix.exists()
    assert package_is_installed(prefix, "python")
    assert package_is_installed(prefix, "pytz")
    assert package_is_installed(prefix, "favicon")
    assert package_is_installed(prefix, "zlib")


@pytest.mark.integration
def test_create_env_no_default_packages(
    monkeypatch: MonkeyPatch,
    conda_cli: CondaCLIFixture,
    tmp_envs_dir: Path,
):
    # use "cheap" packages with no dependencies
    monkeypatch.setenv("CONDA_CREATE_DEFAULT_PACKAGES", "favicon,zlib")
    reset_context()
    assert context.create_default_packages == ("favicon", "zlib")

    env_name = uuid4().hex[:8]
    prefix = tmp_envs_dir / env_name

    conda_cli(
        *("env", "create"),
        *("--name", env_name),
        *("--file", support_file("env_with_dependencies.yml")),
        "--no-default-packages",
    )
    assert prefix.exists()
    assert package_is_installed(prefix, "python")
    assert package_is_installed(prefix, "pytz")
    assert not package_is_installed(prefix, "favicon")
    assert not package_is_installed(prefix, "zlib")


@pytest.mark.integration
def test_create_update_remote_env_file(
    support_file_server_port,
    monkeypatch: MonkeyPatch,
    conda_cli: CondaCLIFixture,
    tmp_envs_dir: Path,
):
    env_name = uuid4().hex[:8]
    prefix = tmp_envs_dir / env_name

    conda_cli(
        *("env", "create"),
        *("--name", env_name),
        *(
            "--file",
            remote_support_file(
                "example/environment_pinned.yml",
                port=support_file_server_port,
            ),
        ),
    )
    assert prefix.exists()
    assert package_is_installed(prefix, "python")
    assert package_is_installed(prefix, "flask=2.0.2")

    env_vars = get_env_vars(prefix)
    assert env_vars["FIXED"] == "fixed"
    assert env_vars["CHANGES"] == "original_value"
    assert env_vars["GETS_DELETED"] == "not_actually_removed_though"
    assert "NEW_VAR" not in env_vars

    conda_cli(
        *("env", "update"),
        *("--name", env_name),
        *(
            "--file",
            remote_support_file(
                "example/environment_pinned_updated.yml",
                port=support_file_server_port,
            ),
        ),
    )
    PrefixData._cache_.clear()
    assert package_is_installed(prefix, "flask=2.0.3")
    assert not package_is_installed(prefix, "flask=2.0.2")

    env_vars = get_env_vars(prefix)
    assert env_vars["FIXED"] == "fixed"
    assert env_vars["CHANGES"] == "updated_value"
    assert env_vars["NEW_VAR"] == "new_var"

    # This ends up sticking around since there is no real way of knowing that an environment
    # variable _used_ to be in the variables dict, but isn't any more.
    assert env_vars["GETS_DELETED"] == "not_actually_removed_though"


@pytest.mark.skipif(on_win, reason="Test is invalid on Windows")
def test_fail_to_create_env_in_dir_with_colon(
    tmp_path: Path, conda_cli: CondaCLIFixture
):
    # Add a directory with a colon
    colon_dir = tmp_path / "fake:dir"
    colon_dir.mkdir()

    with pytest.raises(
        CondaValueError,
        match="Environment paths cannot contain ':'.",
    ):
        conda_cli("create", f"--prefix={colon_dir}/tester")


@pytest.mark.parametrize(
    "env_file",
    ["example/environment.yml", "example/environment_with_pip.yml"],
)
def test_create_env_json(
    env_file,
    conda_cli: CondaCLIFixture,
    path_factory: PathFactoryFixture,
):
    prefix = path_factory()
    stdout, stderr, err = conda_cli(
        *("env", "update"),
        *("--prefix", prefix),
        *("--file", support_file(env_file)),
        "--json",
    )

    for string in stdout and stdout.split("\0") or ():
        json.loads(string)


def test_protected_dirs_error_for_env_create(
    conda_cli: CondaCLIFixture, tmp_env: TmpEnvFixture
):
    with tmp_env() as prefix:
        with pytest.raises(
            CondaValueError,
            match="Environment paths cannot be immediately nested under another conda environment",
        ):
            conda_cli(
                "env",
                "create",
                f"--prefix={prefix}/envs",
                "--file",
                support_file("example/environment_pinned.yml"),
            )


def test_create_env_from_non_existent_plugin(
    conda_cli: CondaCLIFixture,
    tmp_env: TmpEnvFixture,
    monkeypatch: MonkeyPatch,
):
    monkeypatch.setenv("CONDA_ENVIRONMENT_SPECIFIER", "nonexistent_plugin")
    with tmp_env() as prefix:
        with pytest.raises(
            CondaValueError,
        ) as excinfo:
            conda_cli(
                "env",
                "create",
                f"--prefix={prefix}/envs",
                "--file",
                support_file("example/environment_pinned.yml"),
            )

        assert (
            "You have chosen an unrecognized environment specifier type (nonexistent_plugin)"
            in str(excinfo.value)
        )


def test_create_env_custom_platform(
    conda_cli: CondaCLIFixture,
    tmp_env: TmpEnvFixture,
    path_factory: PathFactoryFixture,
    test_recipes_channel: str,
):
    """
    Ensures that the `--platform` option works correctly when creating an environment by
    creating a `.condarc` file with `subir: osx-64`.
    """
    env_file = path_factory("test_recipes_channel.yml")
    env_file.write_text(
        f"""
        name: test-env
        channels:
          - {test_recipes_channel}
        dependencies:
          - dependency
        """
    )

    if context._native_subdir() == "osx-arm64":
        platform = "linux-64"
    else:
        platform = "osx-arm64"

    with tmp_env() as prefix:
        conda_cli(
            "env",
            "create",
            f"--prefix={prefix}",
            "--file",
            str(env_file),
            f"--platform={platform}",
        )
        prefix_data = PrefixData(prefix)

        assert prefix_data.exists()
        assert prefix_data.is_environment()

        config = prefix / ".condarc"

        assert config.is_file()
        assert f"subdir: {platform}" in config.read_text()
