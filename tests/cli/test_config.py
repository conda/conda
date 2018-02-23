# (c) 2012-2014 Continuum Analytics, Inc. / http://continuum.io
# All Rights Reserved
#
# conda is distributed under the terms of the BSD 3-clause license.
# Consult LICENSE.txt or http://opensource.org/licenses/BSD-3-Clause.
from contextlib import contextmanager
from tempfile import NamedTemporaryFile

from conda.base.context import context, reset_context
from conda.cli.python_api import Commands, run_command
from conda.common.configuration import LoadError
from conda.common.serialize import yaml_load
from conda.gateways.disk.delete import rm_rf


# use condarc from source tree to run these tests against

# # unset 'default_channels' so get_default_channels has predictable behavior
# try:
#     del config.sys_rc['default_channels']
# except KeyError:
#     pass

# unset CIO_TEST.  This is a Continuum-internal variable that draws packages from an internal server instead of
#     repo.anaconda.com

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


def test_invalid_config():
    condarc="""\
fgddgh
channels:
  - test
"""
    try:
        with make_temp_condarc(condarc) as rc:
            rc_path = rc
            run_command(Commands.CONFIG, '--file', rc, '--add', 'channels', 'test')
    except LoadError as err:
        error1 = "Load Error: in "
        error2 = "on line 1, column 8. Invalid YAML"
        assert error1 in err.message
        assert error2 in err.message

