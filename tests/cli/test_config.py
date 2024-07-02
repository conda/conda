# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import json
import os
import re
import sys
from contextlib import contextmanager, nullcontext
from textwrap import dedent

import pytest
from pytest import MonkeyPatch
from pytest_mock import MockerFixture
from ruamel.yaml.scanner import ScannerError

from conda import CondaError, CondaMultiError
from conda.auxlib.compat import Utf8NamedTemporaryFile
from conda.base.context import context, reset_context, sys_rc_path, user_rc_path
from conda.common.configuration import ConfigurationLoadError, CustomValidationError
from conda.common.serialize import yaml_round_trip_dump, yaml_round_trip_load
from conda.exceptions import CondaKeyError, CondaValueError
from conda.gateways.disk.delete import rm_rf
from conda.testing import CondaCLIFixture, TmpEnvFixture

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
        tempfile = Utf8NamedTemporaryFile(suffix=".yml", delete=False)
        tempfile.close()
        temp_path = tempfile.name
        if value:
            with open(temp_path, "w") as f:
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


def test_invalid_yaml(conda_cli: CondaCLIFixture):
    condarc = dedent(
        """\
        fgddgh
        channels:
          - test
        """
    )
    try:
        with make_temp_condarc(condarc) as rc:
            try:
                conda_cli("config", "--file", rc, "--add", "channels", "test")
            except ScannerError as err:
                assert "mapping values are not allowed here" == err.problem
    except ConfigurationLoadError as err:
        assert "reason: invalid yaml at line" in err.message


def test_channels_add_empty(conda_cli: CondaCLIFixture):
    with make_temp_condarc() as rc:
        stdout, stderr, _ = conda_cli(
            "config",
            *("--file", rc),
            *("--add", "channels", "test"),
        )
        assert stdout == stderr == ""
        assert _read_test_condarc(rc) == _channels_as_yaml("test", "defaults")


def test_channels_add_empty_with_defaults(conda_cli: CondaCLIFixture):
    # When defaults is explicitly given, it should not be added
    with make_temp_condarc() as rc:
        stdout, stderr, _ = conda_cli(
            "config",
            *("--file", rc),
            *("--add", "channels", "test"),
            *("--add", "channels", "defaults"),
        )
        assert stdout == ""
        assert (
            stderr.strip()
            == "Warning: 'defaults' already in 'channels' list, moving to the top"
        )
        assert _read_test_condarc(rc) == _channels_as_yaml("defaults", "test")


def test_channels_add_duplicate(conda_cli: CondaCLIFixture):
    channels_initial = _channels_as_yaml("test", "defaults", "mychannel")
    channels_expected = _channels_as_yaml("mychannel", "test", "defaults")
    with make_temp_condarc(channels_initial) as rc:
        stdout, stderr, _ = conda_cli(
            "config",
            *("--file", rc),
            *("--add", "channels", "mychannel"),
        )
        assert stdout == ""
        assert (
            stderr.strip()
            == "Warning: 'mychannel' already in 'channels' list, moving to the top"
        )
        assert _read_test_condarc(rc) == channels_expected


def test_channels_prepend(conda_cli: CondaCLIFixture):
    channels_expected = _channels_as_yaml("mychannel", "test", "defaults")
    with make_temp_condarc(CONDARC_BASE) as rc:
        stdout, stderr, _ = conda_cli(
            "config",
            *("--file", rc),
            *("--prepend", "channels", "mychannel"),
        )
        assert stdout == stderr == ""
        assert _read_test_condarc(rc) == channels_expected + "\n" + CONDARC_OTHER


def test_channels_prepend_duplicate(conda_cli: CondaCLIFixture):
    channels_expected = _channels_as_yaml("defaults", "test")
    with make_temp_condarc(CONDARC_BASE) as rc:
        stdout, stderr, _ = conda_cli(
            "config",
            *("--file", rc),
            *("--prepend", "channels", "defaults"),
        )
        assert stdout == ""
        assert (
            stderr.strip()
            == "Warning: 'defaults' already in 'channels' list, moving to the top"
        )
        assert _read_test_condarc(rc) == channels_expected + CONDARC_OTHER


