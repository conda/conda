# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import re
from json import loads as json_loads
from unittest import TestCase

import pytest

from conda.base.context import conda_tests_ctxt_mgmt_def_pol, context
from conda.common.io import env_var
from conda.testing import TmpEnvFixture
from conda.testing.integration import (
    Commands,
    get_conda_list_tuple,
    package_is_installed,
    run_command,
)


@pytest.mark.integration
class PriorityIntegrationTests(TestCase):
    def test_channel_order_channel_priority_true(self, tmp_env: TmpEnvFixture):
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

                payload, _, _ = run_command(
                    Commands.CONFIG, prefix, "--get", "channels", "--json"
                )
                default_channels = json_loads(payload)["get"].get("channels")
                if default_channels:
                    run_command(Commands.CONFIG, prefix, "--remove-key", "channels")

                # add conda-forge channel
                o, e, _ = run_command(
                    Commands.CONFIG,
                    prefix,
                    "--prepend",
                    "channels",
                    "conda-forge",
                    "--json",
                )
                assert context.channels == ("conda-forge", "defaults"), o + e
                # update --all
                update_stdout, _, _ = run_command(Commands.UPDATE, prefix, "--all")

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
                python_tuple = get_conda_list_tuple(prefix, "python")
                assert python_tuple[3] == "conda-forge"
                # conda list should show pycosat coming from conda-forge
                pycosat_tuple = get_conda_list_tuple(prefix, "pycosat")
                assert pycosat_tuple[3] == "conda-forge"

    def test_channel_priority_update(self, tmp_env: TmpEnvFixture):
        """This case will fail now."""
        with tmp_env("python=3.8", "pycosat") as prefix:
            assert package_is_installed(prefix, "python")

            # clear channels config first to not assume default is defaults
            payload, _, _ = run_command(
                Commands.CONFIG, prefix, "--get", "channels", "--json"
            )
            default_channels = json_loads(payload)["get"].get("channels")
            if default_channels:
                run_command(Commands.CONFIG, prefix, "--remove-key", "channels")

            # add conda-forge channel
            o, e, _ = run_command(
                Commands.CONFIG,
                prefix,
                "--prepend",
                "channels",
                "conda-forge",
                "--json",
            )
            assert context.channels == ("conda-forge", "defaults"), o + e

            # update python
            update_stdout, _, _ = run_command(Commands.UPDATE, prefix, "python")

            # pycosat should be in the SUPERSEDED list
            superceded_split = update_stdout.split("UPDATED")
            assert len(superceded_split) == 2
            assert "conda-forge" in superceded_split[1]

            # python sys.version should show conda-forge python
            python_tuple = get_conda_list_tuple(prefix, "python")
            assert python_tuple[3] == "conda-forge"
