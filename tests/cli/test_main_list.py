# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import json

from conda.testing.integration import Commands, make_temp_env, run_command


# conda list
def test_list():
    pkg = "ca-certificates"  # has no dependencies
    with make_temp_env(pkg) as prefix:
        stdout, _, _ = run_command(Commands.LIST, prefix, "--json")
        assert any(item["name"] == pkg for item in json.loads(stdout))


# conda list --reverse
def test_list_reverse():
    pkg = "curl"  # has dependencies
    with make_temp_env(pkg) as prefix:
        stdout, _, _ = run_command(Commands.LIST, prefix, "--json")
        names = [item["name"] for item in json.loads(stdout)]
        assert names == sorted(names)

        stdout, _, _ = run_command(Commands.LIST, prefix, "--reverse", "--json")
        names = [item["name"] for item in json.loads(stdout)]
        assert names == sorted(names, reverse=True)
