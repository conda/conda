# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest

from conda.base.context import context
from conda.common.serialize import yaml_safe_dump, yaml_safe_load
from conda.exceptions import (
    CondaEnvException,
    DryRunExit,
    EnvironmentFileExtensionNotValid,
    EnvironmentFileNotFound,
    EnvironmentLocationNotFound,
    PackagesNotFoundError,
    ResolvePackageNotFound,
    SpecNotFound,
)
from conda.gateways.disk.test import is_conda_environment
from conda.testing.integration import package_is_installed

if TYPE_CHECKING:
    from collections.abc import Iterator

    from pytest import MonkeyPatch

    from conda.testing.fixtures import (
        CondaCLIFixture,
        PathFactoryFixture,
        TmpEnvFixture,
    )

pytestmark = pytest.mark.usefixtures("parametrized_solver_fixture")

# Environment names we use during our tests
TEST_ENV1 = "env1"

# Environment config files we use for our tests
ENVIRONMENT_CA_CERTIFICATES = yaml_safe_dump(
    {
        "name": TEST_ENV1,
        "dependencies": ["ca-certificates"],
        "channels": context.channels,
    }
)

ENVIRONMENT_CA_CERTIFICATES_WITH_VARIABLES = yaml_safe_dump(
    {
        "name": TEST_ENV1,
        "dependencies": ["ca-certificates"],
        "channels": context.channels,
        "variables": {
            "DUDE": "woah",
            "SWEET": "yaaa",
            "API_KEY": "AaBbCcDd===EeFf",
        },
    }
)

ENVIRONMENT_CA_CERTIFICATES_ZLIB = yaml_safe_dump(
    {
        "name": TEST_ENV1,
        "dependencies": ["ca-certificates", "zlib"],
        "channels": context.channels,
    }
)

ENVIRONMENT_PIP_CLICK = yaml_safe_dump(
    {
        "name": TEST_ENV1,
        "dependencies": ["pip>=23", {"pip": ["click"]}],
        "channels": context.channels,
    }
)

ENVIRONMENT_PIP_CLICK_ATTRS = yaml_safe_dump(
    {
        "name": TEST_ENV1,
        "dependencies": ["pip>=23", {"pip": ["click", "attrs"]}],
        "channels": context.channels,
    }
)

ENVIRONMENT_PIP_NONEXISTING = yaml_safe_dump(
    {
        "name": TEST_ENV1,
        "dependencies": ["pip>=23", {"pip": ["nonexisting_"]}],
        "channels": context.channels,
    }
)

ENVIRONMENT_UNSOLVABLE = yaml_safe_dump(
    {
        "name": TEST_ENV1,
        "dependencies": ["does-not-exist"],
        "channels": context.channels,
    }
)


def create_env(content, filename="environment.yml"):
    Path(filename).write_text(content)


@pytest.fixture(autouse=True)
def chdir(tmp_path: Path, monkeypatch: MonkeyPatch) -> Iterator[Path]:
    """
    Change directories to a temporary directory for `conda env` commands since they are
    sensitive to the current working directory.
    """
    monkeypatch.chdir(tmp_path)
    yield tmp_path


@pytest.mark.integration
def test_conda_env_create_no_file(conda_cli: CondaCLIFixture):
    """
    Test `conda env create` without an environment.yml file
    Should fail
    """
    with pytest.raises(EnvironmentFileNotFound):
        conda_cli("env", "create")


@pytest.mark.integration
def test_conda_env_create_no_existent_file(conda_cli: CondaCLIFixture):
    """
    Test `conda env create --file=not_a_file.txt` with a file that does not
    exist.
    """
    with pytest.raises(EnvironmentFileNotFound):
        conda_cli("env", "create", "--file=not_a_file.txt")


@pytest.mark.integration
def test_conda_env_create_no_existent_file_with_name(conda_cli: CondaCLIFixture):
    """
    Test `conda env create --file=not_a_file.txt` with a file that does not
    exist.
    """
    with pytest.raises(EnvironmentFileNotFound):
        conda_cli("env", "create", "--file=not_a_file.txt", "--name=foo")


@pytest.mark.integration
def test_deprecated_binstar(conda_cli: CondaCLIFixture):
    """
    Test retrieving an environment using the BinstarSpec (i.e. it retrieves it from anaconda.org)

    This tests the `remote_origin` command line argument.
    """
    with pytest.warns(FutureWarning), pytest.raises(EnvironmentFileNotFound):
        conda_cli("env", "create", "conda-test/env-remote")

    with pytest.warns(FutureWarning), pytest.raises(EnvironmentFileNotFound):
        conda_cli("env", "update", "conda-test/env-remote")


