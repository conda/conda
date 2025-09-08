# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

import json
from importlib.metadata import version
from logging import getLogger
from typing import TYPE_CHECKING

import pytest

from conda.base.context import context, reset_context
from conda.common.io import stderr_log_level
from conda.exceptions import (
    CondaEnvException,
    DryRunExit,
    EnvironmentLocationNotFound,
    PackagesNotFoundError,
)
from conda.gateways.disk.delete import path_is_clean
from conda.testing.integration import (
    PYTHON_BINARY,
    TEST_LOG_LEVEL,
    package_is_installed,
)

if TYPE_CHECKING:
    from pytest import MonkeyPatch

    from conda.testing.fixtures import CondaCLIFixture, TmpEnvFixture

log = getLogger(__name__)
stderr_log_level(TEST_LOG_LEVEL, "conda")
stderr_log_level(TEST_LOG_LEVEL, "requests")


def test_remove_all(tmp_env: TmpEnvFixture, conda_cli: CondaCLIFixture):
    with tmp_env("python") as prefix:
        assert (prefix / PYTHON_BINARY).exists()
        assert package_is_installed(prefix, "python")

        # regression test for #2154
        with pytest.raises(PackagesNotFoundError) as exc:
            conda_cli("remove", f"--prefix={prefix}", "python", "foo", "numpy", "--yes")
        exception_string = repr(exc.value)
        assert "PackagesNotFoundError" in exception_string
        assert "- numpy" in exception_string
        assert "- foo" in exception_string

        conda_cli("remove", f"--prefix={prefix}", "--all", "--yes")
        assert path_is_clean(prefix)


def test_remove_all_keep_env(tmp_env: TmpEnvFixture, conda_cli: CondaCLIFixture):
    with tmp_env("python") as prefix:
        assert (prefix / PYTHON_BINARY).exists()
        assert package_is_installed(prefix, "python")

        conda_cli("remove", f"--prefix={prefix}", "--all", "--keep-env", "--yes")
        assert not path_is_clean(prefix)


@pytest.mark.integration
@pytest.mark.usefixtures("parametrized_solver_fixture")
def test_remove_globbed_package_names(
    tmp_env: TmpEnvFixture,
    conda_cli: CondaCLIFixture,
):
    if context.solver == "libmamba" and version("conda_libmamba_solver") <= "24.1.0":
        pytest.xfail(
            reason="Removing using wildcards is not available in older versions of the libmamba solver.",
        )
    # classic takes too long with conda-forge
    channels = (
        "--repodata-fn",
        "current_repodata.json",
        "--override-channels",
        "-c",
        "defaults",
    )
    with tmp_env("zlib", "ca-certificates", *channels) as prefix:
        stdout, stderr, _ = conda_cli(
            "remove",
            "--yes",
            f"--prefix={prefix}",
            "*lib*",
            "--dry-run",
            "--json",
            f"--solver={context.solver}",
            *channels,
            raises=DryRunExit,
        )
        log.info(stdout)
        log.info(stderr)
        data = json.loads(stdout)
        assert data.get("success")
        assert any(pkg["name"] == "zlib" for pkg in data["actions"]["UNLINK"])
        if "LINK" in data["actions"]:
            assert all(pkg["name"] != "zlib" for pkg in data["actions"]["LINK"])
        # if ca-certificates is in the unlink list,
        # it should also be in the link list (reinstall)
        for package in data["actions"]["UNLINK"]:
            if package["name"] == "ca-certificates":
                assert any(
                    pkg["name"] == "ca-certificates" for pkg in data["actions"]["LINK"]
                )


def test_remove_nonexistent_env(conda_cli: CondaCLIFixture):
    with pytest.raises(EnvironmentLocationNotFound):
        conda_cli("remove", "--prefix=/non/existent/path", "--all")


def test_remove_all_default_activation_env(
    conda_cli: CondaCLIFixture,
    tmp_env: TmpEnvFixture,
    monkeypatch: MonkeyPatch,
):
    """Check that removing the default_activation_env raises an exception."""
    with tmp_env() as prefix:
        monkeypatch.setenv("CONDA_DEFAULT_ACTIVATION_ENV", prefix)
        reset_context()

        assert prefix == context.default_activation_prefix
        with pytest.raises(
            CondaEnvException,
            match=(
                "Cannot remove an environment if it is configured "
                "as `default_activation_env`."
            ),
        ):
            conda_cli(
                "remove",
                "--all",
                f"--prefix={prefix}",
            )
