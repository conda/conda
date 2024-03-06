# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest

from conda.base.constants import ROOT_ENV_NAME
from conda.base.context import context
from conda.common.serialize import yaml_safe_dump, yaml_safe_load
from conda.core.envs_manager import list_all_known_prefixes
from conda.exceptions import (
    CondaEnvException,
    EnvironmentFileExtensionNotValid,
    EnvironmentFileNotFound,
    EnvironmentLocationNotFound,
    SpecNotFound,
)

if TYPE_CHECKING:
    from typing import Iterator

    from pytest import MonkeyPatch

    from conda.testing import CondaCLIFixture, PathFactoryFixture

pytestmark = pytest.mark.usefixtures("parametrized_solver_fixture")

# Environment names we use during our tests
TEST_ENV1 = "env1"

# Environment config files we use for out tests
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


@pytest.fixture
def env1(conda_cli: CondaCLIFixture) -> Iterator[str]:
    conda_cli("remove", f"--name={TEST_ENV1}", "--all", "--yes")
    yield TEST_ENV1
    conda_cli("remove", f"--name={TEST_ENV1}", "--all", "--yes")


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
def test_create_valid_remote_env(conda_cli: CondaCLIFixture):
    """
    Test retrieving an environment using the BinstarSpec (i.e. it retrieves it from anaconda.org)

    This tests the `remote_origin` command line argument.
    """
    try:
        conda_cli("env", "create", "conda-test/env-remote")
        assert env_is_created("env-remote")

        stdout, _, _ = conda_cli("info", "--json")

        parsed = json.loads(stdout)
        assert [env for env in parsed["envs"] if env.endswith("env-remote")]
    finally:
        # manual cleanup
        conda_cli("remove", "--name=env-remote", "--all", "--yes")


@pytest.mark.integration
def test_create_valid_env(env1: str, conda_cli: CondaCLIFixture):
    """
    Creates an environment.yml file and
    creates and environment with it
    """
    create_env(ENVIRONMENT_CA_CERTIFICATES)
    conda_cli("env", "create")
    assert env_is_created(env1)

    stdout, _, _ = conda_cli("info", "--json")
    parsed = json.loads(stdout)
    assert [env for env in parsed["envs"] if env.endswith(env1)]


@pytest.mark.integration
def test_create_dry_run_yaml(env1: str, conda_cli: CondaCLIFixture):
    create_env(ENVIRONMENT_CA_CERTIFICATES)
    stdout, _, _ = conda_cli("env", "create", "--dry-run")
    assert not env_is_created(env1)

    # Find line where the YAML output starts (stdout might change if plugins involved)
    lines = stdout.splitlines()
    for lineno, line in enumerate(lines):
        if line.startswith("name:"):
            break
    else:
        pytest.fail("Didn't find YAML data in output")

    output = yaml_safe_load("\n".join(lines[lineno:]))
    assert output["name"] == env1
    assert len(output["dependencies"]) > 0


@pytest.mark.integration
def test_create_dry_run_json(env1: str, conda_cli: CondaCLIFixture):
    create_env(ENVIRONMENT_CA_CERTIFICATES)
    stdout, _, _ = conda_cli("env", "create", "--dry-run", "--json")
    assert not env_is_created(env1)

    output = json.loads(stdout)
    assert output.get("name") == env1
    assert len(output["dependencies"])


@pytest.mark.integration
def test_create_valid_env_with_variables(env1: str, conda_cli: CondaCLIFixture):
    """
    Creates an environment.yml file and
    creates and environment with it
    """
    create_env(ENVIRONMENT_CA_CERTIFICATES_WITH_VARIABLES)
    conda_cli("env", "create")
    assert env_is_created(env1)

    stdout, _, _ = conda_cli(
        *("env", "config", "vars", "list"),
        f"--name={env1}",
        "--json",
    )
    output_env_vars = json.loads(stdout)
    assert output_env_vars == {
        "DUDE": "woah",
        "SWEET": "yaaa",
        "API_KEY": "AaBbCcDd===EeFf",
    }

    stdout, _, _ = conda_cli("info", "--json")
    parsed = json.loads(stdout)
    assert [env for env in parsed["envs"] if env.endswith(env1)]


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
def test_conda_env_create_http(conda_cli: CondaCLIFixture):
    """Test `conda env create --file=https://some-website.com/environment.yml`."""
    try:
        conda_cli(
            *("env", "create"),
            "--file=https://raw.githubusercontent.com/conda/conda/main/tests/env/support/simple.yml",
        )
        assert env_is_created("nlp")
    finally:
        # manual cleanup
        conda_cli("remove", "--name=nlp", "--all", "--yes")