@pytest.mark.integration
def test_create_valid_env(path_factory: PathFactoryFixture, conda_cli: CondaCLIFixture):
    """
    Creates an environment.yml file and
    creates an environment with it
    """
    create_env(ENVIRONMENT_CA_CERTIFICATES)
    prefix = path_factory()
    conda_cli(
        "env",
        "create",
        f"--prefix={prefix}",
        # "--file=environment.yml",  # this is the implied default
    )
    assert is_conda_environment(prefix)
    assert package_is_installed(prefix, "ca-certificates")


@pytest.mark.integration
def test_create_unsolvable_env(
    path_factory: PathFactoryFixture, conda_cli: CondaCLIFixture
):
    """
    Creates an environment.yml file and
    fails to solve the environment
    """
    create_env(ENVIRONMENT_UNSOLVABLE)
    prefix = path_factory()
    conda_cli(
        "env",
        "create",
        f"--prefix={prefix}",
        # "--file=environment.yml",  # this is the implied default
        raises=(PackagesNotFoundError, ResolvePackageNotFound),
    )
    assert not is_conda_environment(prefix)


@pytest.mark.integration
def test_create_dry_run_yaml(
    path_factory: PathFactoryFixture, conda_cli: CondaCLIFixture
):
    prefix = path_factory()
    create_env(ENVIRONMENT_CA_CERTIFICATES)
    stdout, _, _ = conda_cli("env", "create", f"--prefix={prefix}", "--dry-run")
    assert not is_conda_environment(prefix)

    # Find line where the YAML output starts (stdout might change if plugins involved)
    lines = stdout.splitlines()
    for lineno, line in enumerate(lines):
        if line.startswith("name:"):
            break
    else:
        pytest.fail("Didn't find YAML data in output")

    output = yaml_safe_load("\n".join(lines[lineno:]))
    assert output["name"] == "env1"
    assert len(output["dependencies"]) > 0


@pytest.mark.integration
def test_create_dry_run_json(
    path_factory: PathFactoryFixture, tmp_path: Path, conda_cli: CondaCLIFixture
):
    prefix = path_factory()
    assert not is_conda_environment(prefix)

    env_file = tmp_path / "environment.yml"
    create_env(ENVIRONMENT_CA_CERTIFICATES, filename=str(env_file))
    assert env_file.is_file()

    stdout, _, _ = conda_cli(
        "env",
        "create",
        f"--file={env_file}",
        f"--prefix={prefix}",
        "--dry-run",
        "--json",
    )
    assert not is_conda_environment(prefix)

    output = json.loads(stdout)
    # assert that the name specified in the environment file matches output
    assert output.get("name") == "env1"
    assert len(output["dependencies"])


@pytest.mark.integration
def test_create_valid_env_with_variables(
    path_factory: PathFactoryFixture, conda_cli: CondaCLIFixture
):
    """
    Creates an environment.yml file and
    creates and environment with it
    """
    prefix = path_factory()
    create_env(ENVIRONMENT_CA_CERTIFICATES_WITH_VARIABLES)
    conda_cli("env", "create", f"--prefix={prefix}")
    assert is_conda_environment(prefix)

    stdout, _, _ = conda_cli(
        *("env", "config", "vars", "list"),
        f"--prefix={prefix}",
        "--json",
    )
    output_env_vars = json.loads(stdout)
    assert output_env_vars == {
        "DUDE": "woah",
        "SWEET": "yaaa",
        "API_KEY": "AaBbCcDd===EeFf",
    }

    assert is_conda_environment(prefix)


@pytest.mark.integration
def test_conda_env_create_empty_file(
    conda_cli: CondaCLIFixture, path_factory: PathFactoryFixture
):
    """Test `conda env create --file=file_name.yml` where file_name.yml is empty."""
    tmp_file = path_factory(suffix=".yml")
    tmp_file.touch()

    with pytest.raises(SpecNotFound):
        conda_cli("env", "create", f"--file={tmp_file}")


@pytest.mark.integration
def test_conda_env_create_http(conda_cli: CondaCLIFixture, tmp_path: Path):
    """Test `conda env create --file=https://some-website.com/environment.yml`."""
    conda_cli(
        *("env", "create"),
        f"--prefix={tmp_path}",
        "--file=https://raw.githubusercontent.com/conda/conda/main/tests/env/support/simple.yml",
    )
    assert (tmp_path / "conda-meta" / "history").is_file()


