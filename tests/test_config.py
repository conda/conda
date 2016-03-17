# (c) 2012-2014 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.
import os
from os.path import dirname, join, exists
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

        for channel in config.normalize_urls(['defaults', 'system',
            'https://anaconda.org/username', 'file:///Users/username/repo',
            'username']):
            assert (channel.endswith('/%s/' % current_platform) or
                    channel.endswith('/noarch/'))
        self.assertEqual(config.normalize_urls([
            'defaults', 'system', 'https://conda.anaconda.org/username',
            'file:///Users/username/repo', 'username'
            ], 'osx-64'),
            [
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
                'https://your.repo/username/noarch/',
                ])

test_condarc = os.path.join(os.path.dirname(__file__), 'test_condarc')
def _read_test_condarc():
    with open(test_condarc) as f:
        return f.read()

# Tests for the conda config command
# FIXME This shoiuld be multiple individual tests
@pytest.mark.slow
def test_config_command_basics():

    try:
        # Test that creating the file adds the defaults channel
        assert not os.path.exists('test_condarc')
        stdout, stderr = run_conda_command('config', '--file', test_condarc, '--add',
            'channels', 'test')
        assert stdout == stderr == ''
        assert _read_test_condarc() == """\
channels:
  - test
  - defaults
"""
        os.unlink(test_condarc)

        # When defaults is explicitly given, it should not be added
        stdout, stderr = run_conda_command('config', '--file', test_condarc, '--add',
    'channels', 'test', '--add', 'channels', 'defaults')
        assert stdout == stderr == ''
        assert _read_test_condarc() == """\
channels:
  - defaults
  - test
"""
        os.unlink(test_condarc)

        # Duplicate keys should not be added twice
        stdout, stderr = run_conda_command('config', '--file', test_condarc, '--add',
        'channels', 'test')
        assert stdout == stderr == ''
        stdout, stderr = run_conda_command('config', '--file', test_condarc, '--add',
        'channels', 'test')
        assert stdout == ''
        assert stderr == "Skipping channels: test, item already exists"
        assert _read_test_condarc() == """\
channels:
  - test
  - defaults
"""
        os.unlink(test_condarc)

        # Test creating a new file with --set
        stdout, stderr = run_conda_command('config', '--file', test_condarc,
        '--set', 'always_yes', 'true')
        assert stdout == stderr == ''
        assert _read_test_condarc() == """\
always_yes: true
"""
        os.unlink(test_condarc)

    finally:
        try:
            pass
            os.unlink(test_condarc)
        except OSError:
            pass


# FIXME Break into multiple tests
@pytest.mark.slow
def test_config_command_get():
    try:
        # Test --get
        with open(test_condarc, 'w') as f:
            f.write("""\
channels:
  - test
  - defaults

create_default_packages:
  - ipython
  - numpy

changeps1: no

always_yes: true

invalid_key: yes

channel_alias: http://alpha.conda.anaconda.org
""")

        stdout, stderr = run_conda_command('config', '--file', test_condarc, '--get')
        assert stdout == """\
--set always_yes True
--set changeps1 no
--set channel_alias http://alpha.conda.anaconda.org
--add channels 'defaults'
--add channels 'test'
--add create_default_packages 'numpy'
--add create_default_packages 'ipython'\
"""
        assert stderr == "unknown key invalid_key"

        stdout, stderr = run_conda_command('config', '--file', test_condarc,
        '--get', 'channels')

        assert stdout == """\
--add channels 'defaults'
--add channels 'test'\
"""
        assert stderr == ""

        stdout, stderr = run_conda_command('config', '--file', test_condarc,
        '--get', 'changeps1')

        assert stdout == """\
--set changeps1 no\
"""
        assert stderr == ""

        stdout, stderr = run_conda_command('config', '--file', test_condarc,
            '--get', 'changeps1', 'channels')

        assert stdout == """\
--set changeps1 no
--add channels 'defaults'
--add channels 'test'\
"""
        assert stderr == ""

        stdout, stderr = run_conda_command('config', '--file', test_condarc,
        '--get', 'allow_softlinks')

        assert stdout == ""
        assert stderr == ""

        stdout, stderr = run_conda_command('config', '--file', test_condarc,
        '--get', 'track_features')

        assert stdout == ""
        assert stderr == ""

        stdout, stderr = run_conda_command('config', '--file', test_condarc,
        '--get', 'invalid_key')

        assert stdout == ""
        assert "invalid choice: 'invalid_key'" in stderr

        stdout, stderr = run_conda_command('config', '--file', test_condarc,
        '--get', 'not_valid_key')

        assert stdout == ""
        assert "invalid choice: 'not_valid_key'" in stderr

        os.unlink(test_condarc)


    finally:
        try:
            pass
            os.unlink(test_condarc)
        except OSError:
            pass