def test_channels_append(conda_cli: CondaCLIFixture):
    with make_temp_condarc(CONDARC_BASE) as rc:
        stdout, stderr, _ = conda_cli(
            "config",
            *("--file", rc),
            *("--append", "channels", "mychannel"),
        )
        assert stdout == stderr == ""
        assert (
            _read_test_condarc(rc)
            == CONDARC_CHANNELS + "\n  - mychannel\n" + CONDARC_OTHER
        )


def test_channels_append_duplicate(conda_cli: CondaCLIFixture):
    channels_expected = _channels_as_yaml("defaults", "test")
    with make_temp_condarc(CONDARC_BASE) as rc:
        stdout, stderr, _ = conda_cli(
            "config",
            *("--file", rc),
            *("--append", "channels", "test"),
        )
        assert stdout == ""
        assert (
            stderr.strip()
            == "Warning: 'test' already in 'channels' list, moving to the bottom"
        )
        assert _read_test_condarc(rc) == channels_expected + CONDARC_OTHER


def test_channels_remove(conda_cli: CondaCLIFixture):
    channels_expected = _channels_as_yaml("defaults")
    with make_temp_condarc(CONDARC_BASE) as rc:
        stdout, stderr, _ = conda_cli(
            "config",
            *("--file", rc),
            *("--remove", "channels", "test"),
        )
        assert stdout == stderr == ""
        assert _read_test_condarc(rc) == channels_expected + CONDARC_OTHER


def test_channels_remove_duplicate(conda_cli: CondaCLIFixture):
    with make_temp_condarc(CONDARC_BASE) as rc:
        stdout, stderr, _ = conda_cli(
            "config",
            *("--file", rc),
            *("--remove", "channels", "test"),
        )

        with pytest.raises(
            CondaKeyError,
            match=r"'channels': value 'test' not present in config",
        ):
            conda_cli(
                "config",
                *("--file", rc),
                *("--remove", "channels", "test"),
            )


def test_create_condarc_on_set(conda_cli: CondaCLIFixture):
    with make_temp_condarc() as rc:
        stdout, stderr, _ = conda_cli(
            "config",
            *("--file", rc),
            *("--set", "always_yes", "true"),
        )
        assert stdout == stderr == ""
        assert _read_test_condarc(rc) == "always_yes: true\n"


def test_show_sorts_keys(conda_cli: CondaCLIFixture):
    # test alphabetical yaml output
    with make_temp_condarc() as rc:
        stdout, stderr, _ = conda_cli("config", "--file", rc, "--show")
        output_keys = yaml_round_trip_load(stdout).keys()

        assert stderr == ""
        assert sorted(output_keys) == [item for item in output_keys]


def test_get_all(conda_cli: CondaCLIFixture):
    condarc = CONDARC_BASE + "\n\ninvalid_key: true\n"
    with make_temp_condarc(condarc) as rc:
        stdout, stderr, _ = conda_cli("config", "--file", rc, "--get")
        assert stdout == dedent(
            """\
            --set always_yes True
            --set changeps1 False
            --set channel_alias http://alpha.conda.anaconda.org
            --add channels 'defaults'   # lowest priority
            --add channels 'test'   # highest priority
            --add create_default_packages 'numpy'
            --add create_default_packages 'ipython'
            """
        )
        assert stderr.strip() == "Unknown key: 'invalid_key'"


def test_get_all_inc_maps(conda_cli: CondaCLIFixture):
    condarc = "invalid_key: true\nchangeps1: false\n" + CONDARC_CHANNELS + CONDARC_MAPS
    with make_temp_condarc(condarc) as rc:
        stdout, stderr, _ = conda_cli("config", "--file", rc, "--get")
        assert stdout == dedent(
            """\
            --set changeps1 False
            --add channels 'defaults'   # lowest priority
            --add channels 'test'   # highest priority
            --set conda_build.cache_dir /tmp/conda-bld
            --set conda_build.error_overlinking True
            --set proxy_servers.http 1.2.3.4:5678
            --set proxy_servers.https 1.2.3.4:5678
            """
        )
        assert stderr.strip() == "Unknown key: 'invalid_key'"


def test_get_channels_list(conda_cli: CondaCLIFixture):
    with make_temp_condarc(CONDARC_BASE) as rc:
        stdout, stderr, _ = conda_cli("config", "--file", rc, "--get", "channels")
        assert stdout == dedent(
            """\
            --add channels 'defaults'   # lowest priority
            --add channels 'test'   # highest priority
            """
        )
        assert stderr == ""


