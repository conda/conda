# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

import os
import pytest

from contextlib import contextmanager
from textwrap import dedent
import pytest

from conda.auxlib.compat import Utf8NamedTemporaryFile

from conda.base.context import context, reset_context, sys_rc_path, user_rc_path
from conda.cli.python_api import Commands, run_command
from conda.common.configuration import ConfigurationLoadError
from conda.common.serialize import yaml_round_trip_load, yaml_round_trip_dump
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
        tempfile = Utf8NamedTemporaryFile(suffix='.yml', delete=False)
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


def _channels_as_yaml(*channels):
    return "\n  - ".join(("channels:",) + channels) + "\n"


CONDARC_CHANNELS = _channels_as_yaml("test", "defaults")

CONDARC_OTHER = """\
create_default_packages:
  - ipython
  - numpy

changeps1: false

# Here is a comment
always_yes: true

channel_alias: http://alpha.conda.anaconda.org
"""

CONDARC_MAPS = """\
proxy_servers:
  http: 1.2.3.4:5678
  https: 1.2.3.4:5678

conda_build:
  cache_dir: /tmp/conda-bld
  error_overlinking: true
"""

CONDARC_BASE = CONDARC_CHANNELS + "\n" + CONDARC_OTHER


def test_invalid_yaml():
    condarc = dedent("""\
        fgddgh
        channels:
          - test
        """)
    try:
        with make_temp_condarc(condarc) as rc:
            rc_path = rc
            run_command(Commands.CONFIG, '--file', rc, '--add', 'channels', 'test')
    except ConfigurationLoadError as err:
        assert "reason: invalid yaml at line" in err.message, err.message


def test_channels_add_empty():
    with make_temp_condarc() as rc:
        stdout, stderr, return_code = run_command(Commands.CONFIG, '--file', rc, '--add',
                                                  'channels', 'test')
        assert stdout == stderr == ''
        assert _read_test_condarc(rc) == _channels_as_yaml("test", "defaults")


def test_channels_add_empty_with_defaults():
    # When defaults is explicitly given, it should not be added
    with make_temp_condarc() as rc:
        stdout, stderr, _ = run_command(Commands.CONFIG, '--file', rc,
                                        '--add', 'channels', 'test',
                                        '--add', 'channels', 'defaults',
                                        use_exception_handler=True)
        assert stdout == ''
        assert stderr.strip() == "Warning: 'defaults' already in 'channels' list, moving to the top"
        assert _read_test_condarc(rc) == _channels_as_yaml("defaults", "test")


def test_channels_add_duplicate():
    channels_initial = _channels_as_yaml("test", "defaults", "mychannel")
    channels_expected = _channels_as_yaml("mychannel", "test", "defaults")
    with make_temp_condarc(channels_initial) as rc:
        stdout, stderr, _ = run_command(Commands.CONFIG, '--file', rc,
                                        '--add', 'channels', 'mychannel',
                                        use_exception_handler=True)
        assert stdout == ''
        assert stderr.strip() == "Warning: 'mychannel' already in 'channels' list, moving to the top"
        assert _read_test_condarc(rc) == channels_expected


def test_channels_prepend():
    channels_expected = _channels_as_yaml("mychannel", "test", "defaults")
    with make_temp_condarc(CONDARC_BASE) as rc:
        stdout, stderr, _ = run_command(Commands.CONFIG, '--file', rc,
                                        '--prepend', 'channels', 'mychannel')
        assert stdout == stderr == ''
        assert _read_test_condarc(rc) == channels_expected + "\n" + CONDARC_OTHER


def test_channels_prepend_duplicate():
    channels_expected = _channels_as_yaml("defaults", "test")
    with make_temp_condarc(CONDARC_BASE) as rc:
        stdout, stderr, _ = run_command(Commands.CONFIG, '--file', rc,
                                        '--prepend', 'channels', 'defaults')
        assert stdout == ''
        assert stderr.strip() == "Warning: 'defaults' already in 'channels' list, moving to the top"
        assert _read_test_condarc(rc) == channels_expected + CONDARC_OTHER


