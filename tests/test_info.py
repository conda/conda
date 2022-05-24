# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from __future__ import absolute_import, division, print_function

import json

import pytest
import sys

from conda.base.context import conda_tests_ctxt_mgmt_def_pol
from conda.cli.python_api import Commands, run_command
from conda.common.io import env_var
from conda.testing.helpers import assert_equals, assert_in

try:
    from unittest.mock import Mock, patch
except ImportError:
    from mock import Mock, patch


def test_info():
    conda_info_out, conda_info_err, rc = run_command(Commands.INFO)
    assert_equals(conda_info_err, '')
    for name in ['platform', 'conda version',
                 'envs directories', 'package cache',
                 'channel URLs', 'config file', 'offline mode']:
        assert_in(name, conda_info_out)

    conda_info_e_out, conda_info_e_err, rc = run_command(Commands.INFO, '-e')
    assert_in('base', conda_info_e_out)
    assert_equals(conda_info_e_err, '')

    conda_info_s_out, conda_info_s_err, rc = run_command(Commands.INFO, '-s')
    assert_equals(conda_info_s_err, '')
    for name in ['sys.version', 'sys.prefix', 'sys.executable', 'conda location',
                 'conda-build', 'PATH']:
        assert_in(name, conda_info_s_out)

    conda_info_all_out, conda_info_all_err, rc = run_command(Commands.INFO, '--all')
    assert_equals(conda_info_all_err, '')
    assert_in(conda_info_out, conda_info_all_out)
    assert_in(conda_info_e_out, conda_info_all_out)
    assert_in(conda_info_s_out, conda_info_all_out)


@pytest.mark.integration
def test_info_package_json():
    out, err, rc = run_command(Commands.INFO, "--json", "itsdangerous=1.0.0=py37_0")

    out = json.loads(out)
    assert set(out.keys()) == {"itsdangerous=1.0.0=py37_0"}
    assert len(out["itsdangerous=1.0.0=py37_0"]) == 1
    assert isinstance(out["itsdangerous=1.0.0=py37_0"], list)

    out, err, rc = run_command(Commands.INFO, "--json", "itsdangerous")

    out = json.loads(out)
    assert set(out.keys()) == {"itsdangerous"}
    assert len(out["itsdangerous"]) > 1
    assert isinstance(out["itsdangerous"], list)


@pytest.mark.skipif(True, reason="only temporary")
@patch('conda.cli.conda_argparse.do_call', side_effect=KeyError('blarg'))
def test_get_info_dict(cli_install_mock):
    # This test patches conda.cli.install.install to throw an artificial exception.
    # What we're looking for here is the proper behavior for how error reports work with
    # collecting `conda info` in this situation.
    with env_var('CONDA_REPORT_ERRORS', 'false', stack_callback=conda_tests_ctxt_mgmt_def_pol):
        out, err, _ = run_command(Commands.CREATE, "-n", "blargblargblarg", "blarg", "--dry-run", "--json",
                                  use_exception_handler=True)
        assert cli_install_mock.call_count == 1
        sys.stdout.write(out)
        sys.stderr.write(err)
        assert not err
        json_obj = json.loads(out)
        assert json_obj['conda_info']['conda_version']

        out, err, _ = run_command(Commands.CREATE, "-n", "blargblargblarg", "blarg", "--dry-run",
                                  use_exception_handler=True)
        sys.stderr.write(out)
        sys.stderr.write(err)
        assert "conda info could not be constructed" not in err
        assert not out
