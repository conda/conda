# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import json

from conda.testing import TmpEnvFixture
from conda.testing.integration import Commands, run_command


# conda list
def test_list(tmp_env: TmpEnvFixture):
    pkg = "ca-certificates"  # has no dependencies
    with tmp_env(pkg) as prefix:
        stdout, _, _ = run_command(Commands.LIST, prefix, "--json")
        assert any(item["name"] == pkg for item in json.loads(stdout))


# conda list --reverse
def test_list_reverse(tmp_env: TmpEnvFixture):
    pkg = "curl"  # has dependencies
    with tmp_env(pkg) as prefix:
        stdout, _, _ = run_command(Commands.LIST, prefix, "--json")
        names = [item["name"] for item in json.loads(stdout)]
        assert names == sorted(names)

        stdout, _, _ = run_command(Commands.LIST, prefix, "--reverse", "--json")
        names = [item["name"] for item in json.loads(stdout)]
        assert names == sorted(names, reverse=True)