def test_get_boolean_value(conda_cli: CondaCLIFixture):
    with make_temp_condarc(CONDARC_BASE) as rc:
        stdout, stderr, _ = conda_cli("config", "--file", rc, "--get", "changeps1")
        assert stdout.strip() == "--set changeps1 False"
        assert stderr == ""


def test_get_string_value(conda_cli: CondaCLIFixture):
    with make_temp_condarc(CONDARC_BASE) as rc:
        stdout, stderr, _ = conda_cli("config", "--file", rc, "--get", "channel_alias")
        assert stdout.strip() == "--set channel_alias http://alpha.conda.anaconda.org"
        assert stderr == ""


@pytest.mark.parametrize(
    "key,value",
    [
        ("proxy_servers.http", "1.2.3.4:5678"),
        ("conda_build.cache_dir", "/tmp/conda-bld"),
    ],
)
def test_get_map_subkey(key, value, conda_cli: CondaCLIFixture):
    with make_temp_condarc(CONDARC_MAPS) as rc:
        stdout, stderr, _ = conda_cli("config", "--file", rc, "--get", key)
        assert stdout.strip() == f"--set {key} {value}"
        assert stderr == ""


def test_get_map_full(conda_cli: CondaCLIFixture):
    with make_temp_condarc(CONDARC_MAPS) as rc:
        stdout, stderr, _ = conda_cli("config", "--file", rc, "--get", "proxy_servers")
        assert "--set proxy_servers.http 1.2.3.4:5678\n" in stdout
        assert "--set proxy_servers.https 1.2.3.4:5678\n" in stdout
        assert stderr == ""


def test_get_multiple_keys(conda_cli: CondaCLIFixture):
    with make_temp_condarc(CONDARC_BASE) as rc:
        stdout, stderr, _ = conda_cli(
            "config",
            *("--file", rc),
            *("--get", "changeps1", "channels"),
        )
        assert stdout == dedent(
            """\
            --set changeps1 False
            --add channels 'defaults'   # lowest priority
            --add channels 'test'   # highest priority
            """
        )
        assert stderr == ""


def test_get_multiple_keys_incl_map_subkey(conda_cli: CondaCLIFixture):
    with make_temp_condarc(CONDARC_BASE + CONDARC_MAPS) as rc:
        stdout, stderr, _ = conda_cli(
            "config",
            *("--file", rc),
            *("--get", "changeps1", "proxy_servers.http"),
        )
        assert stdout == dedent(
            """\
            --set changeps1 False
            --set proxy_servers.http 1.2.3.4:5678
            """
        )
        assert stderr == ""


def test_get_multiple_keys_incl_map_full(conda_cli: CondaCLIFixture):
    with make_temp_condarc(CONDARC_BASE + CONDARC_MAPS) as rc:
        stdout, stderr, _ = conda_cli(
            "config",
            *("--file", rc),
            *("--get", "changeps1", "proxy_servers"),
        )
        assert stdout == dedent(
            """\
            --set changeps1 False
            --set proxy_servers.http 1.2.3.4:5678
            --set proxy_servers.https 1.2.3.4:5678
            """
        )
        assert stderr == ""


def test_get_unconfigured_key(conda_cli: CondaCLIFixture):
    with make_temp_condarc(CONDARC_BASE) as rc:
        stdout, stderr, _ = conda_cli(
            "config",
            *("--file", rc),
            *("--get", "allow_softlinks"),
        )
        assert stdout == ""
        assert stderr == ""


def test_get_invalid_key(conda_cli: CondaCLIFixture):
    condarc = CONDARC_BASE
    with make_temp_condarc(condarc) as rc:
        stdout, stderr, _ = conda_cli("config", "--file", rc, "--get", "invalid_key")
        assert stdout == ""
        assert stderr.strip() == "Unknown key: 'invalid_key'"


def test_set_key(conda_cli: CondaCLIFixture):
    key, from_val, to_val = "changeps1", "true", "false"
    with make_temp_condarc(CONDARC_BASE) as rc:
        stdout, stderr, _ = conda_cli("config", "--file", rc, "--set", key, to_val)
        assert stdout == stderr == ""
        assert _read_test_condarc(rc) == CONDARC_BASE.replace(
            f"{key}: {from_val}", f"{key}: {to_val}"
        )


