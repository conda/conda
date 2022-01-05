# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

import tempfile
from unittest import TestCase
from conda.testing.integration import run_command, Commands

import pytest

from conda.models.match_spec import MatchSpec
from conda.exceptions import UnsatisfiableError
from conda.gateways.disk.delete import rm_rf

try:
    from unittest.mock import patch
except ImportError:
    from mock import patch


@pytest.fixture
def fix_cli_install(tmpdir):
    prefix = tmpdir.mkdir("cli_install_prefix")
    test_env = tmpdir.mkdir("cli_install_test_env")
    run_command(Commands.CREATE, prefix, 'python=3.7')
    yield prefix, test_env
    rm_rf(prefix)
    rm_rf(test_env)


@pytest.mark.integration
def test_pre_link_message(fix_cli_install):
    prefix = fix_cli_install[0]
    with patch("conda.cli.common.confirm_yn") as mck:
        mck.return_value = True
        stdout, stderr, _ = run_command(
            Commands.INSTALL, prefix, "pre_link_messages_package", "--use-local"
        )
        assert "Lorem ipsum dolor sit amet, consectetur adipiscing elit." in stdout


@pytest.mark.integration
def test_find_conflicts_called_once(fix_cli_install):
    prefix, test_env = fix_cli_install
    bad_deps = {'python': {((MatchSpec("statistics"), MatchSpec("python[version='>=2.7,<2.8.0a0']")), 'python=3')}}

    with patch('conda.resolve.Resolve.find_conflicts') as monkey:
        monkey.side_effect = UnsatisfiableError(bad_deps, strict=True)
        with pytest.raises(UnsatisfiableError):
            # Statistics is a py27 only package allowing us a simple unsatisfiable case
            stdout, stderr, _ = run_command(Commands.INSTALL, prefix, 'statistics')
        assert monkey.call_count == 1

        monkey.reset_mock()
        with pytest.raises(UnsatisfiableError):
            stdout, stderr, _ = run_command(Commands.INSTALL, prefix, 'statistics', '--freeze-installed')
        assert monkey.call_count == 1

        monkey.reset_mock()
        with pytest.raises(UnsatisfiableError):
            stdout, stderr, _ = run_command(Commands.CREATE, test_env, 'statistics', 'python=3.7')
        assert monkey.call_count == 1
