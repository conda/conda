from __future__ import absolute_import, division, print_function

import json

import pytest

from conda import config
from conda.cli.python_api import Commands, run_command
from tests.helpers import assert_equals, assert_in


def test_info():
    conda_info_out, conda_info_err, rc = run_command(Commands.INFO)
    assert_equals(conda_info_err, '')
    for name in ['platform', 'conda version', 'root environment',
                 'default environment', 'envs directories', 'package cache',
                 'channel URLs', 'config file', 'offline mode']:
        assert_in(name, conda_info_out)

    conda_info_e_out, conda_info_e_err, rc = run_command(Commands.INFO, '-e')
    assert_in('root', conda_info_e_out)
    assert_equals(conda_info_e_err, '')

    conda_info_s_out, conda_info_s_err, rc = run_command(Commands.INFO, '-s')
    assert_equals(conda_info_s_err, '')
    for name in ['sys.version', 'sys.prefix', 'sys.executable', 'conda location',
                 'conda-build', 'CIO_TEST', 'CONDA_DEFAULT_ENV', 'PATH', 'PYTHONPATH']:
        assert_in(name, conda_info_s_out)
    if config.platform == 'linux':
        assert_in('LD_LIBRARY_PATH', conda_info_s_out)
    if config.platform == 'osx':
        assert_in('DYLD_LIBRARY_PATH', conda_info_s_out)

    conda_info_all_out, conda_info_all_err, rc = run_command(Commands.INFO, '--all')
    assert_equals(conda_info_all_err, '')
    assert_in(conda_info_out, conda_info_all_out)
    assert_in(conda_info_e_out, conda_info_all_out)
    assert_in(conda_info_s_out, conda_info_all_out)


@pytest.mark.integration
def test_info_package_json():
    out, err, rc = run_command(Commands.INFO, "--json", "numpy=1.11.0=py35_0")
    assert err == ""

    out = json.loads(out)
    assert set(out.keys()) == {"numpy=1.11.0=py35_0"}
    assert len(out["numpy=1.11.0=py35_0"]) == 1
    assert isinstance(out["numpy=1.11.0=py35_0"], list)

    out, err, rc = run_command(Commands.INFO, "--json", "numpy")
    assert err == ""

    out = json.loads(out)
    assert set(out.keys()) == {"numpy"}
    assert len(out["numpy"]) > 1
    assert isinstance(out["numpy"], list)