@pytest.mark.parametrize(
    "key,from_val,to_val",
    [
        ("proxy_servers.http", "1.2.3.4:5678", "4.3.2.1:9876"),
        ("conda_build.cache_dir", "/tmp/conda-bld", "/var/tmp/build"),
        # broken: write process for conda_build section converts bools to strings
        pytest.param(
            "conda_build.error_overlinking",
            "true",
            "false",
            marks=pytest.mark.skip("known to be broken"),
        ),
    ],
)
def test_set_map_key(key, from_val, to_val, conda_cli: CondaCLIFixture):
    parent_key, sub_key = key.split(".")
    with make_temp_condarc(CONDARC_MAPS) as rc:
        stdout, stderr, _ = conda_cli("config", "--file", rc, "--set", key, to_val)
        assert stdout == stderr == ""
        assert _read_test_condarc(rc) == CONDARC_MAPS.replace(
            f"  {sub_key}: {from_val}", f"  {sub_key}: {to_val}"
        )


def test_set_unconfigured_key(conda_cli: CondaCLIFixture):
    key, to_val = "restore_free_channel", "true"
    with make_temp_condarc(CONDARC_BASE) as rc:
        stdout, stderr, _ = conda_cli("config", "--file", rc, "--set", key, to_val)
        assert stdout == stderr == ""
        assert _read_test_condarc(rc) == CONDARC_BASE + f"{key}: {to_val}\n"


def test_set_invalid_key(conda_cli: CondaCLIFixture):
    key, to_val = "invalid_key", "a_bogus_value"
    with make_temp_condarc(CONDARC_BASE) as rc:
        with pytest.raises(CondaKeyError, match=r"'invalid_key': unknown parameter"):
            conda_cli("config", "--file", rc, "--set", key, to_val)

        assert _read_test_condarc(rc) == CONDARC_BASE


def test_add_key(conda_cli: CondaCLIFixture):
    with make_temp_condarc(CONDARC_BASE) as rc:
        stdout, stderr, _ = conda_cli(
            "config",
            *("--file", rc),
            *("--add", "disallowed_packages", "perl"),
        )
        assert stdout == stderr == ""
        assert (
            _read_test_condarc(rc) == CONDARC_BASE + "disallowed_packages:\n  - perl\n"
        )


def test_add_invalid_key(conda_cli: CondaCLIFixture):
    key, to_val = "invalid_key", "a_bogus_value"
    with make_temp_condarc(CONDARC_BASE) as rc:
        with pytest.raises(
            CondaValueError, match=f"Key '{key}' is not a known sequence parameter."
        ):
            conda_cli("config", "--file", rc, "--add", key, to_val)

        assert _read_test_condarc(rc) == CONDARC_BASE


def test_remove_key(conda_cli: CondaCLIFixture):
    key, value = "changeps1", "false"
    with make_temp_condarc(CONDARC_BASE) as rc:
        stdout, stderr, _ = conda_cli("config", "--file", rc, "--remove-key", key)
        assert stdout == stderr == ""
        assert f"{key}: {value}\n" not in _read_test_condarc(rc)


def test_remove_key_duplicate(conda_cli: CondaCLIFixture):
    key, value = "changeps1", "false"
    with make_temp_condarc(CONDARC_BASE) as rc:
        conda_cli("config", "--file", rc, "--remove-key", key)

        with pytest.raises(CondaKeyError, match=r"'changeps1': undefined in config"):
            conda_cli("config", "--file", rc, "--remove-key", key)

        assert f"{key}: {value}\n" not in _read_test_condarc(rc)


def test_remove_unconfigured_key(conda_cli: CondaCLIFixture):
    key = "restore_free_channel"
    with make_temp_condarc(CONDARC_BASE) as rc:
        with pytest.raises(
            CondaKeyError,
            match=r"'restore_free_channel': undefined in config",
        ):
            conda_cli("config", "--file", rc, "--remove-key", key)

        assert _read_test_condarc(rc) == CONDARC_BASE


