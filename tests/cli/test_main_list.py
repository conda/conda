# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import json
import re
import sys
from typing import TYPE_CHECKING

import pytest

from conda.base.constants import CONDA_LIST_FIELDS
from conda.common.configuration import CustomValidationError
from conda.core.prefix_data import PrefixData
from conda.exceptions import (
    CondaValueError,
    EnvironmentLocationNotFound,
    PackageNotInstalledError,
)
from conda.testing.integration import package_is_installed

if TYPE_CHECKING:
    from pathlib import Path

    from pytest_mock import MockerFixture

    from conda.testing.fixtures import (
        CondaCLIFixture,
        PathFactoryFixture,
        TmpEnvFixture,
    )


# Precompile for reuse in parameterized cases
MD5_HEX_RE = re.compile(r"#[0-9a-f]{32}")


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


@pytest.mark.parametrize(
    "args",
    [
        ["--canonical"],
        ["--export"],
        ["--explicit", "--md5"],
        ["--full-name"],
        ["--revisions", "--canonical"],
        ["--revisions", "--export"],
        ["--revisions", "--explicit", "--md5"],
        ["--revisions", "--full-name"],
        ["--json", "--canonical"],
        ["--json", "--export"],
        ["--json", "--explicit", "--md5"],
        ["--json", "--full-name"],
        ["--json", "--revisions", "--canonical"],
        ["--json", "--revisions", "--export"],
        ["--json", "--revisions", "--explicit", "--md5"],
        ["--json", "--revisions", "--full-name"],
    ],
)
def test_list_argument_variations(conda_cli: CondaCLIFixture, args: list[str]):
    # cover argument variations
    # mutually exclusive: --canonical, --export, --explicit, (default human readable)
    stdout, _, _ = conda_cli("list", *args)
    if "--md5" in args and "--revisions" not in args:
        assert MD5_HEX_RE.search(stdout)


def test_list_with_bad_prefix_raises(conda_cli: CondaCLIFixture):
    with pytest.raises(EnvironmentLocationNotFound, match="Not a conda environment"):
        conda_cli("list", "--prefix", "not-a-real-path")


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
    stdout, _, _ = conda_cli("list", "python", "--json")
    parsed = json.loads(stdout.strip())
    assert isinstance(parsed, list)
    assert "python" in [package["name"] for package in parsed]


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


def test_fields_dependent(test_recipes_channel: Path, conda_cli, tmp_env):
    pkg = "dependent=1.0"
    with tmp_env(pkg) as prefix:
        assert package_is_installed(prefix, pkg)

        output, _, rc = conda_cli(
            "list",
            f"--prefix={prefix}",
            "--fields",
            "name",
        )
        assert not rc
        assert "dependent" in output.splitlines()

        output, _, rc = conda_cli(
            "list", f"--prefix={prefix}", "--fields", "version", "dependent"
        )
        assert not rc
        assert "1.0" in output.splitlines()


def test_fields_all(conda_cli):
    output, _, rc = conda_cli(
        "list", f"--prefix={sys.prefix}", "--fields", ",".join(CONDA_LIST_FIELDS)
    )
    assert not rc


def test_fields_invalid(conda_cli):
    out, err, exc = conda_cli(
        "list",
        f"--prefix={sys.prefix}",
        "--fields",
        "invalid-field",
        raises=CustomValidationError,
    )
    assert "list_fields" in str(exc)
    assert "invalid-field" in str(exc)


def test_list_full_name(conda_cli):
    out, err, exc = conda_cli("list", f"--prefix={sys.prefix}", "--full-name", "python")
    assert "python" in out
    assert f"{sys.version_info.major}.{sys.version_info.minor}" in out


def test_list_full_name_no_results(conda_cli):
    out, err, exc = conda_cli(
        "list",
        f"--prefix={sys.prefix}",
        "--full-name",
        "does-not-exist",
        "--json",
        raises=PackageNotInstalledError,
    )


def test_exit_codes(conda_cli):
    # If the package is installed, with or without --check, the exit code must be 0
    out, err, rc = conda_cli("list", f"--prefix={sys.prefix}", "conda")
    assert rc == 0

    conda_cli(
        "list",
        f"--prefix={sys.prefix}",
        "does-not-exist",
        raises=CondaValueError,
    )


def test_list_size(
    tmp_env: TmpEnvFixture,
    conda_cli: CondaCLIFixture,
    test_recipes_channel: Path,
) -> None:
    pkg = "dependency"  # has no dependencies
    with tmp_env(pkg) as prefix:
        stdout, _, _ = conda_cli("list", "--prefix", prefix, "--size")
        assert "# environment size:" in stdout

        # Check for Size column in header
        lines = stdout.splitlines()
        header_line = next(line for line in lines if line.startswith("# Name"))
        assert "Size" in header_line

        # Check for size entries
        package_lines = [line for line in lines if not line.startswith("#")]
        assert len(package_lines) > 0
        for line in package_lines:
            # Size should be the last column
            assert any(
                line.strip().endswith(suffix) for suffix in ("B", "KB", "MB", "GB")
            )


def test_list_size_json(
    tmp_env: TmpEnvFixture,
    conda_cli: CondaCLIFixture,
    test_recipes_channel: Path,
) -> None:
    pkg = "dependency"
    with tmp_env(pkg) as prefix:
        stdout, _, _ = conda_cli("list", "--prefix", prefix, "--size", "--json")
        parsed = json.loads(stdout)
        assert isinstance(parsed, list)

        item = next((i for i in parsed if i["name"] == pkg), None)
        assert item is not None
        assert "size" in item
        assert isinstance(item["size"], int)
        assert item["size"] >= 0
