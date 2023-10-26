# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import json
import os
import tempfile
from pathlib import Path

import pytest

from conda.base.constants import ROOT_ENV_NAME
from conda.base.context import context
from conda.common.serialize import yaml_safe_load
from conda.core.envs_manager import list_all_known_prefixes
from conda.exceptions import (
    CondaEnvException,
    EnvironmentFileExtensionNotValid,
    EnvironmentFileNotFound,
    EnvironmentLocationNotFound,
    SpecNotFound,
)
from conda.gateways.disk.delete import rm_rf
from conda.testing import CondaCLIFixture, PathFactoryFixture

pytestmark = pytest.mark.usefixtures("parametrized_solver_fixture")

# Environment names we use during our tests
TEST_ENV_NAME_1 = "env-1"
TEST_ENV_NAME_2 = "snowflakes"
TEST_ENV_NAME_42 = "env-42"
TEST_ENV_NAME_PIP = "env-pip"

# Environment config files we use for out tests
ENVIRONMENT_1 = f"""
name: {TEST_ENV_NAME_1}
dependencies:
  - python
channels:
  - defaults
"""

ENVIRONMENT_1_WITH_VARIABLES = f"""
name: {TEST_ENV_NAME_1}
dependencies:
  - python
channels:
  - defaults
variables:
  DUDE: woah
  SWEET: yaaa
  API_KEY: AaBbCcDd===EeFf

"""

ENVIRONMENT_2 = f"""
name: {TEST_ENV_NAME_1}
dependencies:
  - python
  - flask
channels:
  - defaults
"""

ENVIRONMENT_3_INVALID = f"""
name: {TEST_ENV_NAME_1}
dependecies:
  - python
  - flask
channels:
  - defaults
foo: bar
"""

ENVIRONMENT_PYTHON_PIP_CLICK = f"""
name: {TEST_ENV_NAME_1}
dependencies:
  - python=3
  - pip
  - pip:
    - click
channels:
  - defaults
"""

ENVIRONMENT_PYTHON_PIP_CLICK_ATTRS = f"""
name: {TEST_ENV_NAME_1}
dependencies:
  - python=3
  - pip
  - pip:
    - click
    - attrs
channels:
  - defaults
"""

ENVIRONMENT_PYTHON_PIP_NONEXISTING = f"""
name: {TEST_ENV_NAME_1}
dependencies:
  - python=3
  - pip
  - pip:
    - nonexisting_
channels:
  - defaults
"""


def escape_for_winpath(p):
    if p:
        return p.replace("\\", "\\\\")


def create_env(content, filename="environment.yml"):
    path = Path(filename)
    path.write_text(content)


def remove_env_file(filename="environment.yml"):
    Path(filename).unlink()


@pytest.fixture
def env_name_1(conda_cli: CondaCLIFixture) -> None:
    rm_rf("environment.yml")
    conda_cli("env", "remove", "--name", TEST_ENV_NAME_1, "--yes")
    conda_cli("env", "remove", "--name", TEST_ENV_NAME_42, "--yes")
    conda_cli("env", "remove", "--name", TEST_ENV_NAME_PIP, "--yes")
    for env_nb in range(1, 6):
        conda_cli("env", "remove", "--name", f"envjson-{env_nb}", "--yes")

    yield

    rm_rf("environment.yml")
    conda_cli("env", "remove", "--name", TEST_ENV_NAME_1, "--yes")
    conda_cli("env", "remove", "--name", TEST_ENV_NAME_42, "--yes")
    conda_cli("env", "remove", "--name", TEST_ENV_NAME_PIP, "--yes")
    for env_nb in range(1, 6):
        conda_cli("env", "remove", "--name", f"envjson-{env_nb}", "--yes")


@pytest.mark.integration
def test_conda_env_create_no_file(env_name_1: None, conda_cli: CondaCLIFixture):
    """
    Test `conda env create` without an environment.yml file
    Should fail
    """
    with pytest.raises(EnvironmentFileNotFound):
        conda_cli("env", "create")


@pytest.mark.integration
def test_conda_env_create_no_existent_file(
    env_name_1: None, conda_cli: CondaCLIFixture
):
    """
    Test `conda env create --file=not_a_file.txt` with a file that does not
    exist.
    """
    with pytest.raises(EnvironmentFileNotFound):
        conda_cli("env", "create", "--file", "not_a_file.txt")