@pytest.mark.integration
def test_update(env1: str, conda_cli: CondaCLIFixture):
    create_env(ENVIRONMENT_CA_CERTIFICATES)
    conda_cli("env", "create")

    create_env(ENVIRONMENT_CA_CERTIFICATES_ZLIB)
    conda_cli("env", "update", f"--name={env1}")

    stdout, _, _ = conda_cli("list", f"--name={env1}", "zlib", "--json")
    parsed = json.loads(stdout)
    assert parsed
    assert json.loads(stdout)


@pytest.mark.integration
def test_name(env1: str, conda_cli: CondaCLIFixture):
    """
    # smoke test for gh-254
    Test that --name can override the `name` key inside an environment.yml
    """
    create_env(ENVIRONMENT_CA_CERTIFICATES)
    conda_cli("env", "create", "--file=environment.yml", f"--name={env1}", "--yes")

    stdout, _, _ = conda_cli("info", "--json")

    parsed = json.loads(stdout)
    assert [env for env in parsed["envs"] if env.endswith(env1)]


@pytest.mark.integration
def test_create_valid_env_json_output(env1: str, conda_cli: CondaCLIFixture):
    """
    Creates an environment from an environment.yml file with conda packages (no pip)
    Check the json output
    """
    create_env(ENVIRONMENT_CA_CERTIFICATES)
    stdout, _, _ = conda_cli(
        "env", "create", f"--name={env1}", "--quiet", "--json", "--yes"
    )
    output = json.loads(stdout)
    assert output["success"] is True
    assert len(output["actions"]["LINK"]) > 0
    assert "PIP" not in output["actions"]


@pytest.mark.integration
def test_create_valid_env_with_conda_and_pip_json_output(
    env1: str, conda_cli: CondaCLIFixture
):
    """
    Creates an environment from an environment.yml file with conda and pip dependencies
    Check the json output
    """
    create_env(ENVIRONMENT_PIP_CLICK)
    stdout, _, _ = conda_cli(
        "env", "create", f"--name={env1}", "--quiet", "--json", "--yes"
    )
    output = json.loads(stdout)
    assert len(output["actions"]["LINK"]) > 0
    assert output["actions"]["PIP"][0].startswith("click")


@pytest.mark.integration
def test_update_env_json_output(env1: str, conda_cli: CondaCLIFixture):
    """
    Update an environment by adding a conda package
    Check the json output
    """
    create_env(ENVIRONMENT_CA_CERTIFICATES)
    conda_cli("env", "create", f"--name={env1}", "--json", "--yes")
    create_env(ENVIRONMENT_CA_CERTIFICATES_ZLIB)
    stdout, _, _ = conda_cli("env", "update", f"--name={env1}", "--quiet", "--json")
    output = json.loads(stdout)
    assert output["success"] is True
    assert len(output["actions"]["LINK"]) > 0
    assert "PIP" not in output["actions"]


