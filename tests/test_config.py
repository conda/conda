# (c) 2012-2014 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.
import os
from os.path import dirname, join, exists
from contextlib import contextmanager
from tempfile import mktemp
import unittest

import pytest

import conda.config as config
from conda.utils import get_yaml

from tests.helpers import run_conda_command

yaml = get_yaml()

# use condarc from source tree to run these tests against
config.rc_path = join(dirname(__file__), 'condarc')

def _get_default_urls():
    return ['http://repo.continuum.io/pkgs/free',
            'http://repo.continuum.io/pkgs/pro']
config.get_default_urls = _get_default_urls

# unset CIO_TEST.  This is a Continuum-internal variable that draws packages from an internal server instead of
#     repo.continuum.io
try:
    del os.environ['CIO_TEST']
except KeyError:
    pass


class TestConfig(unittest.TestCase):

    # These tests are mostly to ensure API stability

    def __init__(self, *args, **kwargs):
        config.rc = config.load_condarc(config.rc_path)
        # Otherwise normalization tests will fail if the user is logged into
        # binstar.
        config.rc['add_binstar_token'] = False
        config.channel_alias = config.rc['channel_alias']
        super(TestConfig, self).__init__(*args, **kwargs)

    def test_globals(self):
        self.assertTrue(config.root_dir)
        self.assertTrue(config.pkgs_dirs)
        self.assertTrue(config.envs_dirs)
        self.assertTrue(config.default_prefix)
        self.assertTrue(config.platform)
        self.assertTrue(config.subdir)
        self.assertTrue(config.arch_name)
        self.assertTrue(config.bits in (32, 64))

    def test_pkgs_dir_from_envs_dir(self):
        root_dir = config.root_dir
        root_pkgs = join(root_dir, 'pkgs')
        for pi, po in [
            (join(root_dir, 'envs'), root_pkgs),
            ('/usr/local/foo/envs' if config.platform != 'win' else 'C:\envs',
                '/usr/local/foo/envs/.pkgs' if config.platform != 'win' else 'C:\envs\.pkgs'),
            ]:
            self.assertEqual(config.pkgs_dir_from_envs_dir(pi), po)

    def test_proxy_settings(self):
        self.assertEqual(config.get_proxy_servers(),
                         {'http': 'http://user:pass@corp.com:8080',
                          'https': 'https://user:pass@corp.com:8080'})

    def test_normalize_urls(self):
        current_platform = config.subdir
        assert config.DEFAULT_CHANNEL_ALIAS == 'https://conda.anaconda.org/'
        assert config.rc.get('channel_alias') == 'https://your.repo/'
        assert config.channel_alias == 'https://your.repo/'

        normurls = config.normalize_urls([
            'defaults', 'system', 'https://conda.anaconda.org/username',
            'file:///Users/username/repo', 'username'
            ], 'osx-64')
        assert normurls == [
             'http://repo.continuum.io/pkgs/free/osx-64/',
             'http://repo.continuum.io/pkgs/free/noarch/',
             'http://repo.continuum.io/pkgs/pro/osx-64/',
             'http://repo.continuum.io/pkgs/pro/noarch/',
             'https://your.repo/binstar_username/osx-64/',
             'https://your.repo/binstar_username/noarch/',
             'http://some.custom/channel/osx-64/',
             'http://some.custom/channel/noarch/',
             'http://repo.continuum.io/pkgs/free/osx-64/',
             'http://repo.continuum.io/pkgs/free/noarch/',
             'http://repo.continuum.io/pkgs/pro/osx-64/',
             'http://repo.continuum.io/pkgs/pro/noarch/',
             'https://conda.anaconda.org/username/osx-64/',
             'https://conda.anaconda.org/username/noarch/',
             'file:///Users/username/repo/osx-64/',
             'file:///Users/username/repo/noarch/',
             'https://your.repo/username/osx-64/',
             'https://your.repo/username/noarch/']
        priurls = config.prioritize_channels(normurls)
        assert dict(priurls) == {
             'file:///Users/username/repo/noarch/': ('file:///Users/username/repo', 5),
             'file:///Users/username/repo/osx-64/': ('file:///Users/username/repo', 5),
             'http://repo.continuum.io/pkgs/free/noarch/': ('defaults', 1),
             'http://repo.continuum.io/pkgs/free/osx-64/': ('defaults', 1),
             'http://repo.continuum.io/pkgs/pro/noarch/': ('defaults', 1),
             'http://repo.continuum.io/pkgs/pro/osx-64/': ('defaults', 1),
             'http://some.custom/channel/noarch/': ('http://some.custom/channel', 3),
             'http://some.custom/channel/osx-64/': ('http://some.custom/channel', 3),
             'https://conda.anaconda.org/username/noarch/': ('https://conda.anaconda.org/username', 4),
             'https://conda.anaconda.org/username/osx-64/': ('https://conda.anaconda.org/username', 4),
             'https://your.repo/binstar_username/noarch/': ('binstar_username', 2),
             'https://your.repo/binstar_username/osx-64/': ('binstar_username', 2),
             'https://your.repo/username/noarch/': ('username', 6),
             'https://your.repo/username/osx-64/': ('username', 6)}


