# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import json
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from conda.core.prefix_data import PrefixData
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
def test_list_json(tmp_envs_dirs: Path, conda_cli: CondaCLIFixture):
    stdout, _, _ = conda_cli("list", "--json")
    parsed = json.loads(stdout.strip())
    assert isinstance(parsed, list)

    with pytest.raises(EnvironmentLocationNotFound):
        conda_cli("list", "--name", "nonexistent", "--json")


def test_list_specific_version(
    test_recipes_channel: Path, tmp_env: TmpEnvFixture, conda_cli: CondaCLIFixture
):
    def pkg_info(s):
        # function from nb_conda/envmanager.py
        if isinstance(s, str):
            name, version, build = s.rsplit("-", 2)
            return {"name": name, "version": version, "build": build}
        else:
            return {
                "name": s["name"],
                "version": s["version"],
                "build": s.get("build_string") or s["build"],
            }

    with tmp_env("dependent=1.0") as prefix:
        stdout, _, _ = conda_cli("list", f"--prefix={prefix}", "--json")
        stdout_json = json.loads(stdout)
        packages = [pkg_info(package) for package in stdout_json]
        installed_package = next(p for p in packages if p["name"] == "dependent")
        assert installed_package["version"].startswith("1")


# conda list --revisions --json
def test_list_revisions(tmp_envs_dirs: Path, conda_cli: CondaCLIFixture):
    stdout, _, _ = conda_cli("list", "--revisions", "--json")
    parsed = json.loads(stdout.strip())
    assert isinstance(parsed, list) or (isinstance(parsed, dict) and "error" in parsed)

    with pytest.raises(EnvironmentLocationNotFound):
        conda_cli("list", "--name", "nonexistent", "--revisions", "--json")


# conda list PACKAGE
def test_list_package(tmp_envs_dirs: Path, conda_cli: CondaCLIFixture):
    stdout, _, _ = conda_cli("list", "ipython", "--json")
    parsed = json.loads(stdout.strip())
    assert isinstance(parsed, list)


def test_list_explicit(tmp_env: TmpEnvFixture, conda_cli: CondaCLIFixture):
    pkg = "curl"  # has dependencies
    with tmp_env(pkg) as prefix:
        stdout, _, _ = conda_cli("list", "--prefix", prefix, "--json")
        curl = next(
            (item for item in json.loads(stdout) if item["name"] == "curl"), None
        )
        assert curl

        # Plant a fake token to make sure we can remove it if needed
        json_file = prefix / "conda-meta" / (curl["dist_name"] + ".json")
        json_data = json.loads(json_file.read_text())
        json_data["url"] = (
            "https://conda.anaconda.org/t/some-fake-token/"
            f"{json_data['channel']}/{json_data['subdir']}/{json_data['fn']}"
        )
        json_file.write_text(json.dumps(json_data))

        PrefixData(prefix)._cache_.clear()
        stdout, _, _ = conda_cli("list", "--prefix", prefix, "--explicit")
        assert curl["dist_name"] in stdout
        assert "/t/some-fake-token/" not in stdout  # by default we should not see this

        stdout, _, _ = conda_cli("list", "--prefix", prefix, "--explicit", "--auth")
        assert curl["dist_name"] in stdout
        assert "/t/some-fake-token/" in stdout  # with --auth we do