@pytest.mark.parametrize(
    "key,str_value,py_value",
    [
        ("always_yes", "yes", True),
        ("always_yes", "no", False),
        ("always_yes", "true", True),
        ("always_yes", "false", False),
        ("channel_alias", "https://repo.example.com", "https://repo.example.com"),
        ("proxy_servers.http", "1.2.3.4:5678", {"http": "1.2.3.4:5678"}),
    ],
)
def test_set_check_types(key, str_value, py_value, conda_cli: CondaCLIFixture):
    with make_temp_condarc() as rc:
        stdout, stderr, _ = conda_cli("config", "--file", rc, "--set", key, str_value)
        assert stdout == stderr == ""
        with open(rc) as fh:
            content = yaml_round_trip_load(fh.read())
            if "." in key:
                key = key.split(".", 1)[0]
            assert content[key] == py_value


def test_set_and_get_bool(conda_cli: CondaCLIFixture):
    key = "restore_free_channel"
    with make_temp_condarc() as rc:
        stdout, stderr, _ = conda_cli("config", "--file", rc, "--set", key, "yes")
        stdout, stderr, _ = conda_cli("config", "--file", rc, "--get", key)
        assert stdout.strip() == f"--set {key} True"
        assert stderr == ""


def test_ssl_verify_default():
    with make_temp_condarc() as rc:
        reset_context([rc])
        assert context.ssl_verify is True


def test_ssl_verify_set_bool(conda_cli: CondaCLIFixture):
    with make_temp_condarc() as rc:
        stdout, stderr, _ = conda_cli(
            "config",
            *("--file", rc),
            *("--set", "ssl_verify", "no"),
        )
        assert stdout == stderr == ""
        reset_context([rc])
        assert context.ssl_verify is False


def test_ssl_verify_set_filename(conda_cli: CondaCLIFixture):
    with make_temp_condarc() as rc, Utf8NamedTemporaryFile() as tf:
        stdout, stderr, _ = conda_cli(
            "config",
            *("--file", rc),
            *("--set", "ssl_verify", tf.name),
        )
        assert stdout == stderr == ""
        reset_context([rc])
        assert context.ssl_verify == tf.name


def test_set_rc_without_user_rc(conda_cli: CondaCLIFixture):
    if os.path.exists(sys_rc_path):
        # Backup system rc_config
        with open(sys_rc_path) as fh:
            sys_rc_config_backup = yaml_round_trip_load(fh)
        restore_sys_rc_config_backup = True
    else:
        restore_sys_rc_config_backup = False

    if os.path.exists(user_rc_path):
        # Backup user rc_config
        with open(user_rc_path) as fh:
            user_rc_config_backup = yaml_round_trip_load(fh)
        # Remove user rc_path
        os.remove(user_rc_path)
        restore_user_rc_config_backup = True
    else:
        restore_user_rc_config_backup = False

    try:
        # Write custom system sys_rc_config
        with open(sys_rc_path, "w") as rc:
            rc.write(yaml_round_trip_dump({"channels": ["conda-forge"]}))
    except OSError:
        # In case, we don't have writing right to the system rc config file
        pytest.skip("No writing right to root prefix.")

    # This would create a user rc_config
    stdout, stderr, return_code = conda_cli("config", "--add", "channels", "test")
    assert stdout == stderr == ""
    assert yaml_round_trip_load(_read_test_condarc(user_rc_path)) == {
        "channels": ["test", "conda-forge"]
    }

    if restore_user_rc_config_backup:
        # Restore previous user rc_config
        with open(user_rc_path, "w") as rc:
            rc.write(yaml_round_trip_dump(user_rc_config_backup))
    if restore_sys_rc_config_backup:
        # Restore previous system rc_config
        with open(sys_rc_path, "w") as rc:
            rc.write(yaml_round_trip_dump(sys_rc_config_backup))


def test_custom_multichannels_append(conda_cli: CondaCLIFixture):
    with make_temp_condarc() as rc:
        stdout, stderr, return_code = conda_cli(
            "config",
            *("--file", rc),
            *("--append", "custom_multichannels.foo", "bar"),
        )
        assert stdout == stderr == ""
        assert _read_test_condarc(rc) == yaml_round_trip_dump(
            {"custom_multichannels": {"foo": ["bar"]}}
        )