def test_channels_append():
    with make_temp_condarc(CONDARC_BASE) as rc:
        stdout, stderr, _ = run_command(Commands.CONFIG, '--file', rc,
                                        '--append', 'channels', 'mychannel',
                                        use_exception_handler=True)
        assert stdout == stderr == ''
        assert _read_test_condarc(rc) == \
            CONDARC_CHANNELS + "\n  - mychannel\n" + CONDARC_OTHER


def test_channels_append_duplicate():
    channels_expected = _channels_as_yaml("defaults", "test")
    with make_temp_condarc(CONDARC_BASE) as rc:
        stdout, stderr, _ = run_command(Commands.CONFIG, '--file', rc,
                                        '--append', 'channels', 'test',
                                        use_exception_handler=True)
        assert stdout == ''
        assert stderr.strip() == "Warning: 'test' already in 'channels' list, moving to the bottom"
        assert _read_test_condarc(rc) == channels_expected + CONDARC_OTHER


def test_channels_remove():
    channels_expected = _channels_as_yaml("defaults")
    with make_temp_condarc(CONDARC_BASE) as rc:
        stdout, stderr, _ = run_command(Commands.CONFIG, '--file', rc,
                                        '--remove', 'channels', 'test')
        assert stdout == stderr == ''
        assert _read_test_condarc(rc) == channels_expected + CONDARC_OTHER


def test_channels_remove_duplicate():
    with make_temp_condarc(CONDARC_BASE) as rc:
        stdout, stderr, _ = run_command(Commands.CONFIG, '--file', rc,
                                        '--remove', 'channels', 'test')
        stdout, stderr, _ = run_command(Commands.CONFIG, '--file', rc,
                                        '--remove', 'channels', 'test',
                                        use_exception_handler=True)
        assert stdout == ''
        assert stderr.strip() == "CondaKeyError: 'channels': 'test' is not "\
                                 "in the 'channels' key of the config file"


def test_create_condarc_on_set():
    with make_temp_condarc() as rc:
        stdout, stderr, return_code = run_command(Commands.CONFIG, '--file', rc,
                                                  '--set', 'always_yes', 'true')
        assert stdout == stderr == ''
        assert _read_test_condarc(rc) == "always_yes: true\n"


def test_show_sorts_keys():
    # test alphabetical yaml output
    with make_temp_condarc() as rc:
        stdout, stderr, return_code = run_command(Commands.CONFIG, '--file', rc, '--show')
        output_keys = yaml_round_trip_load(stdout).keys()

        assert stderr == ''
        assert sorted(output_keys) == [item for item in output_keys]


def test_get_all():
    condarc = CONDARC_BASE + "\n\ninvalid_key: true\n"
    with make_temp_condarc(condarc) as rc:
        stdout, stderr, _ = run_command(Commands.CONFIG, '--file', rc, '--get', use_exception_handler=True)
        assert stdout == dedent("""\
            --set always_yes True
            --set changeps1 False
            --set channel_alias http://alpha.conda.anaconda.org
            --add channels 'defaults'   # lowest priority
            --add channels 'test'   # highest priority
            --add create_default_packages 'numpy'
            --add create_default_packages 'ipython'
            """)
        assert stderr.strip() == "unknown key invalid_key"


def test_get_all_inc_maps():
    condarc = ("invalid_key: true\nchangeps1: false\n" +
                CONDARC_CHANNELS + CONDARC_MAPS)
    with make_temp_condarc(condarc) as rc:
        stdout, stderr, _ = run_command(Commands.CONFIG, '--file', rc, '--get', use_exception_handler=True)
        assert stdout == dedent("""\
            --set changeps1 False
            --add channels 'defaults'   # lowest priority
            --add channels 'test'   # highest priority
            --set conda_build.cache_dir /tmp/conda-bld
            --set conda_build.error_overlinking True
            --set proxy_servers.http 1.2.3.4:5678
            --set proxy_servers.https 1.2.3.4:5678
            """)
        assert stderr.strip() == "unknown key invalid_key"


