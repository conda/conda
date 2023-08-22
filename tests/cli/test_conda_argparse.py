# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import re
from logging import getLogger

import pytest

from conda.cli.conda_argparse import generate_parser
from conda.cli.python_api import Commands, run_command
from conda.exceptions import CommandNotFoundError, EnvironmentLocationNotFound

log = getLogger(__name__)


def test_list_through_python_api():
    with pytest.raises(EnvironmentLocationNotFound):
        run_command(Commands.LIST, "-p", "not-a-real-path")

    stdout, stderr, rc = run_command(
        Commands.LIST, "-p", "not-a-real-path", use_exception_handler=True
    )
    assert rc == 1
    assert "Not a conda environment" in stderr
    assert not stdout

    # cover argument variations
    # mutually exclusive: --canonical, --export, --explicit, (default human readable)
    args = [["--canonical"], ["--export"], ["--explicit", "--md5"], ["--full-name"]]
    for json_revisions in [], ["--json"], ["-r"], ["-r", "--json"]:
        for arg in args:
            stdout, stderr, rc = run_command(
                Commands.LIST, *(arg + json_revisions), use_exception_handler=True
            )
            if "--md5" in args:
                assert re.search(r"#[0-9a-f]{32}", stdout)


def test_parser_basics():
    p = generate_parser()
    with pytest.raises(SystemExit, match="2"):
        p.parse_args(["blarg", "--flag"])

    args = p.parse_args(["install", "-vv"])
    assert args.verbosity == 2


def test_cli_args_as_list():
    out, err, rc = run_command(Commands.CONFIG, ["--show", "add_anaconda_token"])
    assert rc == 0


def test_cli_args_as_strings():
    out, err, rc = run_command(Commands.CONFIG, "--show", "add_anaconda_token")
    assert rc == 0
