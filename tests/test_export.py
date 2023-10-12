# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import pytest
from pytest import MonkeyPatch

from conda.base.context import reset_context
from conda.testing import CondaCLIFixture, PathFactoryFixture, TmpEnvFixture
from conda.testing.integration import package_is_installed


@pytest.mark.integration
def test_export(
    tmp_env: TmpEnvFixture,
    conda_cli: CondaCLIFixture,
    path_factory: PathFactoryFixture,
    monkeypatch: MonkeyPatch,
    request
):
    """Test that `conda list --export` output can be used to create a similar environment."""
    monkeypatch.setenv("CONDA_CHANNELS", "defaults")
    reset_context()

    # https://github.com/conda/conda/pull/12984#issuecomment-1749634162
    from conda.base.context import context
    request.applymarker(pytest.mark.xfail(context.solver == "libmamba", reason="see PR #12984", strict=True))

    # assert context.channels == ("defaults",)

    # use "cheap" packages with no dependencies
    with tmp_env("pkgs/main::zlib") as prefix:
        assert package_is_installed(prefix, "pkgs/main::zlib")

        output, _, _ = conda_cli("list", "--prefix", prefix, "--export")

        env_txt = path_factory(suffix=".txt")
        env_txt.write_text(output)

        with tmp_env("--file", env_txt) as prefix2:
            assert package_is_installed(prefix, "pkgs/main::zlib")

            output2, _, _ = conda_cli("list", "--prefix", prefix2, "--export")
            assert output == output2


@pytest.mark.integration
def test_explicit(
    tmp_env: TmpEnvFixture,
    conda_cli: CondaCLIFixture,
    path_factory: PathFactoryFixture,
    request
):
    """Test that `conda list --explicit` output can be used to recreate an identical environment."""
    # https://github.com/conda/conda/pull/12984#issuecomment-1749634162
    from conda.base.context import context
    request.applymarker(pytest.mark.xfail(context.solver == "libmamba", reason="see PR #12984", strict=True))

    # use "cheap" packages with no dependencies
    with tmp_env("pkgs/main::zlib", "conda-forge::ca-certificates") as prefix:
        assert package_is_installed(prefix, "pkgs/main::zlib")
        assert package_is_installed(prefix, "conda-forge::ca-certificates")

        output, _, _ = conda_cli("list", "--prefix", prefix, "--explicit")

        env_txt = path_factory(suffix=".txt")
        env_txt.write_text(output)

        with tmp_env("--file", env_txt) as prefix2:
            assert package_is_installed(prefix2, "pkgs/main::zlib")
            assert package_is_installed(prefix2, "conda-forge::ca-certificates")

            output2, _, _ = conda_cli("list", "--prefix", prefix2, "--explicit")
            assert output == output2
