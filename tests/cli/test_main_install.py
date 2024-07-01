# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from json import loads as json_loads
from pathlib import Path

import pytest
from pytest import MonkeyPatch

from conda.base.context import context, reset_context
from conda.core.prefix_data import PrefixData
from conda.exceptions import DirectoryNotACondaEnvironmentError, PackagesNotFoundError
from conda.gateways.disk.delete import path_is_clean, rm_rf
from conda.testing import CondaCLIFixture, TmpEnvFixture
from conda.testing.integration import package_is_installed


def test_install_freezes_env_by_default(
    test_recipes_channel: Path,
    tmp_env: TmpEnvFixture,
    conda_cli: CondaCLIFixture,
):
    with tmp_env("dependent=2.0") as prefix:
        assert package_is_installed(prefix, "dependent=2.0")
        # Install a version older than the last one
        conda_cli("install", f"--prefix={prefix}", "dependent=1.0", "--yes")

        stdout, stderr, _ = conda_cli("list", f"--prefix={prefix}", "--json")

        pkgs = json_loads(stdout)

        conda_cli(
            "install",
            f"--prefix={prefix}",
            "another_dependent",
            "--freeze-installed",
            "--yes",
        )

        PrefixData._cache_.clear()
        prefix_data = PrefixData(prefix)
        for pkg in pkgs:
            assert prefix_data.get(pkg["name"]).version == pkg["version"]


def test_install_mkdir(tmp_env: TmpEnvFixture, conda_cli: CondaCLIFixture):
    with tmp_env() as prefix:
        file = prefix / "tempfile.txt"
        file.write_text("test")
        dir = prefix / "conda-meta"
        assert dir.is_dir()
        assert file.exists()
        with pytest.raises(
            DirectoryNotACondaEnvironmentError,
            match="The target directory exists, but it is not a conda environment.",
        ):
            conda_cli("install", f"--prefix={dir}", "python", "--mkdir", "--yes")

        conda_cli("create", f"--prefix={dir}", "--yes")
        conda_cli("install", f"--prefix={dir}", "python", "--mkdir", "--yes")
        assert package_is_installed(dir, "python")

        rm_rf(prefix, clean_empty_parents=True)
        assert path_is_clean(dir)

        # regression test for #4849
        conda_cli(
            "install",
            f"--prefix={dir}",
            "python-dateutil",
            "python",
            "--mkdir",
            "--yes",
        )
        assert package_is_installed(dir, "python")
        assert package_is_installed(dir, "python-dateutil")


def test_conda_pip_interop_dependency_satisfied_by_pip(
    monkeypatch: MonkeyPatch, tmp_env: TmpEnvFixture, conda_cli: CondaCLIFixture
):
    monkeypatch.setenv("CONDA_PIP_INTEROP_ENABLED", "true")
    reset_context()
    assert context.pip_interop_enabled
    with tmp_env("python=3.10", "pip") as prefix:
        assert package_is_installed(prefix, "python=3.10")
        assert package_is_installed(prefix, "pip")
        conda_cli(
            "run",
            f"--prefix={prefix}",
            "--dev",
            *("python", "-m", "pip", "install", "itsdangerous"),
        )

        PrefixData._cache_.clear()
        output, error, _ = conda_cli("list", f"--prefix={prefix}")
        assert "itsdangerous" in output
        assert not error

        output, _, _ = conda_cli(
            "install",
            f"--prefix={prefix}",
            "flask",
            "--json",
        )
        json_obj = json_loads(output.strip())
        print(json_obj)
        assert any(rec["name"] == "flask" for rec in json_obj["actions"]["LINK"])
        assert not any(
            rec["name"] == "itsdangerous" for rec in json_obj["actions"]["LINK"]
        )

    with pytest.raises(PackagesNotFoundError):
        conda_cli("search", "not-a-real-package", "--json")


def test_install_from_extracted_package(
    tmp_pkgs_dir: Path, tmp_env: TmpEnvFixture, conda_cli: CondaCLIFixture
):
    def pkgs_dir_has_tarball(tarball_prefix):
        return any(
            tarball_prefix in f.name for f in tmp_pkgs_dir.iterdir() if f.is_file()
        )

    with tmp_env() as prefix:
        # First, make sure the openssl package is present in the cache,
        # downloading it if needed
        assert not pkgs_dir_has_tarball("openssl-")
        conda_cli("install", f"--prefix={prefix}", "openssl", "--yes")
        assert pkgs_dir_has_tarball("openssl-")

        # Then, remove the tarball but keep the extracted directory around
        conda_cli("clean", "--tarballs", "--yes")
        assert not pkgs_dir_has_tarball("openssl-")

    with tmp_env() as prefix:
        # Finally, install openssl, enforcing the use of the extracted package.
        # We expect that the tarball does not appear again because we simply
        # linked the package from the extracted directory. If the tarball
        # appeared again, we decided to re-download the package for some reason.
        conda_cli("install", f"--prefix={prefix}", "openssl", "--offline", "--yes")
        assert not pkgs_dir_has_tarball("openssl-")