# Tests for the conda config command
# FIXME This shoiuld be multiple individual tests
def test_config_command_basics():

        # Test that creating the file adds the defaults channel
    with make_temp_condarc() as rc:
        stdout, stderr, return_code = run_command(Commands.CONFIG, '--file', rc, '--add',
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
        stdout, stderr, return_code = run_command(Commands.CONFIG, '--file', rc, '--add',
                                                  'channels', 'test', '--add', 'channels',
                                                  'defaults', use_exception_handler=True)
        assert stdout == ''
        assert stderr.strip() == "Warning: 'defaults' already in 'channels' list, moving to the top"
        assert _read_test_condarc(rc) == """\
channels:
  - defaults
  - test
"""
    # Duplicate keys should not be added twice
    with make_temp_condarc() as rc:
        stdout, stderr, return_code = run_command(Commands.CONFIG, '--file', rc, '--add',
                                                  'channels', 'test')
        assert stdout == stderr == ''
        stdout, stderr, return_code = run_command(Commands.CONFIG, '--file', rc, '--add',
                                                  'channels', 'test', use_exception_handler=True)
        assert stdout == ''
        assert stderr.strip() == "Warning: 'test' already in 'channels' list, moving to the top"
        assert _read_test_condarc(rc) == """\
channels:
  - test
  - defaults
"""

    # Test append
    with make_temp_condarc() as rc:
        stdout, stderr, return_code = run_command(Commands.CONFIG, '--file', rc, '--add',
                                                  'channels', 'test')
        assert stdout == stderr == ''
        stdout, stderr, return_code = run_command(Commands.CONFIG, '--file', rc, '--append',
                                                  'channels', 'test', use_exception_handler=True)
        assert stdout == ''
        assert stderr.strip() == "Warning: 'test' already in 'channels' list, moving to the bottom"
        assert _read_test_condarc(rc) == """\
channels:
  - defaults
  - test
"""

    # Test duoble remove of defaults
    with make_temp_condarc() as rc:
        stdout, stderr, return_code = run_command(Commands.CONFIG, '--file', rc, '--remove',
                                                  'channels', 'defaults')
        assert stdout == stderr == ''
        stdout, stderr, return_code = run_command(Commands.CONFIG, '--file', rc, '--remove',
                                                  'channels', 'defaults',
                                                  use_exception_handler=True)
        assert stdout == ''
        assert "CondaKeyError: 'channels': 'defaults' is not in the 'channels' " \
               "key of the config file" in stderr

    # Test creating a new file with --set
    with make_temp_condarc() as rc:
        stdout, stderr, return_code = run_command(Commands.CONFIG, '--file', rc,
                                                  '--set', 'always_yes', 'true')
        assert stdout == stderr == ''
        assert _read_test_condarc(rc) == """\
always_yes: true
"""


def test_config_command_show():
    # test alphabetical yaml output
    with make_temp_condarc() as rc:
        stdout, stderr, return_code = run_command(Commands.CONFIG, '--file', rc, '--show')
        output_keys = yaml_load(stdout).keys()

        assert stderr == ''
        assert sorted(output_keys) == [item for item in output_keys]


# FIXME Break into multiple tests
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
        stdout, stderr, return_code = run_command(Commands.CONFIG, '--file', rc, '--get', use_exception_handler=True)
        assert stdout.strip() == """\
--set always_yes True
--set changeps1 False
--set channel_alias http://alpha.conda.anaconda.org
--add channels 'defaults'   # lowest priority
--add channels 'test'   # highest priority
--add create_default_packages 'numpy'
--add create_default_packages 'ipython'\
"""
        assert stderr.strip() == "unknown key invalid_key"

        stdout, stderr, return_code = run_command(Commands.CONFIG, '--file', rc,
                                           '--get', 'channels')

        assert stdout.strip() == """\
--add channels 'defaults'   # lowest priority
--add channels 'test'   # highest priority\
"""
        assert stderr == ""

        stdout, stderr, return_code = run_command(Commands.CONFIG, '--file', rc,
                                           '--get', 'changeps1')

        assert stdout.strip() == """\
--set changeps1 False\
"""
        assert stderr == ""

        stdout, stderr, return_code = run_command(Commands.CONFIG, '--file', rc,
                                           '--get', 'changeps1', 'channels')

        assert stdout.strip() == """\
--set changeps1 False
--add channels 'defaults'   # lowest priority
--add channels 'test'   # highest priority\
"""
        assert stderr == ""

        stdout, stderr, return_code = run_command(Commands.CONFIG, '--file', rc, '--get', 'allow_softlinks')

        assert stdout == ""
        assert stderr == ""

        stdout, stderr, return_code = run_command(Commands.CONFIG, '--file', rc, '--get', 'always_softlink')

        assert stdout == ""
        assert stderr == ""

        stdout, stderr, return_code = run_command(Commands.CONFIG, '--file', rc, '--get', 'track_features')

        assert stdout == ""
        assert stderr == ""

        # stdout, stderr, return_code = run_command(Commands.CONFIG, '--file', rc, '--get', 'invalid_key', use_exception_handler=True)
        #
        # assert stdout == ""
        # assert "invalid choice: 'invalid_key'" in stderr

        # stdout, stderr, return_code = run_command(Commands.CONFIG, '--file', rc, '--get', 'not_valid_key', use_exception_handler=True)
        #
        # assert stdout == ""
        # assert "invalid choice: 'not_valid_key'" in stderr


# FIXME Break into multiple tests
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
        stdout, stderr, return_code = run_command(Commands.CONFIG, '--file', rc, '--get', use_exception_handler=True)
        print(stdout)
        assert stdout.strip() == """\
--set always_yes True
--set changeps1 False
--add channels 'defaults'   # lowest priority
--add channels 'test'   # highest priority
--add create_default_packages 'numpy'
--add create_default_packages 'ipython'\
"""
        with open(rc, 'r') as fh:
            print(fh.read())

        stdout, stderr, return_code = run_command(Commands.CONFIG, '--file', rc, '--prepend',
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

        stdout, stderr, return_code = run_command(Commands.CONFIG, '--file', rc,
                                           '--set', 'changeps1', 'true')

        assert stdout == stderr == ''

        assert _read_test_condarc(rc)== """\
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
        stdout, stderr, return_code = run_command(Commands.CONFIG, '--file', rc, '--add',
                                           'disallowed_packages', 'perl')
        assert stdout == stderr == ''
        assert _read_test_condarc(rc) == condarc + """\
disallowed_packages:
  - perl
"""


# FIXME Break into multiple tests
def test_config_command_remove_force():
    # Finally, test --remove, --remove-key
    with make_temp_condarc() as rc:
        run_command(Commands.CONFIG, '--file', rc, '--add',
                          'channels', 'test')
        run_command(Commands.CONFIG, '--file', rc, '--set',
                          'always_yes', 'true')
        stdout, stderr, return_code = run_command(Commands.CONFIG, '--file', rc,
                                           '--remove', 'channels', 'test')
        assert stdout == stderr == ''
        assert yaml_load(_read_test_condarc(rc)) == {'channels': ['defaults'],
                                                     'always_yes': True}

        stdout, stderr, return_code = run_command(Commands.CONFIG, '--file', rc,
                                           '--remove', 'channels', 'test', use_exception_handler=True)
        assert stdout == ''
        assert "CondaKeyError: 'channels': 'test' is not in the 'channels' " \
               "key of the config file" in stderr

        stdout, stderr, return_code = run_command(Commands.CONFIG, '--file', rc,
                                           '--remove', 'disallow', 'python', use_exception_handler=True)
        assert stdout == ''
        assert "CondaKeyError: 'disallow': key 'disallow' " \
               "is not in the config file" in stderr

        stdout, stderr, return_code = run_command(Commands.CONFIG, '--file', rc,
                                           '--remove-key', 'always_yes')
        assert stdout == stderr == ''
        assert yaml_load(_read_test_condarc(rc)) == {'channels': ['defaults']}

        stdout, stderr, return_code = run_command(Commands.CONFIG, '--file', rc,
                                           '--remove-key', 'always_yes', use_exception_handler=True)

        assert stdout == ''
        assert "CondaKeyError: 'always_yes': key 'always_yes' " \
               "is not in the config file" in stderr


# FIXME Break into multiple tests
def test_config_command_bad_args():
    with make_temp_condarc() as rc:
        stdout, stderr, return_code = run_command(Commands.CONFIG, '--file', rc,
                                                  '--add', 'notarealkey', 'test',
                                                  use_exception_handler=True)
        assert stdout == ''

        stdout, stderr, return_code = run_command(Commands.CONFIG, '--file', rc, '--set',
                                                  'notarealkey', 'true',
                                                  use_exception_handler=True)
        assert stdout == ''




def test_config_set():
    # Test the config set command
    # Make sure it accepts only boolean values for boolean keys and any value for string keys

    with make_temp_condarc() as rc:
        stdout, stderr, return_code = run_command(Commands.CONFIG, '--file', rc,
                                                  '--set', 'always_yes', 'yes')
        assert stdout == ''
        assert stderr == ''
        with open(rc) as fh:
            content = yaml_load(fh.read())
            assert content['always_yes'] is True

        stdout, stderr, return_code = run_command(Commands.CONFIG, '--file', rc,
                                                  '--set', 'always_yes', 'no')
        assert stdout == ''
        assert stderr == ''
        with open(rc) as fh:
            content = yaml_load(fh.read())
            assert content['always_yes'] is False

        stdout, stderr, return_code = run_command(Commands.CONFIG, '--file', rc,
                                                  '--set', 'proxy_servers.http', '1.2.3.4:5678')
        assert stdout == ''
        assert stderr == ''
        with open(rc) as fh:
            content = yaml_load(fh.read())
            assert content['always_yes'] is False
            assert content['proxy_servers'] == {'http': '1.2.3.4:5678'}

        stdout, stderr, return_code = run_command(Commands.CONFIG, '--file', rc,
                                                  '--set', 'ssl_verify', 'false')
        assert stdout == ''
        assert stderr == ''

        stdout, stderr, return_code = run_command(Commands.CONFIG, '--file', rc,
                                                  '--get', 'ssl_verify')
        assert stdout.strip() == '--set ssl_verify False'
        assert stderr == ''


def test_set_rc_string():
    # Test setting string keys in .condarc

    # We specifically test ssl_verify since it can be either a boolean or a string
    with make_temp_condarc() as rc:
        assert context.ssl_verify is True
        stdout, stderr, return_code = run_command(Commands.CONFIG, '--file', rc,
                                                  '--set', 'ssl_verify', 'no')
        assert stdout == ''
        assert stderr == ''

        reset_context([rc])
        assert context.ssl_verify is False

        with NamedTemporaryFile() as tf:
            stdout, stderr, return_code = run_command(Commands.CONFIG, '--file', rc,
                                                      '--set', 'ssl_verify', tf.name)
            assert stdout == ''
            assert stderr == ''

            reset_context([rc])
            assert context.ssl_verify == tf.name