# FIXME Break into multiple tests
@pytest.mark.slow
def test_config_command_parser():
    try:
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

        with open(test_condarc, 'w') as f:
            f.write(condarc)

        stdout, stderr = run_conda_command('config', '--file', test_condarc, '--get')

        assert stdout == """\
--set always_yes yes
--set changeps1 False
--add channels 'defaults'
--add channels 'test'
--add create_default_packages 'numpy'
--add create_default_packages 'ipython'\
"""

        stdout, stderr = run_conda_command('config', '--file', test_condarc, '--add',
            'channels', 'mychannel')
        assert stdout == stderr == ''

        assert _read_test_condarc() == """\
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

        stdout, stderr = run_conda_command('config', '--file', test_condarc,
            '--set', 'changeps1', 'true')

        assert stdout == stderr == ''

        assert _read_test_condarc() == """\
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

        os.unlink(test_condarc)

        # Test adding a new list key. We couldn't test this above because it
        # doesn't work yet with odd whitespace
        condarc = """\
channels:
  - test
  - defaults

always_yes: true
"""

        with open(test_condarc, 'w') as f:
            f.write(condarc)

        stdout, stderr = run_conda_command('config', '--file', test_condarc, '--add',
            'disallow', 'perl')
        assert stdout == stderr == ''
        assert _read_test_condarc() == condarc + """\
disallow:
  - perl
"""
        os.unlink(test_condarc)


    finally:
        try:
            pass
            os.unlink(test_condarc)
        except OSError:
            pass


# FIXME Break into multiple tests
@pytest.mark.slow
def test_config_command_remove_force():
    try:
        # Finally, test --remove, --remove-key
        run_conda_command('config', '--file', test_condarc, '--add',
            'channels', 'test')
        run_conda_command('config', '--file', test_condarc, '--set',
            'always_yes', 'true')
        stdout, stderr = run_conda_command('config', '--file', test_condarc,
            '--remove', 'channels', 'test')
        assert stdout == stderr == ''
        assert yaml.load(_read_test_condarc(), Loader=yaml.RoundTripLoader) == {'channels': ['defaults'],
            'always_yes': True}

        stdout, stderr = run_conda_command('config', '--file', test_condarc,
            '--remove', 'channels', 'test', '--force')
        assert stdout == ''
        assert stderr == "Error: 'test' is not in the 'channels' key of the config file"

        stdout, stderr = run_conda_command('config', '--file', test_condarc,
            '--remove', 'disallow', 'python', '--force')
        assert stdout == ''
        assert stderr == "Error: key 'disallow' is not in the config file"

        stdout, stderr = run_conda_command('config', '--file', test_condarc,
            '--remove-key', 'always_yes', '--force')
        assert stdout == stderr == ''
        assert yaml.load(_read_test_condarc(), Loader=yaml.RoundTripLoader) == {'channels': ['defaults']}

        stdout, stderr = run_conda_command('config', '--file', test_condarc,
            '--remove-key', 'always_yes', '--force')

        assert stdout == ''
        assert stderr == "Error: key 'always_yes' is not in the config file"
        os.unlink(test_condarc)

    finally:
        try:
            pass
            os.unlink(test_condarc)
        except OSError:
            pass


# FIXME Break into multiple tests
@pytest.mark.slow
def test_config_command_bad_args():
    try:
        stdout, stderr = run_conda_command('config', '--file', test_condarc, '--add',
            'notarealkey', 'test')
        assert stdout == ''

        assert not exists(test_condarc)

        stdout, stderr = run_conda_command('config', '--file', test_condarc, '--set',
            'notarealkey', 'yes')
        assert stdout == ''

        assert not exists(test_condarc)

    finally:
        try:
            pass
            os.unlink(test_condarc)
        except OSError:
            pass

def test_invalid_rc():
    # Some tests for unexpected input in the condarc, like keys that are the
    # wrong type
    try:
        condarc = """\
channels:
"""

        with open(test_condarc, 'w') as f:
            f.write(condarc)

        stdout, stderr = run_conda_command('config', '--file', test_condarc,
            '--add', 'channels', 'test')
        assert stdout == ''
        assert stderr == """\
Error: Could not parse the yaml file. Use -f to use the
yaml parser (this will remove any structure or comments from the existing
.condarc file). Reason: key 'channels' should be a list, not NoneType."""
        assert _read_test_condarc() == condarc

        os.unlink(test_condarc)
    finally:
        try:
            pass
            os.unlink(test_condarc)
        except OSError:
            pass

def test_config_set():
    # Test the config set command
    # Make sure it accepts only boolean values for boolean keys and any value for string keys

    try:
        stdout, stderr = run_conda_command('config', '--file', test_condarc,
                                           '--set', 'always_yes', 'yep')

        assert stdout == ''
        assert stderr == 'Error: Key: always_yes; yep is not a YAML boolean.'

    finally:
        try:
            os.unlink(test_condarc)
        except OSError:
            pass

def test_set_rc_string():
    # Test setting string keys in .condarc

    # We specifically test ssl_verify since it can be either a boolean or a string
    try:
        stdout, stderr = run_conda_command('config', '--file', test_condarc,
                                           '--set', 'ssl_verify', 'yes')
        assert stdout == ''
        assert stderr == ''

        verify = yaml.load(open(test_condarc, 'r'), Loader=yaml.RoundTripLoader)['ssl_verify']
        assert verify == 'yes'

        stdout, stderr = run_conda_command('config', '--file', test_condarc,
                                           '--set', 'ssl_verify', 'test_string.crt')
        assert stdout == ''
        assert stderr == ''

        verify = yaml.load(open(test_condarc, 'r'), Loader=yaml.RoundTripLoader)['ssl_verify']
        assert verify == 'test_string.crt'


        os.unlink(test_condarc)
    finally:
        try:
            os.unlink(test_condarc)
        except OSError:
            pass
