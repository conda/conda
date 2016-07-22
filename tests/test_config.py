# (c) 2012-2014 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.
import os
from datetime import datetime
from os.path import dirname, join, exists
from contextlib import contextmanager
from tempfile import mktemp
import unittest

import pytest

import conda.config as config
from conda.install import on_win
from conda.common.yaml import get_yaml

from tests.helpers import run_conda_command

yaml = get_yaml()
testrc = config.load_condarc_(join(dirname(__file__), 'condarc'))

# use condarc from source tree to run these tests against

# unset 'default_channels' so get_default_channels has predictable behavior
try:
    del config.sys_rc['default_channels']
except KeyError:
    pass

# unset CIO_TEST.  This is a Continuum-internal variable that draws packages from an internal server instead of
#     repo.continuum.io
try:
    del os.environ['CIO_TEST']
except KeyError:
    pass

# Remove msys2 from defaults just for testing purposes
if len(config.defaults_) > 2:
    config.defaults_ = config.defaults_[:2]

class BinstarTester(object):
    def __init__(self, domain='https://mybinstar.com', token='01234abcde'):
       self.domain = domain
       self.token = token


class TestConfig(unittest.TestCase):

    # These tests are mostly to ensure API stability

    def setUp(self):
        # Load the test condarc file
        self.rc, config.rc = config.rc, testrc
        config.load_condarc()
        config.binstar_client = BinstarTester()
        config.init_binstar()

    def tearDown(self):
        # Restore original condarc
        config.rc = self.rc
        config.load_condarc()

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

    @pytest.mark.xfail(datetime.now() < datetime(2016, 8, 1),
                       reason="refactor to work with Channel entity")
    def test_normalize_urls(self):
        current_platform = config.subdir
        assert config.DEFAULT_CHANNEL_ALIAS == 'https://conda.anaconda.org/'
        assert config.rc.get('channel_alias') == 'https://your.repo/'
        assert config.channel_prefix(False) == 'https://your.repo/'
        assert config.binstar_domain == 'https://mybinstar.com/'
        assert config.binstar_domain_tok == 'https://mybinstar.com/t/01234abcde/'
        assert config.get_rc_urls() == ["binstar_username", "http://some.custom/channel", "defaults"]
        channel_urls = [
            'defaults', 'system',
            'https://conda.anaconda.org/username',
            'file:///Users/username/repo', 
            'https://mybinstar.com/t/5768wxyz/test2', 
            'https://mybinstar.com/test', 
            'https://conda.anaconda.org/t/abcdefgh/username', 
            'username'
        ]
        platform = 'osx-64'

        normurls = config.normalize_urls(channel_urls, platform)
        assert normurls == [
           # defaults
           'https://repo.continuum.io/pkgs/free/osx-64/',
           'https://repo.continuum.io/pkgs/free/noarch/',
           'https://repo.continuum.io/pkgs/pro/osx-64/',
           'https://repo.continuum.io/pkgs/pro/noarch/',
           # system (condarc)
           'https://your.repo/binstar_username/osx-64/',
           'https://your.repo/binstar_username/noarch/',
           'http://some.custom/channel/osx-64/',
           'http://some.custom/channel/noarch/',
           # defaults is repeated in condarc; that's OK
           'https://repo.continuum.io/pkgs/free/osx-64/',
           'https://repo.continuum.io/pkgs/free/noarch/',
           'https://repo.continuum.io/pkgs/pro/osx-64/',
           'https://repo.continuum.io/pkgs/pro/noarch/',
           # conda.anaconda.org is not our default binstar clinet
           'https://conda.anaconda.org/username/osx-64/',
           'https://conda.anaconda.org/username/noarch/',
           'file:///Users/username/repo/osx-64/',
           'file:///Users/username/repo/noarch/',
           # mybinstar.com is not channel_alias, but we still add tokens
           'https://mybinstar.com/t/5768wxyz/test2/osx-64/',
           'https://mybinstar.com/t/5768wxyz/test2/noarch/',
           # token already supplied, do not change/remove it
           'https://mybinstar.com/t/01234abcde/test/osx-64/',
           'https://mybinstar.com/t/01234abcde/test/noarch/',
           # we do not remove tokens from conda.anaconda.org
           'https://conda.anaconda.org/t/abcdefgh/username/osx-64/',
           'https://conda.anaconda.org/t/abcdefgh/username/noarch/',
           # short channel; add channel_alias
           'https://your.repo/username/osx-64/',
           'https://your.repo/username/noarch/']

        priurls = config.prioritize_channels(normurls)
        assert dict(priurls) == {
           # defaults appears twice, keep higher priority
           'https://repo.continuum.io/pkgs/free/noarch/': ('defaults', 1),
           'https://repo.continuum.io/pkgs/free/osx-64/': ('defaults', 1),
           'https://repo.continuum.io/pkgs/pro/noarch/': ('defaults', 1),
           'https://repo.continuum.io/pkgs/pro/osx-64/': ('defaults', 1),
           'https://your.repo/binstar_username/noarch/': ('binstar_username', 2),
           'https://your.repo/binstar_username/osx-64/': ('binstar_username', 2),
           'http://some.custom/channel/noarch/': ('http://some.custom/channel', 3),
           'http://some.custom/channel/osx-64/': ('http://some.custom/channel', 3),
           'https://conda.anaconda.org/t/abcdefgh/username/noarch/': ('https://conda.anaconda.org/username', 4),
           'https://conda.anaconda.org/t/abcdefgh/username/osx-64/': ('https://conda.anaconda.org/username', 4),
           'file:///Users/username/repo/noarch/': ('file:///Users/username/repo', 5),
           'file:///Users/username/repo/osx-64/': ('file:///Users/username/repo', 5),
           # the tokenized version came first, but we still give it the same priority
           'https://conda.anaconda.org/username/noarch/': ('https://conda.anaconda.org/username', 4),
           'https://conda.anaconda.org/username/osx-64/': ('https://conda.anaconda.org/username', 4),
           'https://mybinstar.com/t/5768wxyz/test2/noarch/': ('https://mybinstar.com/test2', 6),
           'https://mybinstar.com/t/5768wxyz/test2/osx-64/': ('https://mybinstar.com/test2', 6),
           'https://mybinstar.com/t/01234abcde/test/noarch/': ('https://mybinstar.com/test', 7),
           'https://mybinstar.com/t/01234abcde/test/osx-64/': ('https://mybinstar.com/test', 7),
           'https://your.repo/username/noarch/': ('username', 8),
           'https://your.repo/username/osx-64/': ('username', 8)
        }

        # Delete the channel alias so now the short channels point to binstar
        del config.rc['channel_alias']
        config.rc['offline'] = False
        config.load_condarc()
        config.binstar_client = BinstarTester()
        normurls = config.normalize_urls(channel_urls, platform)
        # all your.repo references should be changed to mybinstar.com
        assert normurls == [
           'https://repo.continuum.io/pkgs/free/osx-64/',
           'https://repo.continuum.io/pkgs/free/noarch/',
           'https://repo.continuum.io/pkgs/pro/osx-64/',
           'https://repo.continuum.io/pkgs/pro/noarch/',
           'https://mybinstar.com/t/01234abcde/binstar_username/osx-64/',
           'https://mybinstar.com/t/01234abcde/binstar_username/noarch/',
           'http://some.custom/channel/osx-64/',
           'http://some.custom/channel/noarch/',
           'https://repo.continuum.io/pkgs/free/osx-64/',
           'https://repo.continuum.io/pkgs/free/noarch/',
           'https://repo.continuum.io/pkgs/pro/osx-64/',
           'https://repo.continuum.io/pkgs/pro/noarch/',
           'https://conda.anaconda.org/username/osx-64/',
           'https://conda.anaconda.org/username/noarch/',
           'file:///Users/username/repo/osx-64/',
           'file:///Users/username/repo/noarch/',
           'https://mybinstar.com/t/5768wxyz/test2/osx-64/',
           'https://mybinstar.com/t/5768wxyz/test2/noarch/',
           'https://mybinstar.com/t/01234abcde/test/osx-64/',
           'https://mybinstar.com/t/01234abcde/test/noarch/',
           'https://conda.anaconda.org/t/abcdefgh/username/osx-64/',
           'https://conda.anaconda.org/t/abcdefgh/username/noarch/',
           'https://mybinstar.com/t/01234abcde/username/osx-64/',
           'https://mybinstar.com/t/01234abcde/username/noarch/'
        ]

        # Delete the anaconda token
        config.load_condarc()
        config.binstar_client = BinstarTester(token=None)
        normurls = config.normalize_urls(channel_urls, platform)
        # tokens should not be added (but supplied tokens are kept)
        assert normurls == [
           'https://repo.continuum.io/pkgs/free/osx-64/',
           'https://repo.continuum.io/pkgs/free/noarch/',
           'https://repo.continuum.io/pkgs/pro/osx-64/',
           'https://repo.continuum.io/pkgs/pro/noarch/',
           'https://mybinstar.com/binstar_username/osx-64/',
           'https://mybinstar.com/binstar_username/noarch/',
           'http://some.custom/channel/osx-64/',
           'http://some.custom/channel/noarch/',
           'https://repo.continuum.io/pkgs/free/osx-64/',
           'https://repo.continuum.io/pkgs/free/noarch/',
           'https://repo.continuum.io/pkgs/pro/osx-64/',
           'https://repo.continuum.io/pkgs/pro/noarch/',
           'https://conda.anaconda.org/username/osx-64/',
           'https://conda.anaconda.org/username/noarch/',
           'file:///Users/username/repo/osx-64/',
           'file:///Users/username/repo/noarch/',
           'https://mybinstar.com/t/5768wxyz/test2/osx-64/',
           'https://mybinstar.com/t/5768wxyz/test2/noarch/',
           'https://mybinstar.com/test/osx-64/',
           'https://mybinstar.com/test/noarch/',
           'https://conda.anaconda.org/t/abcdefgh/username/osx-64/',
           'https://conda.anaconda.org/t/abcdefgh/username/noarch/',
           'https://mybinstar.com/username/osx-64/',
           'https://mybinstar.com/username/noarch/'
        ]

        # Turn off add_anaconda_token
        config.rc['add_binstar_token'] = False
        config.load_condarc()
        config.binstar_client = BinstarTester()
        normurls2 = config.normalize_urls(channel_urls, platform)
        # tokens should not be added (but supplied tokens are kept)
        assert normurls == normurls2

        # Disable binstar client altogether
        config.load_condarc()
        config.binstar_client = ()
        normurls = config.normalize_urls(channel_urls, platform)
        # should drop back to conda.anaconda.org
        assert normurls == [
          'https://repo.continuum.io/pkgs/free/osx-64/',
          'https://repo.continuum.io/pkgs/free/noarch/',
          'https://repo.continuum.io/pkgs/pro/osx-64/',
          'https://repo.continuum.io/pkgs/pro/noarch/',
          'https://conda.anaconda.org/binstar_username/osx-64/',
          'https://conda.anaconda.org/binstar_username/noarch/',
          'http://some.custom/channel/osx-64/',
          'http://some.custom/channel/noarch/',
          'https://repo.continuum.io/pkgs/free/osx-64/',
          'https://repo.continuum.io/pkgs/free/noarch/',
          'https://repo.continuum.io/pkgs/pro/osx-64/',
          'https://repo.continuum.io/pkgs/pro/noarch/',
          'https://conda.anaconda.org/username/osx-64/',
          'https://conda.anaconda.org/username/noarch/',
          'file:///Users/username/repo/osx-64/',
          'file:///Users/username/repo/noarch/',
          'https://mybinstar.com/t/5768wxyz/test2/osx-64/',
          'https://mybinstar.com/t/5768wxyz/test2/noarch/',
          'https://mybinstar.com/test/osx-64/',
          'https://mybinstar.com/test/noarch/',
          'https://conda.anaconda.org/t/abcdefgh/username/osx-64/',
          'https://conda.anaconda.org/t/abcdefgh/username/noarch/',
          'https://conda.anaconda.org/username/osx-64/',
          'https://conda.anaconda.org/username/noarch/'
        ]

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
  - defaults
  - test