def test_get_channels_list():
    with make_temp_condarc(CONDARC_BASE) as rc:
        stdout, stderr, _ = run_command(Commands.CONFIG, '--file', rc,
                                           '--get', 'channels')
        assert stdout == dedent("""\
            --add channels 'defaults'   # lowest priority
            --add channels 'test'   # highest priority
            """)
        assert stderr == ""


def test_get_boolean_value():
    with make_temp_condarc(CONDARC_BASE) as rc:
        stdout, stderr, _ = run_command(Commands.CONFIG, '--file', rc,
                                        '--get', 'changeps1')
        assert stdout.strip() == "--set changeps1 False"
        assert stderr == ""


def test_get_string_value():
    with make_temp_condarc(CONDARC_BASE) as rc:
        stdout, stderr, _ = run_command(Commands.CONFIG, '--file', rc,
                                        '--get', 'channel_alias')
        assert stdout.strip() == "--set channel_alias http://alpha.conda.anaconda.org"
        assert stderr == ""


@pytest.mark.parametrize("key,value", [
    ("proxy_servers.http", "1.2.3.4:5678"),
    ("conda_build.cache_dir", "/tmp/conda-bld"),
    ])
def test_get_map_subkey(key, value):
    with make_temp_condarc(CONDARC_MAPS) as rc:
        stdout, stderr, _ = run_command(Commands.CONFIG, '--file', rc,
                                        '--get', key)
        assert stdout.strip() == f"--set {key} {value}"
        assert stderr == ""


def test_get_map_full():
    with make_temp_condarc(CONDARC_MAPS) as rc:
        stdout, stderr, _ = run_command(Commands.CONFIG, '--file', rc,
                                        '--get', 'proxy_servers')
        assert "--set proxy_servers.http 1.2.3.4:5678\n" in stdout
        assert "--set proxy_servers.https 1.2.3.4:5678\n" in stdout
        assert stderr == ""


def test_get_multiple_keys():
    with make_temp_condarc(CONDARC_BASE) as rc:
        stdout, stderr, _ = run_command(Commands.CONFIG, '--file', rc,
                                        '--get', 'changeps1', 'channels')
        assert stdout == dedent("""\
            --set changeps1 False
            --add channels 'defaults'   # lowest priority
            --add channels 'test'   # highest priority
            """)
        assert stderr == ""


def test_get_multiple_keys_incl_map_subkey():
    with make_temp_condarc(CONDARC_BASE + CONDARC_MAPS) as rc:
        stdout, stderr, _ = run_command(Commands.CONFIG, '--file', rc,
                                        '--get', 'changeps1', 'proxy_servers.http')
        assert stdout == dedent("""\
            --set changeps1 False
            --set proxy_servers.http 1.2.3.4:5678
            """)
        assert stderr == ""


def test_get_multiple_keys_incl_map_full():
    with make_temp_condarc(CONDARC_BASE + CONDARC_MAPS) as rc:
        stdout, stderr, _ = run_command(Commands.CONFIG, '--file', rc,
                                        '--get', 'changeps1', 'proxy_servers')
        assert stdout == dedent("""\
            --set changeps1 False
            --set proxy_servers.http 1.2.3.4:5678
            --set proxy_servers.https 1.2.3.4:5678
            """)
        assert stderr == ""


def test_get_unconfigured_key():
    with make_temp_condarc(CONDARC_BASE) as rc:
        stdout, stderr, _ = run_command(Commands.CONFIG, '--file', rc,
                                        '--get', 'allow_softlinks')
        assert stdout == ""
        assert stderr == ""