@pytest.mark.integration
def test_update(path_factory: PathFactoryFixture, conda_cli: CondaCLIFixture):
    prefix = path_factory()
    create_env(ENVIRONMENT_CA_CERTIFICATES)
    conda_cli("env", "create", f"--prefix={prefix}")

    create_env(ENVIRONMENT_CA_CERTIFICATES_ZLIB)
    conda_cli("env", "update", f"--prefix={prefix}")

    stdout, _, _ = conda_cli("list", f"--prefix={prefix}", "zlib", "--json")
    parsed = json.loads(stdout)
    assert parsed
    assert json.loads(stdout)


@pytest.mark.integration
def test_name_override(conda_cli: CondaCLIFixture):
    """
    # smoke test for gh-254
    Test that --name can override the `name` key inside an environment.yml
    """
    create_env(ENVIRONMENT_CA_CERTIFICATES)
    conda_cli("env", "create", "--file=environment.yml", "--name=test_env", "--yes")

    stdout, _, _ = conda_cli("info", "--json")

    parsed = json.loads(stdout)
    assert [env for env in parsed["envs"] if env.endswith("test_env")]


@pytest.mark.integration
def test_create_valid_env_json_output(
    path_factory: PathFactoryFixture, conda_cli: CondaCLIFixture
):
    """
    Creates an environment from an environment.yml file with conda packages (no pip)
    Check the json output
    """
    prefix = path_factory()
    create_env(ENVIRONMENT_CA_CERTIFICATES)
    stdout, _, _ = conda_cli(
        "env", "create", f"--prefix={prefix}", "--quiet", "--json", "--yes"
    )
    output = json.loads(stdout)
    assert output["success"] is True
    assert len(output["actions"]["LINK"]) > 0
    assert "PIP" not in output["actions"]


@pytest.mark.integration
def test_create_valid_env_with_conda_and_pip_json_output(
    path_factory: PathFactoryFixture, conda_cli: CondaCLIFixture
):
    """
    Creates an environment from an environment.yml file with conda and pip dependencies
    Check the json output
    """
    prefix = path_factory()
    create_env(ENVIRONMENT_PIP_CLICK)
    stdout, _, _ = conda_cli(
        "env", "create", f"--prefix={prefix}", "--quiet", "--json", "--yes"
    )
    output = json.loads(stdout)
    assert len(output["actions"]["LINK"]) > 0
    assert output["actions"]["PIP"][0].startswith("click")


@pytest.mark.integration
def test_update_env_json_output(
    path_factory: PathFactoryFixture, conda_cli: CondaCLIFixture
):
    """
    Update an environment by adding a conda package
    Check the json output
    """
    prefix = path_factory()
    create_env(ENVIRONMENT_CA_CERTIFICATES)
    conda_cli("env", "create", f"--prefix={prefix}", "--json", "--yes")
    create_env(ENVIRONMENT_CA_CERTIFICATES_ZLIB)
    stdout, _, _ = conda_cli("env", "update", f"--prefix={prefix}", "--quiet", "--json")
    output = json.loads(stdout)
    assert output["success"] is True
    assert len(output["actions"]["LINK"]) > 0
    assert "PIP" not in output["actions"]


@pytest.mark.integration
def test_update_env_only_pip_json_output(
    path_factory: PathFactoryFixture, conda_cli: CondaCLIFixture, request
):
    """
    Update an environment by adding only a pip package
    Check the json output
    """
    request.applymarker(
        pytest.mark.xfail(
            context.solver == "libmamba",
            reason="Known issue: https://github.com/conda/conda-libmamba-solver/issues/320",
        )
    )
    prefix = path_factory()
    create_env(ENVIRONMENT_PIP_CLICK)
    conda_cli("env", "create", f"--prefix={prefix}", "--json", "--yes")
    create_env(ENVIRONMENT_PIP_CLICK_ATTRS)
    stdout, _, _ = conda_cli("env", "update", f"--prefix={prefix}", "--quiet", "--json")
    output = json.loads(stdout)
    assert output["success"] is True
    # No conda actions (FETCH/LINK), only pip
    assert list(output["actions"].keys()) == ["PIP"]
    # Only attrs installed
    assert len(output["actions"]["PIP"]) == 1
    assert output["actions"]["PIP"][0].startswith("attrs")


