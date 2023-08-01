# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import json

import pytest

from conda.testing import CondaCLIFixture
from conda.testing.helpers import assert_equals, assert_in


def test_info(conda_cli: CondaCLIFixture):
    conda_info_out, conda_info_err, rc = conda_cli("info")
    assert_equals(conda_info_err, "")
    for name in (
        "platform",
        "conda version",
        "envs directories",
        "package cache",
        "channel URLs",
        "config file",
        "offline mode",
    ):
        assert_in(name, conda_info_out)

    conda_info_e_out, conda_info_e_err, rc = conda_cli("info", "-e")
    assert_in("base", conda_info_e_out)
    assert_equals(conda_info_e_err, "")

    conda_info_s_out, conda_info_s_err, rc = conda_cli("info", "-s")
    assert_equals(conda_info_s_err, "")
    for name in (
        "sys.version",
        "sys.prefix",
        "sys.executable",
        "conda location",
        "conda-build",
        "PATH",
    ):
        assert_in(name, conda_info_s_out)

    conda_info_all_out, conda_info_all_err, rc = conda_cli("info", "--all")
    assert_equals(conda_info_all_err, "")
    assert_in(conda_info_out, conda_info_all_out)
    assert_in(conda_info_e_out, conda_info_all_out)
    assert_in(conda_info_s_out, conda_info_all_out)


@pytest.mark.integration
def test_info_package_json(conda_cli: CondaCLIFixture):
    # This is testing deprecated behaviour. The CLI already says:
    # WARNING: 'conda info package_name' is deprecated. Use 'conda search package_name --info'.
    stdout, _, _ = conda_cli(
        "info", "--json", "pkgs/main::itsdangerous=2.0.0=pyhd3eb1b0_0"
    )
    stdout = json.loads(stdout)
    assert set(stdout.keys()) == {"pkgs/main::itsdangerous=2.0.0=pyhd3eb1b0_0"}
    assert len(stdout["pkgs/main::itsdangerous=2.0.0=pyhd3eb1b0_0"]) == 1
    assert isinstance(stdout["pkgs/main::itsdangerous=2.0.0=pyhd3eb1b0_0"], list)

    stdout, _, _ = conda_cli("info", "--json", "pkgs/main::itsdangerous")
    stdout = json.loads(stdout)
    assert set(stdout.keys()) == {"pkgs/main::itsdangerous"}
    assert len(stdout["pkgs/main::itsdangerous"]) > 1
    assert isinstance(stdout["pkgs/main::itsdangerous"], list)
