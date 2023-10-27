# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import json
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from conda.exceptions import EnvironmentLocationNotFound
from conda.testing import CondaCLIFixture, TmpEnvFixture


@pytest.fixture
def tmp_envs_dirs(mocker: MockerFixture, tmp_path: Path) -> Path:
    mocker.patch(
        "conda.base.context.mockable_context_envs_dirs",
        return_value=(str(tmp_path),),
    )
    return tmp_path


# conda list
def test_list(tmp_env: TmpEnvFixture, conda_cli: CondaCLIFixture):
    pkg = "ca-certificates"  # has no dependencies
    with tmp_env(pkg) as prefix:
        stdout, _, _ = conda_cli("list", "--prefix", prefix, "--json")
        assert any(item["name"] == pkg for item in json.loads(stdout))


# conda list --reverse
def test_list_reverse(tmp_env: TmpEnvFixture, conda_cli: CondaCLIFixture):
    pkg = "curl"  # has dependencies
    with tmp_env(pkg) as prefix:
        stdout, _, _ = conda_cli("list", "--prefix", prefix, "--json")
        names = [item["name"] for item in json.loads(stdout)]
        assert names == sorted(names)

        stdout, _, _ = conda_cli("list", "--prefix", prefix, "--reverse", "--json")
        names = [item["name"] for item in json.loads(stdout)]
        assert names == sorted(names, reverse=True)


# conda list --json
def test_list_json(
    tmp_envs_dirs: Path, conda_cli: CondaCLIFixture, tmp_env: TmpEnvFixture
):
    with tmp_env() as prefix:
        stdout, _, _ = conda_cli("list", "--json", "--prefix", prefix)
        parsed = json.loads(stdout.strip())
        assert isinstance(parsed, list)

        with pytest.raises(EnvironmentLocationNotFound):
            conda_cli("list", "--name", "nonexistent", "--json")


# conda list --revisions --json
def test_list_revisions(
    tmp_envs_dirs: Path, conda_cli: CondaCLIFixture, tmp_env: TmpEnvFixture
):
    with tmp_env() as prefix:
        stdout, _, _ = conda_cli("list", "--revisions", "--json", "--prefix", prefix)
        parsed = json.loads(stdout.strip())
        assert isinstance(parsed, list) or (
            isinstance(parsed, dict) and "error" in parsed
        )

        with pytest.raises(EnvironmentLocationNotFound):
            conda_cli("list", "--name", "nonexistent", "--revisions", "--json")


# conda list PACKAGE
def test_list_package(
    tmp_envs_dirs: Path, conda_cli: CondaCLIFixture, tmp_env: TmpEnvFixture
):
    with tmp_env() as prefix:
        stdout, _, _ = conda_cli("list", "ipython", "--json", "--prefix", prefix)
        parsed = json.loads(stdout.strip())
        assert isinstance(parsed, list)
