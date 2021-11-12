# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from __future__ import absolute_import, division, print_function, unicode_literals

from contextlib import contextmanager
from os.path import isdir, join, lexists
from tempfile import gettempdir
from unittest import TestCase
from uuid import uuid4

import pytest

from conda.common.compat import on_win, odict
from conda.core.prefix_data import PrefixData, get_conda_anchor_files_and_records
from tests.data.env_metadata import (
    PATH_TEST_ENV_1, PATH_TEST_ENV_2, PATH_TEST_ENV_3, PATH_TEST_ENV_4,
)
from conda.base.constants import PREFIX_STATE_FILE
from conda.gateways.disk import mkdir_p
from conda.gateways.disk.delete import rm_rf
from conda.exceptions import CorruptedEnvironmentError


ENV_VARS_FILE = '''
{
  "version": 1,
  "env_vars": {
    "ENV_ONE": "one",
    "ENV_TWO": "you",
    "ENV_THREE": "me"
  }
}'''


def _print_output(*args):
    """Helper function to print output in case of failed tests."""
    for arg in args:
        print(arg)
    print('\n')


class DummyPythonRecord:
    files = []


@contextmanager
def set_on_win(val):
    import conda.common.path
    import conda.common.pkg_formats.python
    import conda.core.prefix_data
    on_win_saved = conda.common.path.on_win
    win_path_ok_saved_1 = conda.core.prefix_data.win_path_ok
    win_path_ok_saved_2 = conda.common.pkg_formats.python.win_path_ok
    rm_rf_saved = conda.core.prefix_data.rm_rf
    try:
        conda.common.path.on_win = val
        conda.core.prefix_data.rm_rf = lambda x: None
        if val and not on_win:
            conda.core.prefix_data.win_path_ok = lambda x: x
            conda.common.pkg_formats.python.win_path_ok = lambda x: x
        yield
    finally:
        conda.common.path.on_win = on_win_saved
        conda.core.prefix_data.win_path_ok = win_path_ok_saved_1
        conda.common.pkg_formats.python.win_path_ok = win_path_ok_saved_2
        conda.core.prefix_data.rm_rf = rm_rf_saved


def test_pip_interop_windows():
    test_cases = (
        (PATH_TEST_ENV_3,
         ('babel', 'backports-functools-lru-cache', 'chardet', 'cheroot', 'cherrypy',
         'cssselect', 'dask', 'django', 'django-phonenumber-field', 'django-twilio',
         'entrypoints', 'h5py', 'idna', 'jaraco-functools', 'lxml', 'more-itertools',
         'numpy', 'parsel', 'phonenumberslite', 'pluggy', 'portend', 'py', 'pyjwt',
         'pyopenssl', 'pytz', 'pywin32', 'pywin32-ctypes', 'queuelib', 'requests',
         'scrapy', 'service-identity', 'six', 'tempora', 'tox', 'urllib3', 'virtualenv',
         'w3lib')
        ),
        (PATH_TEST_ENV_4,
         ('asn1crypto', 'attrs', 'automat', 'babel', 'backports-functools-lru-cache',
         'cffi', 'chardet', 'cheroot', 'cherrypy', 'configparser', 'constantly',
         'cryptography', 'cssselect', 'dask', 'django', 'django-phonenumber-field',
         'django-twilio', 'entrypoints', 'enum34', 'functools32', 'h5py', 'hdf5storage',
         'hyperlink', 'idna', 'incremental', 'ipaddress', 'jaraco-functools', 'keyring',
         'lxml', 'more-itertools', 'numpy', 'parsel', 'phonenumberslite', 'pluggy',
        'portend', 'py', 'pyasn1', 'pyasn1-modules', 'pycparser', 'pydispatcher',
        'pyhamcrest', 'pyjwt', 'pyopenssl', 'pytz', 'pywin32', 'pywin32-ctypes',
        'queuelib', 'requests', 'scrapy', 'service-identity', 'six', 'tempora', 'tox',
        'twilio', 'twisted', 'urllib3', 'virtualenv', 'w3lib', 'zope-interface')
        ),
    )

    for path, expected_output in test_cases:
        with set_on_win(True):
            if isdir(path):
                prefixdata = PrefixData(path, pip_interop_enabled=True)
                prefixdata.load()
                records = prefixdata._load_site_packages()
                record_names = tuple(sorted(records.keys()))
                print('RECORDS', record_names)
                assert len(record_names), len(expected_output)
                _print_output(expected_output, record_names)
                for record_name in record_names:
                    _print_output(record_name)
                    assert record_name in expected_output
                for record_name in expected_output:
                    _print_output(record_name)
                    assert record_name in record_names