def test_custom_multichannels_add(conda_cli: CondaCLIFixture):
    with make_temp_condarc() as rc:
        stdout, stderr, return_code = conda_cli(
            "config",
            *("--file", rc),
            *("--add", "custom_multichannels.foo", "bar"),
        )
        assert stdout == stderr == ""
        assert _read_test_condarc(rc) == yaml_round_trip_dump(
            {"custom_multichannels": {"foo": ["bar"]}}
        )


def test_custom_multichannels_prepend(conda_cli: CondaCLIFixture):
    with make_temp_condarc() as rc:
        stdout, stderr, return_code = conda_cli(
            "config",
            *("--file", rc),
            *("--prepend", "custom_multichannels.foo", "bar"),
        )
        assert stdout == stderr == ""
        assert _read_test_condarc(rc) == yaml_round_trip_dump(
            {"custom_multichannels": {"foo": ["bar"]}}
        )


def test_custom_multichannels_append_duplicate(conda_cli: CondaCLIFixture):
    custom_multichannels_expected = yaml_round_trip_dump(
        {"custom_multichannels": {"foo": ["bar"]}}
    )
    with make_temp_condarc(custom_multichannels_expected) as rc:
        stdout, stderr, return_code = conda_cli(
            "config",
            *("--file", rc),
            *("--append", "custom_multichannels.foo", "bar"),
        )
        assert stdout == ""
        assert (
            stderr.strip()
            == "Warning: 'bar' already in 'custom_multichannels.foo' list, moving to the bottom"
        )
        assert _read_test_condarc(rc) == custom_multichannels_expected


def test_custom_multichannels_add_duplicate(conda_cli: CondaCLIFixture):
    custom_multichannels_expected = yaml_round_trip_dump(
        {"custom_multichannels": {"foo": ["bar"]}}
    )
    with make_temp_condarc(custom_multichannels_expected) as rc:
        stdout, stderr, return_code = conda_cli(
            "config",
            *("--file", rc),
            *("--add", "custom_multichannels.foo", "bar"),
        )
        assert stdout == ""
        assert (
            stderr.strip()
            == "Warning: 'bar' already in 'custom_multichannels.foo' list, moving to the top"
        )
        assert _read_test_condarc(rc) == custom_multichannels_expected


def test_custom_multichannels_prepend_duplicate(conda_cli: CondaCLIFixture):
    custom_multichannels_expected = yaml_round_trip_dump(
        {"custom_multichannels": {"foo": ["bar"]}}
    )
    with make_temp_condarc(custom_multichannels_expected) as rc:
        stdout, stderr, return_code = conda_cli(
            "config",
            *("--file", rc),
            *("--prepend", "custom_multichannels.foo", "bar"),
        )
        assert stdout == ""
        assert (
            stderr.strip()
            == "Warning: 'bar' already in 'custom_multichannels.foo' list, moving to the top"
        )
        assert _read_test_condarc(rc) == custom_multichannels_expected


def test_conda_config_describe(
    tmp_env: TmpEnvFixture,
    conda_cli: CondaCLIFixture,
    monkeypatch: MonkeyPatch,
):
    RE_PARAMETERS = (
        re.compile(rf"^# # {name} \(", flags=re.MULTILINE)
        for category, names in context.category_map.items()
        if category not in ("CLI-only", "Hidden and Undocumented")
        for name in names
    )

    with tmp_env() as prefix:
        condarc = prefix / "condarc"

        stdout, stderr, _ = conda_cli("config", f"--file={condarc}", "--describe")
        assert not stderr

        for pattern in RE_PARAMETERS:
            assert pattern.search(stdout)

        stdout, stderr, _ = conda_cli(
            "config", f"--file={condarc}", "--describe", "--json"
        )
        assert not stderr
        json_obj = json.loads(stdout.strip())
        assert len(json_obj) >= 55
        assert "description" in json_obj[0]

        monkeypatch.setenv("CONDA_QUIET", "yes")
        reset_context()
        assert context.quiet

        stdout, stderr, _ = conda_cli("config", f"--file={condarc}", "--show-sources")
        assert not stderr
        assert "envvars" in stdout.strip()

        stdout, stderr, _ = conda_cli(
            "config", f"--file={condarc}", "--show-sources", "--json"
        )
        assert not stderr
        json_obj = json.loads(stdout.strip())
        assert json_obj.get("envvars", {}).get("quiet") is True
        assert json_obj.get("cmd_line", {}).get("json") is True

        monkeypatch.delenv("CONDA_QUIET")
        reset_context()
        assert not context.quiet

        conda_cli("config", f"--file={condarc}", "--set", "changeps1", "false")
        with pytest.raises(CondaError):
            conda_cli("config", f"--file={condarc}", "--write-default")

        rm_rf(prefix / "condarc")
        conda_cli("config", f"--file={condarc}", "--write-default")

        data = (prefix / "condarc").read_text()
        for pattern in RE_PARAMETERS:
            assert pattern.search(data)

        stdout, stderr, _ = conda_cli(
            "config", f"--file={condarc}", "--describe", "--json"
        )
        assert not stderr
        json_obj = json.loads(stdout.strip())
        assert len(json_obj) >= 42
        assert "description" in json_obj[0]

        monkeypatch.setenv("CONDA_QUIET", "yes")
        reset_context()
        assert context.quiet

        stdout, stderr, _ = conda_cli("config", f"--file={condarc}", "--show-sources")
        assert not stderr
        assert "envvars" in stdout.strip()

        stdout, stderr, _ = conda_cli(
            "config", f"--file={condarc}", "--show-sources", "--json"
        )
        assert not stderr
        json_obj = json.loads(stdout.strip())
        assert json_obj.get("envvars", {}).get("quiet") is True
        assert json_obj.get("cmd_line", {}).get("json") is True


