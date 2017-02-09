# (c) 2012-2014 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.
import os
import pytest
import unittest
from conda.models.channel import Channel
from contextlib import contextmanager
from datetime import datetime
from os.path import join, dirname
from tempfile import mkstemp, NamedTemporaryFile

from conda import config
from conda.base.constants import DEFAULT_CHANNEL_ALIAS
from conda.base.context import reset_context, context
from conda.common.configuration import LoadError
from conda.common.yaml import yaml_load
from conda.gateways.disk.delete import rm_rf
from tests.helpers import run_conda_command

# use condarc from source tree to run these tests against

# # unset 'default_channels' so get_default_channels has predictable behavior
# try:
#     del config.sys_rc['default_channels']
# except KeyError:
#     pass

# unset CIO_TEST.  This is a Continuum-internal variable that draws packages from an internal server instead of
#     repo.continuum.io
try:
    del os.environ['CIO_TEST']
except KeyError:
    pass

# # Remove msys2 from defaults just for testing purposes
# if len(config.defaults_) > 2:
#     config.defaults_ = config.defaults_[:2]

# class BinstarTester(object):
#     def __init__(self, domain='https://mybinstar.com', token='01234abcde'):
#        self.domain = domain
#        self.token = token


class TestConfig(unittest.TestCase):

    # These tests are mostly to ensure API stability

    # def setUp(self):
    #     # Load the test condarc file
    #     self.rc, config.rc = config.rc, testrc
    #     config.load_condarc()
    #     config.binstar_client = BinstarTester()
    #     config.init_binstar()
    #
    # def tearDown(self):
    #     # Restore original condarc
    #     config.rc = self.rc
    #     config.load_condarc()

    def test_globals(self):
        self.assertTrue(config.root_dir)
        self.assertTrue(config.pkgs_dirs)
        self.assertTrue(config.envs_dirs)
        self.assertTrue(config.default_prefix)
        self.assertTrue(config.platform)
        self.assertTrue(config.subdir)
        self.assertTrue(config.arch_name)
        self.assertTrue(config.bits in (32, 64))

    # def test_proxy_settings(self):
    #     self.assertEqual(config.get_proxy_servers(),
    #                      {'http': 'http://user:pass@corp.com:8080',
    #                       'https': 'https://user:pass@corp.com:8080'})

    def test_normalize_urls(self):
        context = reset_context([join(dirname(__file__), 'condarc')])
        assert DEFAULT_CHANNEL_ALIAS == 'https://conda.anaconda.org'
        match_me = Channel('https://your.repo/')
        assert context.channel_alias == Channel('https://your.repo/')
        # assert binstar.channel_prefix(False) == 'https://your.repo/'
        # assert binstar.binstar_domain == 'https://mybinstar.com/'
        # assert binstar.binstar_domain_tok == 'https://mybinstar.com/t/01234abcde/'
        assert context.channels == ("binstar_username", "http://some.custom/channel", "defaults")
        channel_urls = [
            'defaults',
            'system',
            'https://conda.anaconda.org/username',
            'file:///Users/username/repo',
            'https://mybinstar.com/t/5768wxyz/test2',
            'https://mybinstar.com/test',
            'https://conda.anaconda.org/t/abcdefgh/username',
            'username'
        ]
        platform = 'osx-64'

    #     normurls = config.normalize_urls(channel_urls, platform)
    #     assert normurls == [
    #        # defaults
    #        'https://repo.continuum.io/pkgs/free/osx-64/',
    #        'https://repo.continuum.io/pkgs/free/noarch/',
    #        'https://repo.continuum.io/pkgs/pro/osx-64/',
    #        'https://repo.continuum.io/pkgs/pro/noarch/',
    #        # system (condarc)
    #        'https://your.repo/binstar_username/osx-64/',
    #        'https://your.repo/binstar_username/noarch/',
    #        'http://some.custom/channel/osx-64/',
    #        'http://some.custom/channel/noarch/',
    #        # defaults is repeated in condarc; that's OK
    #        'https://repo.continuum.io/pkgs/free/osx-64/',
    #        'https://repo.continuum.io/pkgs/free/noarch/',
    #        'https://repo.continuum.io/pkgs/pro/osx-64/',
    #        'https://repo.continuum.io/pkgs/pro/noarch/',
    #        # conda.anaconda.org is not our default binstar clinet
    #        'https://conda.anaconda.org/username/osx-64/',
    #        'https://conda.anaconda.org/username/noarch/',
    #        'file:///Users/username/repo/osx-64/',
    #        'file:///Users/username/repo/noarch/',
    #        # mybinstar.com is not channel_alias, but we still add tokens
    #        'https://mybinstar.com/t/5768wxyz/test2/osx-64/',
    #        'https://mybinstar.com/t/5768wxyz/test2/noarch/',
    #        # token already supplied, do not change/remove it
    #        'https://mybinstar.com/t/01234abcde/test/osx-64/',
    #        'https://mybinstar.com/t/01234abcde/test/noarch/',
    #        # we do not remove tokens from conda.anaconda.org
    #        'https://conda.anaconda.org/t/abcdefgh/username/osx-64/',
    #        'https://conda.anaconda.org/t/abcdefgh/username/noarch/',
    #        # short channel; add channel_alias
    #        'https://your.repo/username/osx-64/',
    #        'https://your.repo/username/noarch/']
    #
    #     priurls = config.prioritize_channels(normurls)
    #     assert dict(priurls) == {
    #        # defaults appears twice, keep higher priority
    #        'https://repo.continuum.io/pkgs/free/noarch/': ('defaults', 1),
    #        'https://repo.continuum.io/pkgs/free/osx-64/': ('defaults', 1),
    #        'https://repo.continuum.io/pkgs/pro/noarch/': ('defaults', 1),
    #        'https://repo.continuum.io/pkgs/pro/osx-64/': ('defaults', 1),
    #        'https://your.repo/binstar_username/noarch/': ('binstar_username', 2),
    #        'https://your.repo/binstar_username/osx-64/': ('binstar_username', 2),
    #        'http://some.custom/channel/noarch/': ('http://some.custom/channel', 3),
    #        'http://some.custom/channel/osx-64/': ('http://some.custom/channel', 3),
    #        'https://conda.anaconda.org/t/abcdefgh/username/noarch/': ('https://conda.anaconda.org/username', 4),
    #        'https://conda.anaconda.org/t/abcdefgh/username/osx-64/': ('https://conda.anaconda.org/username', 4),
    #        'file:///Users/username/repo/noarch/': ('file:///Users/username/repo', 5),
    #        'file:///Users/username/repo/osx-64/': ('file:///Users/username/repo', 5),
    #        # the tokenized version came first, but we still give it the same priority
    #        'https://conda.anaconda.org/username/noarch/': ('https://conda.anaconda.org/username', 4),
    #        'https://conda.anaconda.org/username/osx-64/': ('https://conda.anaconda.org/username', 4),
    #        'https://mybinstar.com/t/5768wxyz/test2/noarch/': ('https://mybinstar.com/test2', 6),
    #        'https://mybinstar.com/t/5768wxyz/test2/osx-64/': ('https://mybinstar.com/test2', 6),
    #        'https://mybinstar.com/t/01234abcde/test/noarch/': ('https://mybinstar.com/test', 7),
    #        'https://mybinstar.com/t/01234abcde/test/osx-64/': ('https://mybinstar.com/test', 7),
    #        'https://your.repo/username/noarch/': ('username', 8),
    #        'https://your.repo/username/osx-64/': ('username', 8)
    #     }
    #
    #     # Delete the channel alias so now the short channels point to binstar
    #     del config.rc['channel_alias']
    #     config.rc['offline'] = False
    #     config.load_condarc()
    #     config.binstar_client = BinstarTester()
    #     normurls = config.normalize_urls(channel_urls, platform)
    #     # all your.repo references should be changed to mybinstar.com
    #     assert normurls == [
    #        'https://repo.continuum.io/pkgs/free/osx-64/',
    #        'https://repo.continuum.io/pkgs/free/noarch/',
    #        'https://repo.continuum.io/pkgs/pro/osx-64/',
    #        'https://repo.continuum.io/pkgs/pro/noarch/',
    #        'https://mybinstar.com/t/01234abcde/binstar_username/osx-64/',
    #        'https://mybinstar.com/t/01234abcde/binstar_username/noarch/',
    #        'http://some.custom/channel/osx-64/',
    #        'http://some.custom/channel/noarch/',
    #        'https://repo.continuum.io/pkgs/free/osx-64/',
    #        'https://repo.continuum.io/pkgs/free/noarch/',
    #        'https://repo.continuum.io/pkgs/pro/osx-64/',
    #        'https://repo.continuum.io/pkgs/pro/noarch/',
    #        'https://conda.anaconda.org/username/osx-64/',
    #        'https://conda.anaconda.org/username/noarch/',
    #        'file:///Users/username/repo/osx-64/',
    #        'file:///Users/username/repo/noarch/',
    #        'https://mybinstar.com/t/5768wxyz/test2/osx-64/',
    #        'https://mybinstar.com/t/5768wxyz/test2/noarch/',
    #        'https://mybinstar.com/t/01234abcde/test/osx-64/',
    #        'https://mybinstar.com/t/01234abcde/test/noarch/',
    #        'https://conda.anaconda.org/t/abcdefgh/username/osx-64/',
    #        'https://conda.anaconda.org/t/abcdefgh/username/noarch/',
    #        'https://mybinstar.com/t/01234abcde/username/osx-64/',
    #        'https://mybinstar.com/t/01234abcde/username/noarch/'
    #     ]
    #
    #     # Delete the anaconda token
    #     config.load_condarc()
    #     config.binstar_client = BinstarTester(token=None)
    #     normurls = config.normalize_urls(channel_urls, platform)
    #     # tokens should not be added (but supplied tokens are kept)
    #     assert normurls == [
    #        'https://repo.continuum.io/pkgs/free/osx-64/',
    #        'https://repo.continuum.io/pkgs/free/noarch/',
    #        'https://repo.continuum.io/pkgs/pro/osx-64/',
    #        'https://repo.continuum.io/pkgs/pro/noarch/',
    #        'https://mybinstar.com/binstar_username/osx-64/',
    #        'https://mybinstar.com/binstar_username/noarch/',
    #        'http://some.custom/channel/osx-64/',
    #        'http://some.custom/channel/noarch/',
    #        'https://repo.continuum.io/pkgs/free/osx-64/',
    #        'https://repo.continuum.io/pkgs/free/noarch/',
    #        'https://repo.continuum.io/pkgs/pro/osx-64/',
    #        'https://repo.continuum.io/pkgs/pro/noarch/',
    #        'https://conda.anaconda.org/username/osx-64/',
    #        'https://conda.anaconda.org/username/noarch/',
    #        'file:///Users/username/repo/osx-64/',
    #        'file:///Users/username/repo/noarch/',
    #        'https://mybinstar.com/t/5768wxyz/test2/osx-64/',
    #        'https://mybinstar.com/t/5768wxyz/test2/noarch/',
    #        'https://mybinstar.com/test/osx-64/',
    #        'https://mybinstar.com/test/noarch/',
    #        'https://conda.anaconda.org/t/abcdefgh/username/osx-64/',
    #        'https://conda.anaconda.org/t/abcdefgh/username/noarch/',
    #        'https://mybinstar.com/username/osx-64/',
    #        'https://mybinstar.com/username/noarch/'
    #     ]
    #
    #     # Turn off add_anaconda_token
    #     config.rc['add_binstar_token'] = False
    #     config.load_condarc()
    #     config.binstar_client = BinstarTester()
    #     normurls2 = config.normalize_urls(channel_urls, platform)
    #     # tokens should not be added (but supplied tokens are kept)
    #     assert normurls == normurls2
    #
    #     # Disable binstar client altogether
    #     config.load_condarc()
    #     config.binstar_client = ()
    #     normurls = config.normalize_urls(channel_urls, platform)
    #     # should drop back to conda.anaconda.org
    #     assert normurls == [
    #       'https://repo.continuum.io/pkgs/free/osx-64/',
    #       'https://repo.continuum.io/pkgs/free/noarch/',
    #       'https://repo.continuum.io/pkgs/pro/osx-64/',
    #       'https://repo.continuum.io/pkgs/pro/noarch/',
    #       'https://conda.anaconda.org/binstar_username/osx-64/',
    #       'https://conda.anaconda.org/binstar_username/noarch/',
    #       'http://some.custom/channel/osx-64/',
    #       'http://some.custom/channel/noarch/',
    #       'https://repo.continuum.io/pkgs/free/osx-64/',
    #       'https://repo.continuum.io/pkgs/free/noarch/',
    #       'https://repo.continuum.io/pkgs/pro/osx-64/',
    #       'https://repo.continuum.io/pkgs/pro/noarch/',
    #       'https://conda.anaconda.org/username/osx-64/',
    #       'https://conda.anaconda.org/username/noarch/',
    #       'file:///Users/username/repo/osx-64/',
    #       'file:///Users/username/repo/noarch/',
    #       'https://mybinstar.com/t/5768wxyz/test2/osx-64/',
    #       'https://mybinstar.com/t/5768wxyz/test2/noarch/',
    #       'https://mybinstar.com/test/osx-64/',
    #       'https://mybinstar.com/test/noarch/',
    #       'https://conda.anaconda.org/t/abcdefgh/username/osx-64/',
    #       'https://conda.anaconda.org/t/abcdefgh/username/noarch/',
    #       'https://conda.anaconda.org/username/osx-64/',
    #       'https://conda.anaconda.org/username/noarch/'
    #     ]