def test_get_invalid_key():
    condarc = CONDARC_BASE
    with make_temp_condarc(condarc) as rc:
        stdout, stderr, _ = run_command(Commands.CONFIG, '--file', rc,
                                        '--get', 'invalid_key',
                                        use_exception_handler=True)
        assert stdout == ""
        assert stderr.strip() == "unknown key invalid_key"


def test_set_key():
    key, from_val, to_val = "changeps1", "true", "false"
    with make_temp_condarc(CONDARC_BASE) as rc:
        stdout, stderr, _= run_command(Commands.CONFIG, '--file', rc,
                                       '--set', key, to_val)
        assert stdout == stderr == ''
        assert _read_test_condarc(rc)== \
                CONDARC_BASE.replace(f"{key}: {from_val}", f"{key}: {to_val}")


@pytest.mark.parametrize("key,from_val,to_val", [
    ("proxy_servers.http", "1.2.3.4:5678", "4.3.2.1:9876"),
    ("conda_build.cache_dir", "/tmp/conda-bld", "/var/tmp/build"),
    # broken: write process for conda_build section converts bools to strings
    pytest.param("conda_build.error_overlinking", "true", "false",
                 marks=pytest.mark.skip("known to be broken")),
    ])
def test_set_map_key(key, from_val, to_val):
    parent_key, sub_key = key.split(".")
    with make_temp_condarc(CONDARC_MAPS) as rc:
        stdout, stderr, _= run_command(Commands.CONFIG, '--file', rc,
                                       '--set', key, to_val)
        assert stdout == stderr == ''
        assert _read_test_condarc(rc) == \
                CONDARC_MAPS.replace(f"  {sub_key}: {from_val}",
                                     f"  {sub_key}: {to_val}")


def test_set_unconfigured_key():
    key, to_val = "restore_free_channel", "true"
    with make_temp_condarc(CONDARC_BASE) as rc:
        stdout, stderr, _= run_command(Commands.CONFIG, '--file', rc,
                                       '--set', key, to_val,
                                        use_exception_handler=True)
        assert stdout == stderr == ''
        assert _read_test_condarc(rc) == CONDARC_BASE + f"{key}: {to_val}\n"


def test_set_invalid_key():
    key, to_val = "invalid_key", "a_bogus_value"
    error = f"CondaValueError: Key '{key}' is not a known primitive parameter."
    with make_temp_condarc(CONDARC_BASE) as rc:
        stdout, stderr, _= run_command(Commands.CONFIG, '--file', rc,
                                       '--set', key, to_val,
                                        use_exception_handler=True)
        assert stdout == ''
        assert stderr.strip() == error
        assert _read_test_condarc(rc)== CONDARC_BASE


def test_add_key():
    with make_temp_condarc(CONDARC_BASE) as rc:
        stdout, stderr, _ = run_command(Commands.CONFIG, '--file', rc,
                                        '--add', 'disallowed_packages', 'perl')
        assert stdout == stderr == ''
        assert _read_test_condarc(rc) == \
            CONDARC_BASE + "disallowed_packages:\n  - perl\n"


def test_add_invalid_key():
    key, to_val = "invalid_key", "a_bogus_value"
    error = f"CondaValueError: Key '{key}' is not a known sequence parameter."
    with make_temp_condarc(CONDARC_BASE) as rc:
        stdout, stderr, _= run_command(Commands.CONFIG, '--file', rc,
                                       '--add', key, to_val,
                                        use_exception_handler=True)
        assert stdout == ''
        assert stderr.strip() == error
        assert _read_test_condarc(rc)== CONDARC_BASE


def test_remove_key():
    key, value = "changeps1", "false"
    with make_temp_condarc(CONDARC_BASE) as rc:
        stdout, stderr, _ = run_command(Commands.CONFIG, '--file', rc,
                                        '--remove-key', key,
                                        use_exception_handler=True)
        assert stdout == stderr == ''
        assert f"{key}: {value}\n" not in _read_test_condarc(rc)