def test_pip_interop_osx():
    test_cases = (
        (PATH_TEST_ENV_1,
         ('asn1crypto', 'babel', 'backports-functools-lru-cache', 'cffi', 'chardet',
          'cheroot', 'cherrypy', 'configparser', 'cryptography', 'cssselect', 'dask',
          'django', 'django-phonenumber-field', 'django-twilio', 'entrypoints',
          'enum34', 'h5py', 'idna', 'ipaddress', 'jaraco-functools', 'lxml',
          'more-itertools', 'numpy', 'parsel', 'phonenumberslite', 'pip', 'pluggy',
          'portend', 'py', 'pycparser', 'pyjwt', 'pyopenssl', 'pytz', 'queuelib',
          'requests', 'scrapy', 'service-identity', 'six', 'tempora', 'tox', 'twisted',
          'urllib3', 'virtualenv', 'w3lib')
        ),
        (PATH_TEST_ENV_2,
         ('asn1crypto', 'attrs', 'automat', 'babel', 'backports-functools-lru-cache',
          'cffi', 'chardet', 'cheroot', 'cherrypy', 'constantly', 'cryptography',
          'cssselect', 'dask', 'django', 'django-phonenumber-field', 'django-twilio',
          'entrypoints', 'h5py', 'hdf5storage', 'hyperlink', 'idna', 'incremental',
          'jaraco-functools', 'keyring', 'lxml', 'more-itertools', 'numpy', 'parsel',
          'phonenumberslite', 'pip', 'pluggy', 'portend', 'py', 'pyasn1', 'pyasn1-modules',
          'pycparser', 'pydispatcher', 'pyhamcrest', 'pyjwt', 'pyopenssl', 'pysocks', 'pytz',
          'queuelib', 'requests', 'scrapy', 'service-identity', 'six', 'tempora', 'tox',
          'twilio', 'twisted', 'urllib3', 'virtualenv', 'w3lib', 'zope-interface')
        ),
    )

    for path, expected_output in test_cases:
        if isdir(path):
            with set_on_win(False):
                prefixdata = PrefixData(path, pip_interop_enabled=True)
                prefixdata.load()
                records = prefixdata._load_site_packages()
                record_names = tuple(sorted(records.keys()))
                print('RECORDS', record_names)
                assert len(record_names), len(expected_output)
                _print_output(expected_output, record_names)
                for record_name in record_names:
                    _print_output(record_name)
                    assert record_name in expected_output
                for record_name in expected_output:
                    _print_output(record_name)
                    assert record_name in record_names


def test_get_conda_anchor_files_and_records():
    valid_tests = [
        'v/site-packages/spam.egg-info/PKG-INFO',
        'v/site-packages/foo.dist-info/RECORD',
        'v/site-packages/bar.egg-info',
    ]
    invalid_tests = [
        'v/site-packages/valid-package/_vendor/invalid-now.egg-info/PKG-INFO',
        'i/site-packages/stuff.egg-link',
        'i/spam.egg-info/PKG-INFO',
        'i/foo.dist-info/RECORD',
        'i/bar.egg-info',
        'i/site-packages/spam',
        'i/site-packages/foo',
        'i/site-packages/bar',
    ]
    tests = valid_tests + invalid_tests
    records = []
    for path in tests:
        record = DummyPythonRecord()
        record.files = [path]
        records.append(record)

    output = get_conda_anchor_files_and_records("v/site-packages", records)
    expected_output = odict()
    for i in range(len(valid_tests)):
        expected_output[valid_tests[i]] = records[i]

    _print_output(output, expected_output)
    assert output == expected_output


def test_corrupt_unicode_conda_meta_json():
    """Test for graceful failure if a Unicode corrupt file exists in conda-meta."""
    with pytest.raises(CorruptedEnvironmentError):
        PrefixData("tests/data/corrupt/unicode").load()


def test_corrupt_json_conda_meta_json():
    """Test for graceful failure if a JSON corrupt file exists in conda-meta."""
    with pytest.raises(CorruptedEnvironmentError):
        PrefixData("tests/data/corrupt/json").load()


class PrefixDatarUnitTests(TestCase):

    def setUp(self):
        tempdirdir = gettempdir()
        dirname = str(uuid4())[:8]
        self.prefix = join(tempdirdir, dirname)
        mkdir_p(self.prefix)
        assert isdir(self.prefix)
        mkdir_p(join(self.prefix, 'conda-meta'))
        activate_env_vars = join(self.prefix, PREFIX_STATE_FILE)
        with open(activate_env_vars, 'w') as f:
            f.write(ENV_VARS_FILE)
        self.pd = PrefixData(self.prefix)

    def tearDown(self):
        rm_rf(self.prefix)
        assert not lexists(self.prefix)

    def test_get_environment_env_vars(self):
        ex_env_vars = {
            "ENV_ONE": "one",
            "ENV_TWO": "you",
            "ENV_THREE": "me"
        }
        env_vars = self.pd.get_environment_env_vars()
        assert ex_env_vars == env_vars

    def test_set_unset_environment_env_vars(self):
        env_vars_one = {
            "ENV_ONE": "one",
            "ENV_TWO": "you",
            "ENV_THREE": "me",
        }
        env_vars_add = {
            "ENV_ONE": "one",
            "ENV_TWO": "you",
            "ENV_THREE": "me",
            "WOAH": "dude"
        }
        self.pd.set_environment_env_vars({"WOAH":"dude"})
        env_vars = self.pd.get_environment_env_vars()
        assert env_vars_add == env_vars

        self.pd.unset_environment_env_vars(['WOAH'])
        env_vars = self.pd.get_environment_env_vars()
        assert env_vars_one == env_vars

    def test_set_unset_environment_env_vars_no_exist(self):
        env_vars_one = {
            "ENV_ONE": "one",
            "ENV_TWO": "you",
            "ENV_THREE": "me",
        }
        self.pd.unset_environment_env_vars(['WOAH'])
        env_vars = self.pd.get_environment_env_vars()
        assert env_vars_one == env_vars
