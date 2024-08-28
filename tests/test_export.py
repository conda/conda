# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import annotations

from contextlib import nullcontext
from typing import TYPE_CHECKING

import pytest

from conda.base.context import reset_context
from conda.exceptions import ParseError
from conda.misc import _match_specs_from_explicit
from conda.testing.integration import package_is_installed

if TYPE_CHECKING:
    from pytest import MonkeyPatch

    from conda.testing import CondaCLIFixture, PathFactoryFixture, TmpEnvFixture

pytestmark = pytest.mark.usefixtures("parametrized_solver_fixture")


@pytest.mark.integration
def test_export(
    tmp_env: TmpEnvFixture,
    conda_cli: CondaCLIFixture,
    path_factory: PathFactoryFixture,
    monkeypatch: MonkeyPatch,
):
    """Test that `conda list --export` output can be used to create a similar environment."""
    monkeypatch.setenv("CONDA_CHANNELS", "defaults")
    reset_context()
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


# Using --quiet here as a no-op flag for test simplicity
@pytest.mark.parametrize("checksum_flag", ("--quiet", "--md5", "--sha256"))
@pytest.mark.integration
def test_explicit(
    tmp_env: TmpEnvFixture,
    conda_cli: CondaCLIFixture,
    path_factory: PathFactoryFixture,
    checksum_flag: str,
):
    """Test that `conda list --explicit` output can be used to recreate an identical environment."""
    # use "cheap" packages with no dependencies
    with tmp_env("pkgs/main::zlib", "conda-forge::ca-certificates") as prefix:
        assert package_is_installed(prefix, "pkgs/main::zlib")
        assert package_is_installed(prefix, "conda-forge::ca-certificates")

        output, _, _ = conda_cli(
            "list", "--prefix", prefix, "--explicit", checksum_flag
        )

    env_txt = path_factory(suffix=".txt")
    env_txt.write_text(output)

    with tmp_env("--file", env_txt) as prefix2:
        assert package_is_installed(prefix2, "pkgs/main::zlib")
        assert package_is_installed(prefix2, "conda-forge::ca-certificates")

        output2, _, _ = conda_cli(
            "list", "--prefix", prefix2, "--explicit", checksum_flag
        )
        assert output == output2


@pytest.mark.parametrize(
    "url, checksum, raises",
    (
        [
            "https://conda.anaconda.org/conda-forge/noarch/doc8-1.1.1-pyhd8ed1ab_0.conda",
            "5e9e17751f19d03c4034246de428582e",
            None,
        ],
        [
            "https://conda.anaconda.org/conda-forge/noarch/conda-24.1.0-pyhd3eb1b0_0.conda",
            "2707f68aada792d1cf3a44c51d55b38b0cd65b0c192d2a5f9ef0550dc149a7d3",
            None,
        ],
        [
            "https://conda.anaconda.org/conda-forge/noarch/conda-24.1.0-pyhd3eb1b0_0.conda",
            "sha256:2707f68aada792d1cf3a44c51d55b38b0cd65b0c192d2a5f9ef0550dc149a7d3",
            None,
        ],
        [
            "https://conda.anaconda.org/conda-forge/noarch/conda-24.1.0-pyhd3eb1b0_0.conda",
            "sha123:2707f68aada792d1cf3a44c51d55b38b0cd65b0c192d2a5f9ef0550dc149a7d3",
            ParseError,
        ],
        [
            "https://conda.anaconda.org/conda-forge/noarch/conda-24.1.0-pyhd3eb1b0_0.conda",
            "md5:5e9e17751f19d03c4034246de428582e",  # this is not valid syntax; use without 'md5:'
            ParseError,
        ],
        [
            "doc8-1.1.1-pyhd8ed1ab_0.conda",
            "5e9e17751f19d03c4034246de428582e",
            None,
        ],
        [
            "../doc8-1.1.1-pyhd8ed1ab_0.conda",
            "5e9e17751f19d03c4034246de428582e",
            None,
        ],
        [
            "../doc8-1.1.1-pyhd8ed1ab_0.conda",
            "5e9e17751f19d03",
            ParseError,
        ],
    ),
)
def test_explicit_parser(url: str, checksum: str, raises: Exception | None):
    lines = [url + (f"#{checksum}" if checksum else "")]
    with pytest.raises(raises) if raises else nullcontext():
        specs = list(_match_specs_from_explicit(lines))
    if raises:
        return

    assert len(specs) == 1
    spec = specs[0]
    assert spec.get("url").split("/")[-1] == url.split("/")[-1]
    assert checksum.rsplit(":", 1)[-1] in (spec.get("md5"), spec.get("sha256"))