@contextmanager
def make_temp_condarc(value=None):
    try:
        tempfile = NamedTemporaryFile(suffix='.yml', delete=False)
        tempfile.close()
        temp_path = tempfile.name
        if value:
            with open(temp_path, 'w') as f:
                f.write(value)
        reset_context([temp_path])
        yield temp_path
    finally:
        rm_rf(temp_path)


def _read_test_condarc(rc):
    with open(rc) as f:
        return f.read()


@pytest.mark.integration
def test_invalid_config():
    condarc="""\
fgddgh
channels:
  - test
"""
    try:
        with make_temp_condarc(condarc) as rc:
            rc_path = rc
            run_conda_command('config', '--file', rc, '--add',
                                           'channels', 'test')
    except LoadError as err:
        error1 = "Load Error: in "
        error2 = "on line 1, column 8. Invalid YAML"
        assert error1 in err.message
        assert error2 in err.message

# Tests for the conda config command
# FIXME This shoiuld be multiple individual tests
@pytest.mark.slow
@pytest.mark.integration
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
        print(_read_test_condarc(rc))
        print(_read_test_condarc(rc))
        print(_read_test_condarc(rc))

    with make_temp_condarc() as rc:
        # When defaults is explicitly given, it should not be added
        stdout, stderr = run_conda_command('config', '--file', rc, '--add',
                                           'channels', 'test', '--add', 'channels', 'defaults')
        assert stdout == ''
        assert stderr == "Warning: 'defaults' already in 'channels' list, moving to the top"
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
        assert stderr == "Warning: 'test' already in 'channels' list, moving to the top"
        assert _read_test_condarc(rc) == """\
channels:
  - test
  - defaults
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
        assert "CondaKeyError: Error with key 'channels': 'defaults' is not in the 'channels' " \
               "key of the config file" in stderr

    # Test creating a new file with --set
    with make_temp_condarc() as rc:
        stdout, stderr = run_conda_command('config', '--file', rc,
            '--set', 'always_yes', 'true')
        assert stdout == stderr == ''
        assert _read_test_condarc(rc) == """\