@pytest.mark.integration
def test_update_env_no_action_json_output(
    path_factory: PathFactoryFixture, conda_cli: CondaCLIFixture, request
):
    """
    Update an already up-to-date environment
    Check the json output
    """
    prefix = path_factory()
    request.applymarker(
        pytest.mark.xfail(
            context.solver == "libmamba",
            reason="Known issue: https://github.com/conda/conda-libmamba-solver/issues/320",
        )
    )
    create_env(ENVIRONMENT_PIP_CLICK)
    conda_cli("env", "create", f"--prefix={prefix}", "--json", "--yes")
    stdout, _, _ = conda_cli("env", "update", f"--prefix={prefix}", "--quiet", "--json")
    output = json.loads(stdout)
    assert output["message"] == "All requested packages already installed."


@pytest.mark.integration
def test_remove_dry_run(path_factory: PathFactoryFixture, conda_cli: CondaCLIFixture):
    # Test for GH-10231
    prefix = path_factory()
    create_env(ENVIRONMENT_CA_CERTIFICATES)
    conda_cli("env", "create", f"--prefix={prefix}")
    assert is_conda_environment(prefix)

    with pytest.raises(DryRunExit):
        conda_cli("env", "remove", f"--prefix={prefix}", "--dry-run")


@pytest.mark.integration
def test_set_unset_env_vars(
    path_factory: PathFactoryFixture, conda_cli: CondaCLIFixture
):
    create_env(ENVIRONMENT_CA_CERTIFICATES)
    prefix = path_factory()

    conda_cli("env", "create", f"--prefix={prefix}")
    conda_cli(
        *("env", "config", "vars", "set"),
        f"--prefix={prefix}",
        "DUDE=woah",
        "SWEET=yaaa",
        "API_KEY=AaBbCcDd===EeFf",
    )
    stdout, _, _ = conda_cli(
        *("env", "config", "vars", "list"),
        f"--prefix={prefix}",
        "--json",
    )
    output_env_vars = json.loads(stdout)
    assert output_env_vars == {
        "DUDE": "woah",
        "SWEET": "yaaa",
        "API_KEY": "AaBbCcDd===EeFf",
    }

    conda_cli(
        *("env", "config", "vars", "unset"),
        f"--prefix={prefix}",
        "DUDE",
        "SWEET",
        "API_KEY",
    )
    stdout, _, _ = conda_cli(
        *("env", "config", "vars", "list"),
        f"--prefix={prefix}",
        "--json",
    )
    output_env_vars = json.loads(stdout)
    assert output_env_vars == {}


@pytest.mark.integration
def test_set_unset_env_vars_env_no_exist(conda_cli: CondaCLIFixture):
    with pytest.raises(EnvironmentLocationNotFound):
        conda_cli(
            *("env", "config", "vars", "set"),
            f"--name={uuid4().hex}",
            "DUDE=woah",
            "SWEET=yaaa",
            "API_KEY=AaBbCcDd===EeFf",
        )


@pytest.mark.integration
def test_pip_error_is_propagated(
    path_factory: PathFactoryFixture, conda_cli: CondaCLIFixture
):
    """
    Creates an environment from an environment.yml file with conda and incorrect pip dependencies
    The output must clearly show pip error.
    """
    prefix = path_factory()

    create_env(ENVIRONMENT_PIP_NONEXISTING)
    with pytest.raises(CondaEnvException, match="Pip failed"):
        conda_cli("env", "create", f"--prefix={prefix}")


@pytest.mark.integration
def test_env_export(
    tmp_env: TmpEnvFixture, conda_cli: CondaCLIFixture, path_factory: PathFactoryFixture
):
    """Test conda env export."""
    with tmp_env("zlib") as prefix:
        assert is_conda_environment(prefix)

        stdout, _, _ = conda_cli("env", "export", f"--prefix={prefix}")

        env_yml = path_factory(suffix=".yml")
        env_yml.write_text(stdout)

        conda_cli("env", "remove", f"--prefix={prefix}", "--yes")
        assert not is_conda_environment(prefix)
        conda_cli("env", "create", f"--prefix={prefix}", f"--file={env_yml}", "--yes")
        assert is_conda_environment(prefix)

        # regression test for #6220
        stdout, stderr, _ = conda_cli(
            "env", "export", f"--prefix={prefix}", "--no-builds"
        )
        assert not stderr
        env_description = yaml_safe_load(stdout)
        assert len(env_description["dependencies"])
        for spec_str in env_description["dependencies"]:
            assert spec_str.count("=") == 1

        conda_cli("env", "remove", f"--prefix={prefix}", "--yes")
        assert not is_conda_environment(prefix)