@pytest.mark.integration
def test_conda_env_create_no_existent_file_with_name(
    env_name_1: None, conda_cli: CondaCLIFixture
):
    """
    Test `conda env create --file=not_a_file.txt` with a file that does not
    exist.
    """
    with pytest.raises(EnvironmentFileNotFound):
        conda_cli("env", "create", "--file", "not_a_file.txt", "--name", "foo")


@pytest.mark.integration
def test_create_valid_remote_env(env_name_1: None, conda_cli: CondaCLIFixture):
    """
    Test retrieving an environment using the BinstarSpec (i.e. it retrieves it from anaconda.org)

    This tests the `remote_origin` command line argument.
    """
    conda_cli("env", "create", "conda-test/env-42")
    assert env_is_created(TEST_ENV_NAME_42)

    stdout, _, _ = conda_cli("info", "--json")

    parsed = json.loads(stdout)
    assert [env for env in parsed["envs"] if env.endswith(TEST_ENV_NAME_42)]


@pytest.mark.integration
def test_create_valid_env(env_name_1: None, conda_cli: CondaCLIFixture):
    """
    Creates an environment.yml file and
    creates and environment with it
    """
    create_env(ENVIRONMENT_1)
    conda_cli("env", "create")
    assert env_is_created(TEST_ENV_NAME_1)

    stdout, _, _ = conda_cli("info", "--json")
    parsed = json.loads(stdout)
    assert [env for env in parsed["envs"] if env.endswith(TEST_ENV_NAME_1)]


@pytest.mark.integration
def test_create_dry_run_yaml(env_name_1: None, conda_cli: CondaCLIFixture):
    create_env(ENVIRONMENT_1)
    stdout, _, _ = conda_cli("env", "create", "--dry-run")
    assert not env_is_created(TEST_ENV_NAME_1)

    # Find line where the YAML output starts (stdout might change if plugins involved)
    lines = stdout.splitlines()
    for lineno, line in enumerate(lines):
        if line.startswith("name:"):
            break
    else:
        pytest.fail("Didn't find YAML data in output")

    output = yaml_safe_load("\n".join(lines[lineno:]))
    assert output["name"] == "env-1"
    assert len(output["dependencies"]) > 0


@pytest.mark.integration
def test_create_dry_run_json(env_name_1: None, conda_cli: CondaCLIFixture):
    create_env(ENVIRONMENT_1)
    stdout, _, _ = conda_cli("env", "create", "--dry-run", "--json")
    assert not env_is_created(TEST_ENV_NAME_1)

    output = json.loads(stdout)
    assert output.get("name") == "env-1"
    assert len(output["dependencies"])