@contextmanager
def make_temp_condarc(value=None):
    try:
        tempfile = mktemp()
        if value:
            with open(tempfile, 'w') as f:
                f.write(value)
        yield tempfile
    finally:
        if exists(tempfile):
            os.remove(tempfile)

def _read_test_condarc(rc):
    with open(rc) as f:
        return f.read()

# Tests for the conda config command
# FIXME This shoiuld be multiple individual tests
@pytest.mark.slow
def test_config_command_basics():

        # Test that creating the file adds the defaults channel
    with make_temp_condarc() as rc:
        stdout, stderr = run_conda_command('config', '--file', rc, '--add',
          'channels', 'test')
        assert stdout == stderr == ''
        assert _read_test_condarc(rc) == """\
channels:
  - test
  - defaults
"""
    with make_temp_condarc() as rc:
        # When defaults is explicitly given, it should not be added
        stdout, stderr = run_conda_command('config', '--file', rc, '--add',
            'channels', 'test', '--add', 'channels', 'defaults')
        assert stdout == stderr == ''
        assert _read_test_condarc(rc) == """\
channels:
  - defaults
  - test
"""
    # Duplicate keys should not be added twice
    with make_temp_condarc() as rc:
        stdout, stderr = run_conda_command('config', '--file', rc, '--add',
            'channels', 'test')
        assert stdout == stderr == ''
        stdout, stderr = run_conda_command('config', '--file', rc, '--add',
            'channels', 'test')
        assert stdout == ''
        assert stderr == "Skipping channels: test, item already exists"
        assert _read_test_condarc(rc) == """\
channels:
  - test
  - defaults
"""

    # Test creating a new file with --set
    with make_temp_condarc() as rc:
        stdout, stderr = run_conda_command('config', '--file', rc,
            '--set', 'always_yes', 'true')
        assert stdout == stderr == ''
        assert _read_test_condarc(rc) == """\
always_yes: true
"""


# FIXME Break into multiple tests
@pytest.mark.slow
def test_config_command_get():
    # Test --get
    condarc = """\
channels:
  - test
  - defaults

create_default_packages:
  - ipython
  - numpy

changeps1: false

always_yes: true

invalid_key: true

channel_alias: http://alpha.conda.anaconda.org
"""
    with make_temp_condarc(condarc) as rc:
        stdout, stderr = run_conda_command('config', '--file', rc, '--get')
        assert stdout == """\
--set always_yes True
--set changeps1 False
--set channel_alias http://alpha.conda.anaconda.org
--add channels 'defaults'
--add channels 'test'
--add create_default_packages 'numpy'
--add create_default_packages 'ipython'\
"""
        assert stderr == "unknown key invalid_key"

        stdout, stderr = run_conda_command('config', '--file', rc,
        '--get', 'channels')

        assert stdout == """\
--add channels 'defaults'
--add channels 'test'\
"""
        assert stderr == ""

        stdout, stderr = run_conda_command('config', '--file', rc,
        '--get', 'changeps1')

        assert stdout == """\
--set changeps1 False\
"""
        assert stderr == ""

        stdout, stderr = run_conda_command('config', '--file', rc,
            '--get', 'changeps1', 'channels')

        assert stdout == """\
--set changeps1 False
--add channels 'defaults'
--add channels 'test'\
"""
        assert stderr == ""

        stdout, stderr = run_conda_command('config', '--file', rc,
        '--get', 'allow_softlinks')

        assert stdout == ""
        assert stderr == ""

        stdout, stderr = run_conda_command('config', '--file', rc,
        '--get', 'track_features')

        assert stdout == ""
        assert stderr == ""

        stdout, stderr = run_conda_command('config', '--file', rc,
        '--get', 'invalid_key')

        assert stdout == ""
        assert "invalid choice: 'invalid_key'" in stderr

        stdout, stderr = run_conda_command('config', '--file', rc,
        '--get', 'not_valid_key')

        assert stdout == ""
        assert "invalid choice: 'not_valid_key'" in stderr