always_yes: true
"""


@pytest.mark.integration
def test_config_command_show():
    # test alphabetical yaml output
    with make_temp_condarc() as rc:
        stdout, stderr = run_conda_command('config', '--file', rc, '--show')
        output_keys = yaml_load(stdout).keys()

        assert stderr == ''
        assert sorted(output_keys) == [item for item in output_keys]


# FIXME Break into multiple tests
@pytest.mark.slow
@pytest.mark.integration
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
--add channels 'defaults'   # lowest priority
--add channels 'test'   # highest priority
--add create_default_packages 'numpy'
--add create_default_packages 'ipython'\
"""
        assert stderr == "unknown key invalid_key"

        stdout, stderr = run_conda_command('config', '--file', rc,
                                           '--get', 'channels')

        assert stdout == """\
--add channels 'defaults'   # lowest priority
--add channels 'test'   # highest priority\
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
--add channels 'defaults'   # lowest priority
--add channels 'test'   # highest priority\
"""
        assert stderr == ""

        stdout, stderr = run_conda_command('config', '--file', rc, '--get', 'allow_softlinks')

        assert stdout == ""
        assert stderr == ""

        stdout, stderr = run_conda_command('config', '--file', rc, '--get', 'always_softlink')

        assert stdout == ""
        assert stderr == ""

        stdout, stderr = run_conda_command('config', '--file', rc, '--get', 'track_features')

        assert stdout == ""
        assert stderr == ""

        stdout, stderr = run_conda_command('config', '--file', rc, '--get', 'invalid_key')

        assert stdout == ""
        assert "invalid choice: 'invalid_key'" in stderr

        stdout, stderr = run_conda_command('config', '--file', rc, '--get', 'not_valid_key')

        assert stdout == ""
        assert "invalid choice: 'not_valid_key'" in stderr


