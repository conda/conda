# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import re
from logging import getLogger

import pytest

from conda.cli.conda_argparse import generate_parser
from conda.exceptions import EnvironmentLocationNotFound
from conda.testing import CondaCLIFixture

log = getLogger(__name__)


def test_list_through_python_api(conda_cli: CondaCLIFixture):
    with pytest.raises(EnvironmentLocationNotFound, match="Not a conda environment"):
        conda_cli("list", "--prefix", "not-a-real-path")

    # cover argument variations
    # mutually exclusive: --canonical, --export, --explicit, (default human readable)
    for args1 in [[], ["--json"]]:
        for args2 in [[], ["--revisions"]]:
            for args3 in [
                ["--canonical"],
                ["--export"],
                ["--explicit", "--md5"],
                ["--full-name"],
            ]:
                args = (*args1, *args2, *args3)
                stdout, _, _ = conda_cli("list", *args)
                if "--md5" in args and "--revisions" not in args:
                    assert re.search(r"#[0-9a-f]{32}", stdout)


def test_parser_basics():
    p = generate_parser()
    with pytest.raises(SystemExit, match="2"):
        p.parse_args(["blarg", "--flag"])

    args = p.parse_args(["install", "-vv"])
    assert args.verbosity == 2


def test_cli_args_as_strings(conda_cli: CondaCLIFixture):
    stdout, stderr, err = conda_cli("config", "--show", "add_anaconda_token")
    assert stdout
    assert not stderr
    assert not err