@pytest.mark.integration
def test_update_env_only_pip_json_output(
    env1: str, conda_cli: CondaCLIFixture, request
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
    create_env(ENVIRONMENT_PIP_CLICK)
    conda_cli("env", "create", f"--name={env1}", "--json", "--yes")
    create_env(ENVIRONMENT_PIP_CLICK_ATTRS)
    stdout, _, _ = conda_cli("env", "update", f"--name={env1}", "--quiet", "--json")
    output = json.loads(stdout)
    assert output["success"] is True
    # No conda actions (FETCH/LINK), only pip
    assert list(output["actions"].keys()) == ["PIP"]
    # Only attrs installed
    assert len(output["actions"]["PIP"]) == 1
    assert output["actions"]["PIP"][0].startswith("attrs")


@pytest.mark.integration
def test_update_env_no_action_json_output(
    env1: str, conda_cli: CondaCLIFixture, request
):
    """
    Update an already up-to-date environment
    Check the json output
    """
    request.applymarker(
        pytest.mark.xfail(
            context.solver == "libmamba",
            reason="Known issue: https://github.com/conda/conda-libmamba-solver/issues/320",
        )
    )
    create_env(ENVIRONMENT_PIP_CLICK)
    conda_cli("env", "create", f"--name={env1}", "--json", "--yes")
    stdout, _, _ = conda_cli("env", "update", f"--name={env1}", "--quiet", "--json")
    output = json.loads(stdout)
    assert output["message"] == "All requested packages already installed."


@pytest.mark.integration
def test_remove_dry_run(env1: str, conda_cli: CondaCLIFixture):
    # Test for GH-10231
    create_env(ENVIRONMENT_CA_CERTIFICATES)
    conda_cli("env", "create")
    conda_cli("env", "remove", f"--name={env1}", "--dry-run")
    assert env_is_created(env1)


@pytest.mark.integration
def test_set_unset_env_vars(env1: str, conda_cli: CondaCLIFixture):
    create_env(ENVIRONMENT_CA_CERTIFICATES)
    conda_cli("env", "create")
    conda_cli(
        *("env", "config", "vars", "set"),
        f"--name={env1}",
        "DUDE=woah",
        "SWEET=yaaa",
        "API_KEY=AaBbCcDd===EeFf",
    )
    stdout, _, _ = conda_cli(
        *("env", "config", "vars", "list"),
        f"--name={env1}",
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
        f"--name={env1}",
        "DUDE",
        "SWEET",
        "API_KEY",
    )
    stdout, _, _ = conda_cli(
        *("env", "config", "vars", "list"),
        f"--name={env1}",
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
def test_pip_error_is_propagated(env1: str, conda_cli: CondaCLIFixture):
    """
    Creates an environment from an environment.yml file with conda and incorrect pip dependencies
    The output must clearly show pip error.
    Check the json output
    """
    create_env(ENVIRONMENT_PIP_NONEXISTING)
    with pytest.raises(CondaEnvException, match="Pip failed"):
        conda_cli("env", "create")


def env_is_created(env_name):
    """
        Assert an environment is created
    Args:
        env_name: the environment name
    Returns: True if created
             False otherwise
    """
    from os.path import basename

    for prefix in list_all_known_prefixes():
        name = ROOT_ENV_NAME if prefix == context.root_prefix else basename(prefix)
        if name == env_name:
            return True

    return False


@pytest.mark.integration
def test_env_export(
    env1: str, conda_cli: CondaCLIFixture, path_factory: PathFactoryFixture
):
    """Test conda env export."""
    conda_cli("create", f"--name={env1}", "zlib", "--yes")
    assert env_is_created(env1)

    stdout, _, _ = conda_cli("env", "export", f"--name={env1}")

    env_yml = path_factory(suffix=".yml")
    env_yml.write_text(stdout)

    conda_cli("env", "remove", f"--name={env1}", "--yes")
    assert not env_is_created(env1)
    conda_cli("env", "create", f"--file={env_yml}", "--yes")
    assert env_is_created(env1)

    # regression test for #6220
    stdout, stderr, _ = conda_cli("env", "export", f"--name={env1}", "--no-builds")
    assert not stderr
    env_description = yaml_safe_load(stdout)
    assert len(env_description["dependencies"])
    for spec_str in env_description["dependencies"]:
        assert spec_str.count("=") == 1

    conda_cli("env", "remove", f"--name={env1}", "--yes")
    assert not env_is_created(env1)


@pytest.mark.integration
def test_env_export_with_variables(
    env1: str, conda_cli: CondaCLIFixture, path_factory: PathFactoryFixture
):
    """Test conda env export."""
    conda_cli("create", f"--name={env1}", "zlib", "--yes")
    assert env_is_created(env1)

    conda_cli(
        *("env", "config", "vars", "set"),
        f"--name={env1}",
        "DUDE=woah",
        "SWEET=yaaa",
    )

    stdout, _, _ = conda_cli("env", "export", f"--name={env1}")

    env_yml = path_factory(suffix=".yml")
    env_yml.write_text(stdout)

    conda_cli("env", "remove", f"--name={env1}", "--yes")
    assert not env_is_created(env1)
    conda_cli("env", "create", f"--file={env_yml}", "--yes")
    assert env_is_created(env1)

    stdout, stderr, _ = conda_cli("env", "export", f"--name={env1}", "--no-builds")
    assert not stderr
    env_description = yaml_safe_load(stdout)
    assert len(env_description["variables"])
    assert env_description["variables"].keys()

    conda_cli("env", "remove", f"--name={env1}", "--yes")
    assert not env_is_created(env1)


@pytest.mark.integration
def test_env_export_json(env1: str, conda_cli: CondaCLIFixture):
    """Test conda env export."""
    conda_cli("create", f"--name={env1}", "zlib", "--yes")
    assert env_is_created(env1)

    stdout, _, _ = conda_cli("env", "export", f"--name={env1}", "--json")

    conda_cli("env", "remove", f"--name={env1}", "--yes")
    assert not env_is_created(env1)

    # regression test for #6220
    stdout, stderr, _ = conda_cli(
        "env", "export", f"--name={env1}", "--no-builds", "--json"
    )
    assert not stderr

    env_description = json.loads(stdout)
    assert len(env_description["dependencies"])
    for spec_str in env_description["dependencies"]:
        assert spec_str.count("=") == 1

    conda_cli("env", "remove", f"--name={env1}", "--yes")
    assert not env_is_created(env1)


@pytest.mark.integration
def test_list(env1: str, conda_cli: CondaCLIFixture, path_factory: PathFactoryFixture):
    """Test conda list -e and conda create from txt."""
    conda_cli("create", f"--name={env1}", "--yes")
    assert env_is_created(env1)

    stdout, _, _ = conda_cli("list", f"--name={env1}", "--export")

    env_txt = path_factory(suffix=".txt")
    env_txt.write_text(stdout)

    conda_cli("env", "remove", f"--name={env1}", "--yes")
    assert not env_is_created(env1)
    conda_cli("create", f"--name={env1}", f"--file={env_txt}", "--yes")
    assert env_is_created(env1)

    stdout2, _, _ = conda_cli("list", f"--name={env1}", "--export")
    assert stdout == stdout2


@pytest.mark.integration
def test_export_multi_channel(
    env1: str, conda_cli: CondaCLIFixture, path_factory: PathFactoryFixture
):
    """Test conda env export."""
    from conda.core.prefix_data import PrefixData

    PrefixData._cache_.clear()
    conda_cli("create", f"--name={env1}", "python", "--yes")
    assert env_is_created(env1)

    # install something from other channel not in config file
    conda_cli(
        "install",
        f"--name={env1}",
        "--channel=conda-test",
        "test_timestamp_sort",
        "--yes",
    )
    stdout, _, _ = conda_cli("env", "export", f"--name={env1}")
    assert "conda-test" in stdout

    stdout1, _, _ = conda_cli("list", f"--name={env1}", "--explicit")

    env_yml = path_factory(suffix=".yml")
    env_yml.write_text(stdout)

    conda_cli("env", "remove", f"--name={env1}", "--yes")
    assert not env_is_created(env1)
    conda_cli("env", "create", f"--file={env_yml}", "--yes")
    assert env_is_created(env1)

    # check explicit that we have same file
    stdout2, _, _ = conda_cli("list", f"--name={env1}", "--explicit")
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