# FIXME Break into multiple tests
@pytest.mark.slow
def test_config_command_parser():
    # Now test the YAML "parser"
    # Channels is normal content.
    # create_default_packages has extra spaces in list items
    condarc = """\
channels:
  - test
  - defaults

create_default_packages :
  -  ipython
  -  numpy

changeps1: false

# Here is a comment
always_yes: yes
"""
    # First verify that this itself is valid YAML
    assert yaml.load(condarc, Loader=yaml.RoundTripLoader) == {'channels': ['test', 'defaults'],
        'create_default_packages': ['ipython', 'numpy'], 'changeps1':
        False, 'always_yes': 'yes'}

    with make_temp_condarc(condarc) as rc:
        stdout, stderr = run_conda_command('config', '--file', rc, '--get')

        assert stdout == """\
--set always_yes yes
--set changeps1 False
--add channels 'defaults'
--add channels 'test'
--add create_default_packages 'numpy'
--add create_default_packages 'ipython'\
"""

        stdout, stderr = run_conda_command('config', '--file', rc, '--add',
            'channels', 'mychannel')
        assert stdout == stderr == ''

        assert _read_test_condarc(rc) == """\
channels:
  - mychannel
  - test
  - defaults

create_default_packages:
  - ipython
  - numpy

changeps1: false

# Here is a comment
always_yes: 'yes'
"""

        stdout, stderr = run_conda_command('config', '--file', rc,
            '--set', 'changeps1', 'true')

        assert stdout == stderr == ''

        assert _read_test_condarc(rc) == """\
channels:
  - mychannel
  - test
  - defaults

create_default_packages:
  - ipython
  - numpy

changeps1: true

# Here is a comment
always_yes: 'yes'
"""

        # Test adding a new list key. We couldn't test this above because it
        # doesn't work yet with odd whitespace
    condarc = """\
channels:
  - test
  - defaults

always_yes: true
"""

    with make_temp_condarc(condarc) as rc:
        stdout, stderr = run_conda_command('config', '--file', rc, '--add',
            'disallow', 'perl')
        assert stdout == stderr == ''
        assert _read_test_condarc(rc) == condarc + """\
disallow:
  - perl
"""


# FIXME Break into multiple tests
@pytest.mark.slow
def test_config_command_remove_force():
    # Finally, test --remove, --remove-key
    with make_temp_condarc() as rc:
        run_conda_command('config', '--file', rc, '--add',
            'channels', 'test')
        run_conda_command('config', '--file', rc, '--set',
            'always_yes', 'true')
        stdout, stderr = run_conda_command('config', '--file', rc,
            '--remove', 'channels', 'test')
        assert stdout == stderr == ''
        assert yaml.load(_read_test_condarc(rc), Loader=yaml.RoundTripLoader) == {'channels': ['defaults'],
            'always_yes': True}

        stdout, stderr = run_conda_command('config', '--file', rc,
            '--remove', 'channels', 'test', '--force')
        assert stdout == ''
        assert stderr == "Error: 'test' is not in the 'channels' key of the config file"

        stdout, stderr = run_conda_command('config', '--file', rc,
            '--remove', 'disallow', 'python', '--force')
        assert stdout == ''
        assert stderr == "Error: key 'disallow' is not in the config file"

        stdout, stderr = run_conda_command('config', '--file', rc,
            '--remove-key', 'always_yes', '--force')
        assert stdout == stderr == ''
        assert yaml.load(_read_test_condarc(rc), Loader=yaml.RoundTripLoader) == {'channels': ['defaults']}

        stdout, stderr = run_conda_command('config', '--file', rc,
            '--remove-key', 'always_yes', '--force')

        assert stdout == ''
        assert stderr == "Error: key 'always_yes' is not in the config file"


# FIXME Break into multiple tests
@pytest.mark.slow
def test_config_command_bad_args():
    with make_temp_condarc() as rc:
        stdout, stderr = run_conda_command('config', '--file', rc, '--add',
            'notarealkey', 'test')
        assert stdout == ''

        assert not exists(rc)

        stdout, stderr = run_conda_command('config', '--file', rc, '--set',
            'notarealkey', 'true')
        assert stdout == ''

        assert not exists(rc)

def test_invalid_rc():
    # Some tests for unexpected input in the condarc, like keys that are the
    # wrong type
    condarc = """\
channels:
"""

    with make_temp_condarc(condarc) as rc:
        stdout, stderr = run_conda_command('config', '--file', rc,
                                           '--add', 'channels', 'test')
        assert stdout == ''
        assert stderr == """\
Error: Could not parse the yaml file. Use -f to use the
yaml parser (this will remove any structure or comments from the existing
.condarc file). Reason: key 'channels' should be a list, not NoneType."""
        assert _read_test_condarc(rc) == condarc


def test_config_set():
    # Test the config set command
    # Make sure it accepts only boolean values for boolean keys and any value for string keys

    with make_temp_condarc() as rc:
        stdout, stderr = run_conda_command('config', '--file', rc,
                                           '--set', 'always_yes', 'yes')

        assert stdout == ''
        assert stderr == 'Error: Key: always_yes; yes is not a YAML boolean.'

        stdout, stderr = run_conda_command('config', '--file', rc,
                                           '--set', 'always_yes', 'no')

        assert stdout == ''
        assert stderr == 'Error: Key: always_yes; no is not a YAML boolean.'

def test_set_rc_string():
    # Test setting string keys in .condarc

    # We specifically test ssl_verify since it can be either a boolean or a string
    with make_temp_condarc() as rc:
        stdout, stderr = run_conda_command('config', '--file', rc,
                                           '--set', 'ssl_verify', 'yes')
        assert stdout == ''
        assert stderr == ''

        verify = yaml.load(open(rc, 'r'), Loader=yaml.RoundTripLoader)['ssl_verify']
        assert verify == 'yes'

        stdout, stderr = run_conda_command('config', '--file', rc,
                                           '--set', 'ssl_verify', 'test_string.crt')
        assert stdout == ''
        assert stderr == ''

        verify = yaml.load(open(rc, 'r'), Loader=yaml.RoundTripLoader)['ssl_verify']
        assert verify == 'test_string.crt'