def test_remove_key_duplicate():
    key, value = "changeps1", "false"
    error = f"CondaKeyError: '{key}': key '{key}' is not in the config file"
    with make_temp_condarc(CONDARC_BASE) as rc:
        stdout, stderr, _ = run_command(Commands.CONFIG, '--file', rc,
                                        '--remove-key', key,
                                        use_exception_handler=True)
        stdout, stderr, _ = run_command(Commands.CONFIG, '--file', rc,
                                        '--remove-key', key,
                                        use_exception_handler=True)
        assert stdout == ''
        assert stderr.strip() == error
        assert f"{key}: {value}\n" not in _read_test_condarc(rc)


def test_remove_unconfigured_key():
    key = "restore_free_channel"
    error = f"CondaKeyError: '{key}': key '{key}' is not in the config file"
    with make_temp_condarc(CONDARC_BASE) as rc:
        stdout, stderr, _ = run_command(Commands.CONFIG, '--file', rc,
                                        '--remove-key', key,
                                        use_exception_handler=True)
        assert stdout == ''
        assert stderr.strip() == error
        assert _read_test_condarc(rc) == CONDARC_BASE


@pytest.mark.parametrize("key,str_value,py_value", [
    ("always_yes", "yes", True),
    ("always_yes", "no", False),
    ("always_yes", "true", True),
    ("always_yes", "false", False),
    ("channel_alias", "https://repo.example.com", "https://repo.example.com"),
    ("proxy_servers.http", "1.2.3.4:5678", {'http': '1.2.3.4:5678'}),
    ])
def test_set_check_types(key, str_value, py_value):
    with make_temp_condarc() as rc:
        stdout, stderr, _ = run_command(Commands.CONFIG, '--file', rc,
                                        '--set', key, str_value,
                                        use_exception_handler=True)
        assert stdout == stderr == ''
        with open(rc) as fh:
            content = yaml_round_trip_load(fh.read())
            if "." in key: key = key.split(".", 1)[0]
            assert content[key] == py_value


def test_set_and_get_bool():
    key = 'restore_free_channel'
    with make_temp_condarc() as rc:
        stdout, stderr, _ = run_command(Commands.CONFIG, '--file', rc,
                                        '--set', key, 'yes')
        stdout, stderr, _ = run_command(Commands.CONFIG, '--file', rc,
                                        '--get', key)
        assert stdout.strip() == f'--set {key} True'
        assert stderr == ''


def test_ssl_verify_default():
    with make_temp_condarc() as rc:
        reset_context([rc])
        assert context.ssl_verify is True


def test_ssl_verify_set_bool():
    with make_temp_condarc() as rc:
        stdout, stderr, _ = run_command(Commands.CONFIG, '--file', rc,
                                        '--set', 'ssl_verify', 'no')
        assert stdout == stderr == ''
        reset_context([rc])
        assert context.ssl_verify is False


def test_ssl_verify_set_filename():
    with make_temp_condarc() as rc, Utf8NamedTemporaryFile() as tf:
        stdout, stderr, _ = run_command(Commands.CONFIG, '--file', rc,
                                        '--set', 'ssl_verify', tf.name)
        assert stdout == stderr == ''
        reset_context([rc])
        assert context.ssl_verify == tf.name


