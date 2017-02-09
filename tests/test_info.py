from __future__ import print_function, absolute_import, division
import json

import pytest

from conda import config
from conda.cli import main_info

from tests.helpers import run_conda_command, assert_in, assert_equals


@pytest.mark.integration
def test_info():
    conda_info_out, conda_info_err = run_conda_command('info')
    assert_equals(conda_info_err, '')
    for name in ['platform', 'conda version', 'root environment',
                 'default environment', 'envs directories', 'package cache',
                 'channel URLs', 'config file', 'offline mode']:
        assert_in(name, conda_info_out)

    conda_info_e_out, conda_info_e_err = run_conda_command('info', '-e')
    assert_in('root', conda_info_e_out)
    assert_equals(conda_info_e_err, '')

    conda_info_s_out, conda_info_s_err = run_conda_command('info', '-s')
    assert_equals(conda_info_s_err, '')
    for name in ['sys.version', 'sys.prefix', 'sys.executable', 'conda location',
                 'conda-build', 'CIO_TEST', 'CONDA_DEFAULT_ENV', 'PATH', 'PYTHONPATH']:
        assert_in(name, conda_info_s_out)
    if config.platform == 'linux':
        assert_in('LD_LIBRARY_PATH', conda_info_s_out)
    if config.platform == 'osx':
        assert_in('DYLD_LIBRARY_PATH', conda_info_s_out)

    conda_info_all_out, conda_info_all_err = run_conda_command('info', '--all')
    assert_equals(conda_info_all_err, '')
    assert_in(conda_info_out, conda_info_all_out)
    assert_in(conda_info_e_out, conda_info_all_out)
    assert_in(conda_info_s_out, conda_info_all_out)


@pytest.mark.integration
def test_info_package_json():
    out, err = run_conda_command("info", "--json", "numpy=1.11.0=py35_0")
    assert err == ""

    out = json.loads(out)
    assert set(out.keys()) == {"numpy=1.11.0=py35_0"}
    assert len(out["numpy=1.11.0=py35_0"]) == 1
    assert isinstance(out["numpy=1.11.0=py35_0"], list)

    out, err = run_conda_command("info", "--json", "numpy")
    assert err == ""

    out = json.loads(out)
    assert set(out.keys()) == {"numpy"}
    assert len(out["numpy"]) > 1
    assert isinstance(out["numpy"], list)
