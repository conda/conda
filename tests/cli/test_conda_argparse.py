# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from __future__ import absolute_import, division, print_function, unicode_literals

from logging import getLogger

import pytest

from conda.cli.main import generate_parser
from conda.cli.python_api import Commands, run_command
from conda.exceptions import CommandNotFoundError, EnvironmentLocationNotFound

log = getLogger(__name__)


def test_help_through_python_api():
    stdout, stderr, rc = run_command(Commands.HELP)
    assert rc == 0
    assert not stderr
    assert "\n    install" in stdout

    with pytest.raises(EnvironmentLocationNotFound):
        run_command(Commands.LIST, "-p", "not-a-real-path")

    stdout, stderr, rc = run_command(Commands.LIST, "-p", "not-a-real-path",
                                         use_exception_handler=True)
    assert rc == 1
    assert "Not a conda environment" in stderr
    assert not stdout


def test_parser_basics():
    p = generate_parser()
    with pytest.raises(CommandNotFoundError):
        p.parse_args(["blarg", "--flag"])

    args = p.parse_args(["install", "-vv"])
    assert args.verbosity == 2


def test_cli_args_as_list():
    out, err, rc = run_command(Commands.CONFIG, ["--show", "add_anaconda_token"])
    assert rc == 0


def test_cli_args_as_strings():
    out, err, rc = run_command(Commands.CONFIG, "--show", "add_anaconda_token")
    assert rc == 0