def test_set_rc_without_user_rc():

    if os.path.exists(sys_rc_path):
        # Backup system rc_config
        with open(sys_rc_path, 'r') as fh:
            sys_rc_config_backup = yaml_round_trip_load(fh)
        restore_sys_rc_config_backup = True
    else:
        restore_sys_rc_config_backup = False

    if os.path.exists(user_rc_path):
        # Backup user rc_config
        with open(user_rc_path, 'r') as fh:
            user_rc_config_backup = yaml_round_trip_load(fh)
        # Remove user rc_path
        os.remove(user_rc_path)
        restore_user_rc_config_backup = True
    else:
        restore_user_rc_config_backup = False

    try:
        # Write custom system sys_rc_config
        with open(sys_rc_path, 'w') as rc:
            rc.write(yaml_round_trip_dump({'channels':['conda-forge']}))
    except (OSError, IOError):
        # In case, we don't have writing right to the system rc config file
        pytest.skip("No writing right to root prefix.")

    # This would create a user rc_config
    stdout, stderr, return_code = run_command(Commands.CONFIG,
                                              '--add', 'channels', 'test')
    assert stdout == stderr == ''
    assert yaml_round_trip_load(_read_test_condarc(user_rc_path)) == {'channels': ['test', 'conda-forge']}

    if restore_user_rc_config_backup:
        # Restore previous user rc_config
        with open(user_rc_path, 'w') as rc:
            rc.write(yaml_round_trip_dump(user_rc_config_backup))
    if restore_sys_rc_config_backup:
        # Restore previous system rc_config
        with open(sys_rc_path, 'w') as rc:
            rc.write(yaml_round_trip_dump(sys_rc_config_backup))


def test_custom_multichannels_append():
    with make_temp_condarc() as rc:
        stdout, stderr, return_code = run_command(Commands.CONFIG, '--file', rc, '--append',
                                                  'custom_multichannels.foo', 'bar')
        assert stdout == stderr == ''
        assert _read_test_condarc(rc) == yaml_round_trip_dump({"custom_multichannels": {"foo": ["bar"]}})


def test_custom_multichannels_add():
    with make_temp_condarc() as rc:
        stdout, stderr, return_code = run_command(Commands.CONFIG, '--file', rc, '--add',
                                                  'custom_multichannels.foo', 'bar')
        assert stdout == stderr == ''
        assert _read_test_condarc(rc) == yaml_round_trip_dump({"custom_multichannels": {"foo": ["bar"]}})


def test_custom_multichannels_prepend():
    with make_temp_condarc() as rc:
        stdout, stderr, return_code = run_command(Commands.CONFIG, '--file', rc, '--prepend',
                                                  'custom_multichannels.foo', 'bar')
        assert stdout == stderr == ''
        assert _read_test_condarc(rc) == yaml_round_trip_dump({"custom_multichannels": {"foo": ["bar"]}})


def test_custom_multichannels_append_duplicate():
    custom_multichannels_expected = yaml_round_trip_dump({"custom_multichannels": {"foo": ["bar"]}})
    with make_temp_condarc(custom_multichannels_expected) as rc:
        stdout, stderr, return_code = run_command(Commands.CONFIG, '--file', rc, '--append',
                                                  'custom_multichannels.foo', 'bar')
        assert stdout == ''
        assert stderr.strip() == "Warning: 'bar' already in 'custom_multichannels.foo' list, moving to the bottom"
        assert _read_test_condarc(rc) == custom_multichannels_expected


def test_custom_multichannels_add_duplicate():
    custom_multichannels_expected = yaml_round_trip_dump({"custom_multichannels": {"foo": ["bar"]}})
    with make_temp_condarc(custom_multichannels_expected) as rc:
        stdout, stderr, return_code = run_command(Commands.CONFIG, '--file', rc, '--add',
                                                  'custom_multichannels.foo', 'bar')
        assert stdout == ''
        assert stderr.strip() == "Warning: 'bar' already in 'custom_multichannels.foo' list, moving to the top"
        assert _read_test_condarc(rc) == custom_multichannels_expected


def test_custom_multichannels_prepend_duplicate():
    custom_multichannels_expected = yaml_round_trip_dump({"custom_multichannels": {"foo": ["bar"]}})
    with make_temp_condarc(custom_multichannels_expected) as rc:
        stdout, stderr, return_code = run_command(Commands.CONFIG, '--file', rc, '--prepend',
                                                  'custom_multichannels.foo', 'bar')
        assert stdout == ''
        assert stderr.strip() == "Warning: 'bar' already in 'custom_multichannels.foo' list, moving to the top"
        assert _read_test_condarc(rc) == custom_multichannels_expected