@pytest.mark.integration
def test_env_export_with_variables(
    tmp_env: TmpEnvFixture, conda_cli: CondaCLIFixture, path_factory: PathFactoryFixture
):
    """Test conda env export."""
    with tmp_env("zlib") as prefix:
        assert is_conda_environment(prefix)

        conda_cli(
            *("env", "config", "vars", "set"),
            f"--prefix={prefix}",
            "DUDE=woah",
            "SWEET=yaaa",
        )

        stdout, _, _ = conda_cli("env", "export", f"--prefix={prefix}")

        env_yml = path_factory(suffix=".yml")
        env_yml.write_text(stdout)

        conda_cli("env", "remove", f"--prefix={prefix}", "--yes")
        assert not is_conda_environment(prefix)
        conda_cli("env", "create", f"--prefix={prefix}", f"--file={env_yml}", "--yes")
        assert is_conda_environment(prefix)

        stdout, stderr, _ = conda_cli(
            "env", "export", f"--prefix={prefix}", "--no-builds"
        )
        assert not stderr
        env_description = yaml_safe_load(stdout)
        assert len(env_description["variables"])
        assert env_description["variables"].keys()


@pytest.mark.integration
def test_env_export_json(tmp_env: TmpEnvFixture, conda_cli: CondaCLIFixture):
    """Test conda env export."""
    with tmp_env("zlib") as prefix:
        stdout, _, _ = conda_cli("env", "export", f"--prefix={prefix}", "--json")

        env_description = json.loads(stdout)
        assert len(env_description["dependencies"])
        for spec_str in env_description["dependencies"]:
            assert spec_str.count("=") == 2

        # regression test for #6220
        stdout, stderr, _ = conda_cli(
            "env", "export", f"--prefix={prefix}", "--no-builds", "--json"
        )
        assert not stderr

        env_description = json.loads(stdout)
        assert len(env_description["dependencies"])
        for spec_str in env_description["dependencies"]:
            assert spec_str.count("=") == 1


@pytest.mark.integration
def test_list(
    tmp_env: TmpEnvFixture, conda_cli: CondaCLIFixture, path_factory: PathFactoryFixture
):
    """Test conda list -e and conda create from txt."""
    with tmp_env() as prefix:
        conda_cli("create", f"--prefix={prefix}", "--yes")
        assert is_conda_environment(prefix)

        stdout, _, _ = conda_cli("list", f"--prefix={prefix}", "--export")

        env_txt = path_factory(suffix=".txt")
        env_txt.write_text(stdout)

        conda_cli("env", "remove", f"--prefix={prefix}", "--yes")
        assert not is_conda_environment(prefix)
        conda_cli("create", f"--prefix={prefix}", f"--file={env_txt}", "--yes")
        assert is_conda_environment(prefix)

        stdout2, _, _ = conda_cli("list", f"--prefix={prefix}", "--export")
        assert stdout == stdout2


@pytest.mark.integration
def test_export_multi_channel(
    tmp_env: TmpEnvFixture, conda_cli: CondaCLIFixture, path_factory: PathFactoryFixture
):
    """Test conda env export."""
    from conda.core.prefix_data import PrefixData

    PrefixData._cache_.clear()
    with tmp_env() as prefix:
        conda_cli("create", f"--prefix={prefix}", "python", "--yes")
        assert is_conda_environment(prefix)

        # install something from other channel not in config file
        conda_cli(
            "install",
            f"--prefix={prefix}",
            "--channel=conda-test",
            "test_timestamp_sort",
            "--yes",
        )
        stdout, _, _ = conda_cli("env", "export", f"--prefix={prefix}")
        assert "conda-test" in stdout

        stdout1, _, _ = conda_cli("list", f"--prefix={prefix}", "--explicit")

        env_yml = path_factory(suffix=".yml")
        env_yml.write_text(stdout)

        conda_cli("env", "remove", f"--prefix={prefix}", "--yes")
        assert not is_conda_environment(prefix)
        conda_cli("env", "create", f"--prefix={prefix}", f"--file={env_yml}", "--yes")
        assert is_conda_environment(prefix)

        # check explicit that we have same file
        stdout2, _, _ = conda_cli("list", f"--prefix={prefix}", "--explicit")
        assert stdout1 == stdout2


@pytest.mark.integration
def test_non_existent_file(conda_cli: CondaCLIFixture):
    with pytest.raises(EnvironmentFileNotFound):
        conda_cli("env", "create", "--file", "i_do_not_exist.yml", "--yes")


@pytest.mark.integration
def test_invalid_extensions(
    conda_cli: CondaCLIFixture,
    path_factory: PathFactoryFixture,
):
    env_yml = path_factory(suffix=".ymla")
    env_yml.touch()

    with pytest.raises(EnvironmentFileExtensionNotValid):
        conda_cli("env", "create", f"--file={env_yml}", "--yes")
