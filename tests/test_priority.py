# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import re
from json import loads as json_loads
from unittest import TestCase

import pytest

from conda.base.context import conda_tests_ctxt_mgmt_def_pol, context
from conda.common.io import env_var
from conda.core.prefix_data import PrefixData
from conda.testing import CondaCLIFixture, TmpEnvFixture
from conda.testing.integration import package_is_installed


@pytest.mark.integration
def test_channel_order_channel_priority_true(
    tmp_env: TmpEnvFixture, conda_cli: CondaCLIFixture
):
    # This is broken, tmp_env will reset the context. We get away with it, but really
    # we need a function that does both these at the same time.
    with env_var(
        "CONDA_PINNED_PACKAGES",
        "python=3.8",
        stack_callback=conda_tests_ctxt_mgmt_def_pol,
    ):
        with tmp_env("pycosat=0.6.3") as prefix:
            assert package_is_installed(prefix, "python=3.8")
            assert package_is_installed(prefix, "pycosat")

            payload, _, _ = conda_cli("config", "--get", "channels", "--json")
            default_channels = json_loads(payload)["get"].get("channels")
            if default_channels:
                conda_cli("config", "--remove-key", "channels")

            # add conda-forge channel
            o, e, _ = conda_cli(
                "config",
                "--prepend",
                "channels",
                "conda-forge",
                "--json",
            )
            assert context.channels == ("conda-forge", "defaults"), o + e
            # update --all
            update_stdout, _, _ = conda_cli("update", "--prefix", prefix, "--all")

            # this assertion works with the pinned_packages config to make sure
            # conda update --all still respects the pinned python version
            assert package_is_installed(prefix, "python=3.8")

            # pycosat should be in the SUPERSEDED list
            # after the 4.4 solver work, looks like it's in the DOWNGRADED list
            # This language needs changed anyway here.
            # For packages that CHANGE because they're being moved to a higher-priority channel
            # the message should be
            #
            # The following packages will be UPDATED to a higher-priority channel:
            #
            installed_str, x = update_stdout.split("UPDATED")
            assert re.search(
                r"pkgs/main::pycosat-0.6.3-py38h[^\s]+ --> conda-forge::pycosat", x
            )

            # python sys.version should show conda-forge python
            assert PrefixData(prefix).get("python").channel.name == "conda-forge"

            # conda list should show pycosat coming from conda-forge
            assert PrefixData(prefix).get("pycosat").channel.name == "conda-forge"


@pytest.mark.integration
def test_channel_priority_update(tmp_env: TmpEnvFixture, conda_cli: CondaCLIFixture):
    """This case will fail now."""
    with tmp_env("python=3.8", "pycosat") as prefix:
        assert package_is_installed(prefix, "python")

        # clear channels config first to not assume default is defaults
        payload, _, _ = conda_cli("config", "--get", "channels", "--json")
        default_channels = json_loads(payload)["get"].get("channels")
        if default_channels:
            conda_cli("config", "--remove-key", "channels")

        # add conda-forge channel
        o, e, _ = conda_cli(
            "config",
            "--prepend",
            "channels",
            "conda-forge",
            "--json",
        )
        assert context.channels == ("conda-forge", "defaults"), o + e

        # update python
        update_stdout, _, _ = conda_cli("update", "--prefix", prefix, "python")

        # pycosat should be in the SUPERSEDED list
        superceded_split = update_stdout.split("UPDATED")
        assert len(superceded_split) == 2
        assert "conda-forge" in superceded_split[1]

        # python sys.version should show conda-forge python
        assert PrefixData(prefix).get("python").channel.name == "conda-forge"
