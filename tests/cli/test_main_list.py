# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from conda.core.prefix_data import PrefixData
from conda.exceptions import EnvironmentLocationNotFound
from conda.testing.integration import package_is_installed

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_mock import MockerFixture

    from conda.testing.fixtures import (
        CondaCLIFixture,
        PathFactoryFixture,
        TmpEnvFixture,
    )


@pytest.fixture
def tmp_envs_dirs(mocker: MockerFixture, tmp_path: Path) -> Path:
    mocker.patch(
        "conda.base.context.mockable_context_envs_dirs",
        return_value=(str(tmp_path),),
    )
    return tmp_path


# conda list
def test_list(
    tmp_env: TmpEnvFixture,
    conda_cli: CondaCLIFixture,
    test_recipes_channel: Path,
) -> None:
    pkg = "dependency"  # has no dependencies
    with tmp_env(pkg) as prefix:
        stdout, _, _ = conda_cli("list", "--prefix", prefix, "--json")
        assert any(item["name"] == pkg for item in json.loads(stdout))


# conda list --reverse
def test_list_reverse(
    tmp_env: TmpEnvFixture,
    conda_cli: CondaCLIFixture,
    test_recipes_channel: Path,
) -> None:
    pkg = "dependent"  # has dependencies
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
    test_recipes_channel: Path,
    tmp_env: TmpEnvFixture,
    conda_cli: CondaCLIFixture,
) -> None:
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
def test_list_revisions(tmp_envs_dirs: Path, conda_cli: CondaCLIFixture) -> None:
    stdout, _, _ = conda_cli("list", "--revisions", "--json")
    parsed = json.loads(stdout.strip())
    assert isinstance(parsed, list) or (isinstance(parsed, dict) and "error" in parsed)

    with pytest.raises(EnvironmentLocationNotFound):
        conda_cli("list", "--name", "nonexistent", "--revisions", "--json")


# conda list PACKAGE
def test_list_package(tmp_envs_dirs: Path, conda_cli: CondaCLIFixture) -> None:
    stdout, _, _ = conda_cli("list", "ipython", "--json")
    parsed = json.loads(stdout.strip())
    assert isinstance(parsed, list)


def test_list_explicit(
    tmp_env: TmpEnvFixture,
    conda_cli: CondaCLIFixture,
    test_recipes_channel: Path,
) -> None:
    pkg = "dependency"  # has no dependencies
    with tmp_env(pkg) as prefix:
        stdout, _, _ = conda_cli("list", "--prefix", prefix, "--json")
        dist_names = [item["dist_name"] for item in json.loads(stdout)]
        assert len(dist_names) == 1
        dist_name = dist_names[0]

        # Plant a fake token to make sure we can remove it if needed
        token = "t/some-fake-token/"
        json_file = prefix / "conda-meta" / (dist_name + ".json")
        json_data = json.loads(json_file.read_text())
        json_data["url"] = (
            f"https://conda.anaconda.org/{token}"
            f"{json_data['channel']}/{json_data['subdir']}/{json_data['fn']}"
        )
        json_file.write_text(json.dumps(json_data))

        PrefixData(prefix)._cache_.clear()
        stdout, _, _ = conda_cli("list", "--prefix", prefix, "--explicit")
        assert dist_name in stdout
        assert token not in stdout  # by default we should not see this

        stdout, _, _ = conda_cli("list", "--prefix", prefix, "--explicit", "--auth")
        assert dist_name in stdout
        assert token in stdout  # with --auth we do


@pytest.mark.integration
def test_export(
    tmp_env: TmpEnvFixture,
    conda_cli: CondaCLIFixture,
    path_factory: PathFactoryFixture,
    test_recipes_channel: Path,
) -> None:
    """Test that `conda list --export` output can be used to create a similar environment."""
    pkg = "dependency=1.0"  # has no dependencies
    with tmp_env(pkg) as prefix:
        assert package_is_installed(prefix, pkg)

        output, _, _ = conda_cli("list", f"--prefix={prefix}", "--export")

        env_txt = path_factory(suffix=".txt")
        env_txt.write_text(output)

        with tmp_env("--file", env_txt) as prefix2:
            assert package_is_installed(prefix, pkg)

            output2, _, _ = conda_cli("list", f"--prefix={prefix2}", "--export")
            assert output == output2


@pytest.mark.parametrize("checksum_flag", (None, "--md5", "--sha256"))
@pytest.mark.integration
def test_explicit(
    tmp_env: TmpEnvFixture,
    conda_cli: CondaCLIFixture,
    path_factory: PathFactoryFixture,
    checksum_flag: str | None,
    test_recipes_channel: Path,
) -> None:
    """Test that `conda list --explicit` output can be used to recreate an identical environment."""
    pkg = "dependent=1.0"  # has dependencies
    pkg2 = "dependency"
    with tmp_env(pkg) as prefix:
        assert package_is_installed(prefix, pkg)
        assert package_is_installed(prefix, pkg2)

        output, _, _ = conda_cli(
            "list",
            f"--prefix={prefix}",
            "--explicit",
            *([checksum_flag] if checksum_flag else ()),
        )

    env_txt = path_factory(suffix=".txt")
    env_txt.write_text(output)

    with tmp_env("--file", env_txt) as prefix2:
        assert package_is_installed(prefix2, pkg)
        assert package_is_installed(prefix2, pkg2)

        output2, _, _ = conda_cli(
            "list",
            f"--prefix={prefix2}",
            "--explicit",
            *([checksum_flag] if checksum_flag else ()),
        )
        assert output == output2