"""
    with make_temp_condarc() as rc:
        # When defaults is explicitly given, it should not be added
        stdout, stderr = run_conda_command('config', '--file', rc, '--add',
            'channels', 'test', '--add', 'channels', 'defaults')
        assert stdout == ''
        assert stderr == "Warning: 'defaults' already in 'channels' list, moving to the bottom"
        assert _read_test_condarc(rc) == """\
channels:
  - test
  - defaults
"""
    # Duplicate keys should not be added twice
    with make_temp_condarc() as rc:
        stdout, stderr = run_conda_command('config', '--file', rc, '--add',
            'channels', 'test')
        assert stdout == stderr == ''
        stdout, stderr = run_conda_command('config', '--file', rc, '--add',
            'channels', 'test')
        assert stdout == ''
        assert stderr == "Warning: 'test' already in 'channels' list, moving to the bottom"
        assert _read_test_condarc(rc) == """\
channels:
  - defaults
  - test
"""

    # Test append
    with make_temp_condarc() as rc:
        stdout, stderr = run_conda_command('config', '--file', rc, '--add',
            'channels', 'test')
        assert stdout == stderr == ''
        stdout, stderr = run_conda_command('config', '--file', rc, '--append',
            'channels', 'test')
        assert stdout == ''
        assert stderr == "Warning: 'test' already in 'channels' list, moving to the bottom"
        assert _read_test_condarc(rc) == """\