# FIXME Break into multiple tests
@pytest.mark.slow
@pytest.mark.integration
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
always_yes: true
"""
    # First verify that this itself is valid YAML
    assert yaml_load(condarc) == {'channels': ['test', 'defaults'],
                                  'create_default_packages': ['ipython', 'numpy'],
                                  'changeps1': False,
                                  'always_yes': True}

    with make_temp_condarc(condarc) as rc:
        stdout, stderr = run_conda_command('config', '--file', rc, '--get')
        print(stdout)
        assert stdout == """\
--set always_yes True
--set changeps1 False
--add channels 'defaults'   # lowest priority
--add channels 'test'   # highest priority
--add create_default_packages 'numpy'
--add create_default_packages 'ipython'\
"""
        with open(rc, 'r') as fh:
            print(fh.read())

        stdout, stderr = run_conda_command('config', '--file', rc, '--prepend',
                                           'channels', 'mychannel')
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
@pytest.mark.integration
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
        assert yaml_load(_read_test_condarc(rc)) == {'channels': ['defaults'],
                                                     'always_yes': True}

        stdout, stderr = run_conda_command('config', '--file', rc,
                                           '--remove', 'channels', 'test', '--force')
        assert stdout == ''
        assert "CondaKeyError: Error with key 'channels': 'test' is not in the 'channels' " \
               "key of the config file" in stderr

        stdout, stderr = run_conda_command('config', '--file', rc,
                                           '--remove', 'disallow', 'python', '--force')
        assert stdout == ''
        assert "CondaKeyError: Error with key 'disallow': key 'disallow' " \
               "is not in the config file" in stderr

        stdout, stderr = run_conda_command('config', '--file', rc,
                                           '--remove-key', 'always_yes', '--force')
        assert stdout == stderr == ''
        assert yaml_load(_read_test_condarc(rc)) == {'channels': ['defaults']}

        stdout, stderr = run_conda_command('config', '--file', rc,
                                           '--remove-key', 'always_yes', '--force')

        assert stdout == ''
        assert "CondaKeyError: Error with key 'always_yes': key 'always_yes' " \
               "is not in the config file" in stderr


# FIXME Break into multiple tests
@pytest.mark.slow
@pytest.mark.integration
def test_config_command_bad_args():
    with make_temp_condarc() as rc:
        stdout, stderr = run_conda_command('config', '--file', rc, '--add',
                                           'notarealkey', 'test')
        assert stdout == ''

        stdout, stderr = run_conda_command('config', '--file', rc, '--set',
                                           'notarealkey', 'true')
        assert stdout == ''


# def test_invalid_rc():
#     # Some tests for unexpected input in the condarc, like keys that are the
#     # wrong type
#     condarc = """\
# channels:
# """
#
#     with make_temp_condarc(condarc) as rc:
#         stdout, stderr = run_conda_command('config', '--file', rc,
#                                            '--add', 'channels', 'test')
#         assert stdout == ''
#         assert stderr == """\
# CondaError: Parse error: key 'channels' should be a list, not NoneType."""
#         assert _read_test_condarc(rc) == condarc


@pytest.mark.integration
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


@pytest.mark.integration
def test_set_rc_string():
    # Test setting string keys in .condarc

    # We specifically test ssl_verify since it can be either a boolean or a string
    with make_temp_condarc() as rc:
        assert context.ssl_verify is True
        stdout, stderr = run_conda_command('config', '--file', rc,
                                           '--set', 'ssl_verify', 'no')
        assert stdout == ''
        assert stderr == ''

        reset_context([rc])
        assert context.ssl_verify is False

        with NamedTemporaryFile() as tf:
            stdout, stderr = run_conda_command('config', '--file', rc,
                                               '--set', 'ssl_verify', tf.name)
            assert stdout == ''
            assert stderr == ''

            reset_context([rc])
            assert context.ssl_verify == tf.name