def test_conda_config_validate(
    tmp_env: TmpEnvFixture,
    mocker: MockerFixture,
    conda_cli: CondaCLIFixture,
):
    with tmp_env() as prefix:
        mocker.patch(
            "conda.base.context.determine_target_prefix",
            return_value=prefix,
        )
        condarc = prefix / "condarc"

        # test that we can set a valid value
        conda_cli("config", f"--file={condarc}", "--set", "ssl_verify", "no")

        # test that we can validate a valid config
        stdout, stderr, err = conda_cli("config", "--validate")
        assert not stdout
        assert not stderr
        assert not err

        # set invalid values
        conda_cli(
            "config",
            f"--file={condarc}",
            *("--set", "ssl_verify", "/path/doesnt/exist"),
            *("--set", "default_python", "anaconda"),
        )
        reset_context()

        # test that we validate individual values
        with pytest.raises(
            CustomValidationError,
            match=(
                default_python_error := (
                    r"default_python value 'anaconda' not of the form "
                    r"'\[23\]\.\[0-9\]\[0-9\]\?'"
                )
            ),
        ):
            assert context.default_python == "anaconda"
        with pytest.raises(
            CustomValidationError,
            match=(
                ssl_verify_error := (
                    "must be a boolean, a path to a certificate bundle file, a path to a "
                    "directory containing certificates of trusted CAs, or 'truststore' to use "
                    "the operating system certificate store."
                )
            ),
        ):
            assert context.ssl_verify == "/path/doesnt/exist"

        # test that validating an invalid config fails
        with pytest.raises(CondaMultiError) as exc:
            conda_cli("config", "--validate")

        # test that the error message contains both validation errors
        assert len(exc.value.errors) == 2
        assert exc.match(default_python_error)
        assert exc.match(ssl_verify_error)


def test_conda_config_validate_sslverify_truststore(
    tmp_env: TmpEnvFixture,
    mocker: MockerFixture,
    conda_cli: CondaCLIFixture,
):
    with tmp_env() as prefix:
        mocker.patch(
            "conda.base.context.determine_target_prefix",
            return_value=prefix,
        )
        condarc = prefix / "condarc"

        # test that we can set ssl_verify
        conda_cli("config", f"--file={condarc}", "--set", "ssl_verify", "truststore")

        # test that truststore is valid for Python 3.10+
        with (
            pytest.raises(
                CustomValidationError,
                match=(
                    truststore_error := (
                        "`ssl_verify: truststore` is only supported on "
                        "Python 3.10 or later"
                    )
                ),
            )
            if sys.version_info < (3, 10)
            else nullcontext()
        ):
            assert context.ssl_verify == "truststore"

        # test that truststore is a valid value for Python 3.10+
        with (
            pytest.raises(CustomValidationError, match=truststore_error)
            if sys.version_info < (3, 10)
            else nullcontext()
        ):
            stdout, stderr, err = conda_cli("config", "--validate")
            assert not stdout
            assert not stderr
            assert not err