channels:
  - defaults
  - test
"""

    # Test duoble remove of defaults
    with make_temp_condarc() as rc:
        stdout, stderr = run_conda_command('config', '--file', rc, '--remove',
            'channels', 'defaults')
        assert stdout == stderr == ''
        stdout, stderr = run_conda_command('config', '--file', rc, '--remove',
            'channels', 'defaults')
        assert stdout == ''
        assert stderr == "Key error: 'defaults' is not in the 'channels' key of the config file"

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
--add channels 'test'   # lowest priority
--add channels 'defaults'   # highest priority
--add create_default_packages 'ipython'
--add create_default_packages 'numpy'\
"""
        assert stderr == "unknown key invalid_key"

        stdout, stderr = run_conda_command('config', '--file', rc,
        '--get', 'channels')

        assert stdout == """\
--add channels 'test'   # lowest priority
--add channels 'defaults'   # highest priority\
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
--add channels 'test'   # lowest priority
--add channels 'defaults'   # highest priority\
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
        print(stdout)
        assert stdout == """\
--set always_yes True
--set changeps1 False
--add channels 'test'   # lowest priority
--add channels 'defaults'   # highest priority
--add create_default_packages 'ipython'
--add create_default_packages 'numpy'\
"""
        print(">>>>")
        with open(rc, 'r') as fh:
            print(fh.read())



        stdout, stderr = run_conda_command('config', '--file', rc, '--prepend', 'channels', 'mychannel')
        assert stdout == stderr == ''

        with open(rc, 'r') as fh:
            print(fh.read())

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
always_yes: true
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
always_yes: true
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
        assert stderr == "Key error: 'test' is not in the 'channels' key of the config file"

        stdout, stderr = run_conda_command('config', '--file', rc,
            '--remove', 'disallow', 'python', '--force')
        assert stdout == ''
        assert stderr == "Key error: key 'disallow' is not in the config file"

        stdout, stderr = run_conda_command('config', '--file', rc,
            '--remove-key', 'always_yes', '--force')
        assert stdout == stderr == ''
        assert yaml.load(_read_test_condarc(rc), Loader=yaml.RoundTripLoader) == {'channels': ['defaults']}

        stdout, stderr = run_conda_command('config', '--file', rc,
            '--remove-key', 'always_yes', '--force')

        assert stdout == ''
        assert stderr == "Key error: key 'always_yes' is not in the config file"


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
Parse error: Error: Could not parse the yaml file. Use -f to use the
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
        assert stderr == ''

        stdout, stderr = run_conda_command('config', '--file', rc,
                                           '--set', 'always_yes', 'no')

        assert stdout == ''
        assert stderr == ''

def test_set_rc_string():
    # Test setting string keys in .condarc

    # We specifically test ssl_verify since it can be either a boolean or a string
    with make_temp_condarc() as rc:
        stdout, stderr = run_conda_command('config', '--file', rc,
                                           '--set', 'ssl_verify', 'yes')
        assert stdout == ''
        assert stderr == ''

        verify = yaml.load(open(rc, 'r'), Loader=yaml.RoundTripLoader)['ssl_verify']
        assert verify is True

        stdout, stderr = run_conda_command('config', '--file', rc,
                                           '--set', 'ssl_verify', 'test_string.crt')
        assert stdout == ''
        assert stderr == ''

        verify = yaml.load(open(rc, 'r'), Loader=yaml.RoundTripLoader)['ssl_verify']
        assert verify == 'test_string.crt'