@pytest.mark.integration
def test_create_valid_env_with_variables(env_name_1: None, conda_cli: CondaCLIFixture):
    """
    Creates an environment.yml file and
    creates and environment with it
    """
    create_env(ENVIRONMENT_1_WITH_VARIABLES)
    conda_cli("env", "create")
    assert env_is_created(TEST_ENV_NAME_1)

    stdout, _, _ = conda_cli(
        *("env", "config", "vars", "list"),
        *("--name", TEST_ENV_NAME_1),
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
    assert [env for env in parsed["envs"] if env.endswith(TEST_ENV_NAME_1)]


@pytest.mark.integration
def test_conda_env_create_empty_file(env_name_1: None, conda_cli: CondaCLIFixture):
    """Test `conda env create --file=file_name.yml` where file_name.yml is empty."""
    tmp_file = tempfile.NamedTemporaryFile(suffix=".yml", delete=False)

    with pytest.raises(SpecNotFound):
        conda_cli("env", "create", "--file", tmp_file.name)

    tmp_file.close()
    os.unlink(tmp_file.name)


@pytest.mark.integration
def test_conda_env_create_http(env_name_1: None, conda_cli: CondaCLIFixture):
    """Test `conda env create --file=https://some-website.com/environment.yml`."""
    conda_cli(
        *("env", "create"),
        *(
            "--file",
            "https://raw.githubusercontent.com/conda/conda/main/tests/conda_env/support/simple.yml",
        ),
    )
    try:
        assert env_is_created("nlp")
    finally:
        conda_cli("env", "remove", "--name", "nlp", "--yes")


@pytest.mark.integration
def test_update(env_name_1: None, conda_cli: CondaCLIFixture):
    create_env(ENVIRONMENT_1)
    conda_cli("env", "create")
    create_env(ENVIRONMENT_2)

    conda_cli("env", "update", "--name", TEST_ENV_NAME_1)

    stdout, _, _ = conda_cli("list", "--name", TEST_ENV_NAME_1, "flask", "--json")
    parsed = json.loads(stdout)
    assert parsed


@pytest.mark.integration
def test_name(env_name_1: None, conda_cli: CondaCLIFixture):
    """
    # smoke test for gh-254
    Test that --name can overide the `name` key inside an environment.yml
    """
    create_env(ENVIRONMENT_1)
    env_name = "smoke-gh-254"

    # It might be the case that you need to run this test more than once!
    try:
        conda_cli("env", "remove", "--name", env_name, "--yes")
    except:
        pass

    conda_cli("env", "create", "--file", "environment.yml", "--name", env_name, "--yes")

    stdout, _, _ = conda_cli("info", "--json")

    parsed = json.loads(stdout)
    assert [env for env in parsed["envs"] if env.endswith(env_name)]


@pytest.mark.integration
def test_create_valid_env_json_output(env_name_1: None, conda_cli: CondaCLIFixture):
    """
    Creates an environment from an environment.yml file with conda packages (no pip)
    Check the json output
    """
    create_env(ENVIRONMENT_1)
    stdout, _, _ = conda_cli(
        "env", "create", "--name", "envjson-1", "--quiet", "--json", "--yes"
    )
    output = json.loads(stdout)
    assert output["success"] is True
    assert len(output["actions"]["LINK"]) > 0
    assert "PIP" not in output["actions"]


@pytest.mark.integration
def test_create_valid_env_with_conda_and_pip_json_output(
    env_name_1: None, conda_cli: CondaCLIFixture
):
    """
    Creates an environment from an environment.yml file with conda and pip dependencies
    Check the json output
    """
    create_env(ENVIRONMENT_PYTHON_PIP_CLICK)
    stdout, _, _ = conda_cli(
        "env", "create", "--name", "envjson-2", "--quiet", "--json", "--yes"
    )
    output = json.loads(stdout)
    assert len(output["actions"]["LINK"]) > 0
    assert output["actions"]["PIP"][0].startswith("click")


@pytest.mark.integration
def test_update_env_json_output(env_name_1: None, conda_cli: CondaCLIFixture):
    """
    Update an environment by adding a conda package
    Check the json output
    """
    create_env(ENVIRONMENT_1)
    conda_cli("env", "create", "--name", "envjson-3", "--json", "--yes")
    create_env(ENVIRONMENT_2)
    stdout, _, _ = conda_cli(
        "env", "update", "--name", "envjson-3", "--quiet", "--json"
    )
    output = json.loads(stdout)
    assert output["success"] is True
    assert len(output["actions"]["LINK"]) > 0
    assert "PIP" not in output["actions"]


@pytest.mark.integration
def test_update_env_only_pip_json_output(
    env_name_1: None, conda_cli: CondaCLIFixture, request
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
    create_env(ENVIRONMENT_PYTHON_PIP_CLICK)
    conda_cli("env", "create", "--name", "envjson-4", "--json", "--yes")
    create_env(ENVIRONMENT_PYTHON_PIP_CLICK_ATTRS)
    stdout, _, _ = conda_cli(
        "env", "update", "--name", "envjson-4", "--quiet", "--json"
    )
    output = json.loads(stdout)
    assert output["success"] is True
    # No conda actions (FETCH/LINK), only pip
    assert list(output["actions"].keys()) == ["PIP"]
    # Only attrs installed
    assert len(output["actions"]["PIP"]) == 1
    assert output["actions"]["PIP"][0].startswith("attrs")


@pytest.mark.integration
def test_update_env_no_action_json_output(
    env_name_1: None, conda_cli: CondaCLIFixture, request
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
    create_env(ENVIRONMENT_PYTHON_PIP_CLICK)
    conda_cli("env", "create", "--name", "envjson-5", "--json", "--yes")
    stdout, _, _ = conda_cli(
        "env", "update", "--name", "envjson-5", "--quiet", "--json"
    )
    output = json.loads(stdout)
    assert output["message"] == "All requested packages already installed."


@pytest.mark.integration
def test_remove_dry_run(env_name_1: None, conda_cli: CondaCLIFixture):
    # Test for GH-10231
    create_env(ENVIRONMENT_1)
    conda_cli("env", "create")
    conda_cli("env", "remove", "--name", "env-1", "--dry-run")
    assert env_is_created("env-1")


@pytest.mark.integration
def test_set_unset_env_vars(env_name_1: None, conda_cli: CondaCLIFixture):
    create_env(ENVIRONMENT_1)
    conda_cli("env", "create")
    env_name = "env-1"
    conda_cli(
        *("env", "config", "vars", "set"),
        *("--name", env_name),
        "DUDE=woah",
        "SWEET=yaaa",
        "API_KEY=AaBbCcDd===EeFf",
    )
    stdout, _, _ = conda_cli(
        *("env", "config", "vars", "list"),
        *("--name", env_name),
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
        *("--name", env_name),
        "DUDE",
        "SWEET",
        "API_KEY",
    )
    stdout, _, _ = conda_cli(
        *("env", "config", "vars", "list"),
        *("--name", env_name),
        "--json",
    )
    output_env_vars = json.loads(stdout)
    assert output_env_vars == {}


@pytest.mark.integration
def test_set_unset_env_vars_env_no_exist(env_name_1: None, conda_cli: CondaCLIFixture):
    create_env(ENVIRONMENT_1)
    conda_cli("env", "create")
    env_name = "env-11"
    with pytest.raises(EnvironmentLocationNotFound):
        conda_cli(
            *("env", "config", "vars", "set"),
            *("--name", env_name),
            "DUDE=woah",
            "SWEET=yaaa",
            "API_KEY=AaBbCcDd===EeFf",
        )


@pytest.mark.integration
def test_pip_error_is_propagated(env_name_1: None, conda_cli: CondaCLIFixture):
    """
    Creates an environment from an environment.yml file with conda and incorrect pip dependencies
    The output must clearly show pip error.
    Check the json output
    """
    create_env(ENVIRONMENT_PYTHON_PIP_NONEXISTING)
    with pytest.raises(CondaEnvException, match="Pip failed"):
        conda_cli("env", "create", "--name", TEST_ENV_NAME_PIP)


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


@pytest.fixture
def env_name_2(conda_cli: CondaCLIFixture) -> None:
    # It *can* happen that this does not remove the env directory and then
    # the CREATE fails. Keep your eyes out! We could use rm_rf, but do we
    # know which conda install we're talking about? Now? Forever? I'd feel
    # safer adding an `rm -rf` if we had a `Commands.ENV_NAME_TO_PREFIX` to
    # tell us which folder to remove.
    conda_cli("env", "remove", "--name", TEST_ENV_NAME_2, "--yes")

    yield

    conda_cli("env", "remove", "--name", TEST_ENV_NAME_2, "--yes")


@pytest.mark.integration
def test_env_export(
    env_name_2: None, conda_cli: CondaCLIFixture, path_factory: PathFactoryFixture
):
    """Test conda env export."""
    conda_cli("create", "--name", TEST_ENV_NAME_2, "flask", "--yes")
    assert env_is_created(TEST_ENV_NAME_2)

    stdout, _, _ = conda_cli("env", "export", "--name", TEST_ENV_NAME_2)

    env_yml = path_factory(suffix=".yml")
    env_yml.write_text(stdout)

    conda_cli("env", "remove", "--name", TEST_ENV_NAME_2, "--yes")
    assert not env_is_created(TEST_ENV_NAME_2)
    conda_cli("env", "create", "--file", env_yml, "--yes")
    assert env_is_created(TEST_ENV_NAME_2)

    # regression test for #6220
    stdout, stderr, _ = conda_cli(
        "env", "export", "--name", TEST_ENV_NAME_2, "--no-builds"
    )
    assert not stderr
    env_description = yaml_safe_load(stdout)
    assert len(env_description["dependencies"])
    for spec_str in env_description["dependencies"]:
        assert spec_str.count("=") == 1

    conda_cli("env", "remove", "--name", TEST_ENV_NAME_2, "--yes")
    assert not env_is_created(TEST_ENV_NAME_2)


@pytest.mark.integration
def test_env_export_with_variables(
    env_name_2: None, conda_cli: CondaCLIFixture, path_factory: PathFactoryFixture
):
    """Test conda env export."""
    conda_cli("create", "--name", TEST_ENV_NAME_2, "flask", "--yes")
    assert env_is_created(TEST_ENV_NAME_2)

    conda_cli(
        *("env", "config", "vars", "set"),
        *("--name", TEST_ENV_NAME_2),
        "DUDE=woah",
        "SWEET=yaaa",
    )

    stdout, _, _ = conda_cli("env", "export", "--name", TEST_ENV_NAME_2)

    env_yml = path_factory(suffix=".yml")
    env_yml.write_text(stdout)

    conda_cli("env", "remove", "--name", TEST_ENV_NAME_2, "--yes")
    assert not env_is_created(TEST_ENV_NAME_2)
    conda_cli("env", "create", "--file", env_yml, "--yes")
    assert env_is_created(TEST_ENV_NAME_2)

    stdout, stderr, _ = conda_cli(
        "env", "export", "--name", TEST_ENV_NAME_2, "--no-builds"
    )
    assert not stderr
    env_description = yaml_safe_load(stdout)
    assert len(env_description["variables"])
    assert env_description["variables"].keys()

    conda_cli("env", "remove", "--name", TEST_ENV_NAME_2, "--yes")
    assert not env_is_created(TEST_ENV_NAME_2)


@pytest.mark.integration
def test_env_export_json(env_name_2: None, conda_cli: CondaCLIFixture):
    """Test conda env export."""
    conda_cli("create", "--name", TEST_ENV_NAME_2, "flask", "--yes")
    assert env_is_created(TEST_ENV_NAME_2)

    stdout, _, _ = conda_cli("env", "export", "--name", TEST_ENV_NAME_2, "--json")

    conda_cli("env", "remove", "--name", TEST_ENV_NAME_2, "--yes")
    assert not env_is_created(TEST_ENV_NAME_2)

    # regression test for #6220
    stdout, stderr, _ = conda_cli(
        "env", "export", "--name", TEST_ENV_NAME_2, "--no-builds", "--json"
    )
    assert not stderr

    env_description = json.loads(stdout)
    assert len(env_description["dependencies"])
    for spec_str in env_description["dependencies"]:
        assert spec_str.count("=") == 1

    conda_cli("env", "remove", "--name", TEST_ENV_NAME_2, "--yes")
    assert not env_is_created(TEST_ENV_NAME_2)


@pytest.mark.integration
def test_list(
    env_name_2: None, conda_cli: CondaCLIFixture, path_factory: PathFactoryFixture
):
    """Test conda list -e and conda create from txt."""
    conda_cli("create", "--name", TEST_ENV_NAME_2, "--yes")
    assert env_is_created(TEST_ENV_NAME_2)

    stdout, _, _ = conda_cli("list", "--name", TEST_ENV_NAME_2, "--export")

    env_txt = path_factory(suffix=".txt")
    env_txt.write_text(stdout)

    conda_cli("env", "remove", "--name", TEST_ENV_NAME_2, "--yes")
    assert not env_is_created(TEST_ENV_NAME_2)
    conda_cli("create", "--name", TEST_ENV_NAME_2, "--file", env_txt, "--yes")
    assert env_is_created(TEST_ENV_NAME_2)

    stdout2, _, _ = conda_cli("list", "--name", TEST_ENV_NAME_2, "--export")
    assert stdout == stdout2


@pytest.mark.integration
def test_export_multi_channel(
    env_name_2: None, conda_cli: CondaCLIFixture, path_factory: PathFactoryFixture
):
    """Test conda env export."""
    from conda.core.prefix_data import PrefixData

    PrefixData._cache_.clear()
    conda_cli("create", "--name", TEST_ENV_NAME_2, "python", "--yes")
    assert env_is_created(TEST_ENV_NAME_2)

    # install something from other channel not in config file
    conda_cli(
        "install",
        *("--name", TEST_ENV_NAME_2),
        *("--channel", "conda-test"),
        "test_timestamp_sort",
        "--yes",
    )
    stdout, _, _ = conda_cli("env", "export", "--name", TEST_ENV_NAME_2)
    assert "conda-test" in stdout

    stdout1, _, _ = conda_cli("list", "--name", TEST_ENV_NAME_2, "--explicit")

    env_yml = path_factory(suffix=".yml")
    env_yml.write_text(stdout)

    conda_cli("env", "remove", "--name", TEST_ENV_NAME_2, "--yes")
    assert not env_is_created(TEST_ENV_NAME_2)
    conda_cli("env", "create", "--file", env_yml, "--yes")
    assert env_is_created(TEST_ENV_NAME_2)

    # check explicit that we have same file
    stdout2, _, _ = conda_cli("list", "--name", TEST_ENV_NAME_2, "--explicit")
    assert stdout1 == stdout2


@pytest.mark.integration
def test_non_existent_file(env_name_2: None, conda_cli: CondaCLIFixture):
    with pytest.raises(EnvironmentFileNotFound):
        conda_cli("env", "create", "--file", "i_do_not_exist.yml", "--yes")


@pytest.mark.integration
def test_invalid_extensions(
    env_name_2: None,
    conda_cli: CondaCLIFixture,
    path_factory: PathFactoryFixture,
):
    env_yml = path_factory(suffix=".ymla")
    env_yml.touch()

    with pytest.raises(EnvironmentFileExtensionNotValid):
        conda_cli("env", "create", "--file", env_yml, "--yes")
