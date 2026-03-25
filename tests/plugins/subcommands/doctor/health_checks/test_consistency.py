# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
"""Tests for the environment consistency health check."""

from __future__ import annotations

from typing import TYPE_CHECKING

from conda.base.constants import OK_MARK, X_MARK
from conda.common.serialize import yaml

if TYPE_CHECKING:
    from conda.testing.fixtures import CondaCLIFixture, TmpEnvFixture
    from tests.conftest import test_recipes_channel


def test_env_consistency_check_passes(
    tmp_env: TmpEnvFixture,
    conda_cli: CondaCLIFixture,
    test_recipes_channel: test_recipes_channel,
):
    """Test that environment consistency check passes for a valid environment."""
    with tmp_env("dependent") as prefix:
        out, _, _ = conda_cli("doctor", "--prefix", prefix)

        assert f"{OK_MARK} The environment is consistent.\n" in out


def test_env_consistency_check_fails(
    tmp_env: TmpEnvFixture,
    conda_cli: CondaCLIFixture,
    test_recipes_channel: test_recipes_channel,
):
    """Test that environment consistency check fails when dependencies are missing."""
    pkg_to_install = test_recipes_channel / "noarch" / "dependent-1.0-0.tar.bz2"

    with tmp_env(pkg_to_install) as prefix:
        out, _, _ = conda_cli("doctor", "--prefix", prefix)
        assert f"{X_MARK} The environment is not consistent.\n" in out


def test_env_consistency_check_fails_verbose(
    tmp_env: TmpEnvFixture,
    conda_cli: CondaCLIFixture,
    test_recipes_channel: test_recipes_channel,
):
    """Test verbose output when environment consistency check fails."""
    pkg_to_install = test_recipes_channel / "noarch" / "dependent-1.0-0.tar.bz2"

    expected_output_dict = {
        "dependent": {"missing": ["dependency[version='>=1.0,<2.0a0']"]}
    }
    expected_output_yaml = yaml.dumps(expected_output_dict)

    with tmp_env(pkg_to_install) as prefix:
        out, _, _ = conda_cli("doctor", "--verbose", "--prefix", prefix)
        assert f"{X_MARK} The environment is not consistent.\n" in out
        assert expected_output_yaml in out


def test_env_consistency_constrains_not_met(
    tmp_env: TmpEnvFixture,
    conda_cli: CondaCLIFixture,
    test_recipes_channel: test_recipes_channel,
):
    """Test that environment consistency check detects unmet constraints."""
    pkg_1_to_install = test_recipes_channel / "noarch" / "run_constrained-1.0-0.conda"
    pkg_2_to_install = test_recipes_channel / "noarch" / "dependency-1.0-0.tar.bz2"

    with tmp_env(pkg_1_to_install, pkg_2_to_install) as prefix:
        expected_output_dict = {
            "run_constrained": {
                "inconsistent": [
                    {
                        "expected": "dependency[version='>=2.0']",
                        "installed": "dependency[version='1.0']",
                    }
                ]
            }
        }
        expected_output_yaml = yaml.dumps(expected_output_dict)

        out, _, _ = conda_cli("doctor", "--verbose", "--prefix", prefix)
        assert f"{X_MARK} The environment is not consistent.\n" in out
        assert expected_output_yaml in out
