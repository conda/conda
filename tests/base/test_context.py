# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from __future__ import annotations

import os
from itertools import chain
from os.path import abspath, join
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING
from unittest import mock

import pytest
from platformdirs import user_data_dir

from conda.auxlib.collection import AttrDict
from conda.auxlib.ish import dals
from conda.base.constants import (
    APP_NAME,
    DEFAULT_AGGRESSIVE_UPDATE_PACKAGES,
    DEFAULT_CHANNELS,
    ChannelPriority,
    PathConflict,
)
from conda.base.context import (
    Context,
    channel_alias_validation,
    context,
    default_python_validation,
    get_plugin_config_data,
    reset_context,
    validate_channels,
    validate_prefix_name,
)
from conda.common.configuration import Configuration, ValidationError, YamlRawParameter
from conda.common.path import expand, win_path_backout
from conda.common.serialize import yaml_round_trip_load
from conda.common.url import join_url, path_to_url
from conda.exceptions import (
    ChannelDenied,
    ChannelNotAllowed,
    CondaValueError,
    EnvironmentNameNotFound,
)
from conda.gateways.disk.permissions import make_read_only
from conda.models.channel import Channel
from conda.models.match_spec import MatchSpec
from conda.utils import on_win

if TYPE_CHECKING:
    from pytest import MonkeyPatch

    from conda.testing import PathFactoryFixture

TEST_CONDARC = dals(
    """
    custom_channels:
      darwin: https://some.url.somewhere/stuff
      chuck: http://another.url:8080/with/path
    custom_multichannels:
      michele:
        - https://do.it.with/passion
        - learn_from_every_thing
      steve:
        - more-downloads
    channel_settings:
      - channel: darwin
        param_one: value_one
        param_two: value_two
      - channel: "http://localhost"
        param_one: value_one
        param_two: value_two
    migrated_custom_channels:
      darwin: s3://just/cant
      chuck: file:///var/lib/repo/
    migrated_channel_aliases:
      - https://conda.anaconda.org
    channel_alias: ftp://new.url:8082
    conda-build:
      root-dir: /some/test/path
    proxy_servers:
      http: http://user:pass@corp.com:8080
      https: none
      ftp:
      sftp: ''
      ftps: false
      rsync: 'false'
    aggressive_update_packages: []
    channel_priority: false
    """
)


@pytest.fixture
def testdata() -> None:
    reset_context()
    context._set_raw_data(
        {
            "testdata": YamlRawParameter.make_raw_parameters(
                "testdata", yaml_round_trip_load(TEST_CONDARC)
            )
        }
    )


def test_migrated_custom_channels(testdata: None):
    assert (
        Channel(
            "https://some.url.somewhere/stuff/darwin/noarch/a-mighty-fine.tar.bz2"
        ).canonical_name
        == "darwin"
    )
    assert (
        Channel("s3://just/cant/darwin/noarch/a-mighty-fine.tar.bz2").canonical_name
        == "darwin"
    )
    assert Channel("s3://just/cant/darwin/noarch/a-mighty-fine.tar.bz2").urls() == [
        "https://some.url.somewhere/stuff/darwin/noarch"
    ]


def test_old_channel_alias(testdata: None):
    platform = context.subdir

    cf_urls = [
        f"ftp://new.url:8082/conda-forge/{platform}",
        "ftp://new.url:8082/conda-forge/noarch",
    ]
    assert Channel("conda-forge").urls() == cf_urls

    url = "https://conda.anaconda.org/conda-forge/osx-64/some-great-package.tar.bz2"
    assert Channel(url).canonical_name == "conda-forge"
    assert Channel(url).base_url == "ftp://new.url:8082/conda-forge"
    assert Channel(url).urls() == [
        "ftp://new.url:8082/conda-forge/osx-64",
        "ftp://new.url:8082/conda-forge/noarch",
    ]
    assert Channel(
        "https://conda.anaconda.org/conda-forge/label/dev/linux-64/"
        "some-great-package.tar.bz2"
    ).urls() == [
        "ftp://new.url:8082/conda-forge/label/dev/linux-64",
        "ftp://new.url:8082/conda-forge/label/dev/noarch",
    ]


def test_signing_metadata_url_base(testdata: None):
    SIGNING_URL_BASE = "https://conda.example.com/pkgs"
    string = f"signing_metadata_url_base: {SIGNING_URL_BASE}"
    reset_context()
    rd = {
        "testdata": YamlRawParameter.make_raw_parameters(
            "testdata", yaml_round_trip_load(string)
        )
    }
    context._set_raw_data(rd)
    assert context.signing_metadata_url_base == SIGNING_URL_BASE


def test_signing_metadata_url_base_empty_default_channels(testdata: None):
    string = dals(
        """
        default_channels: []
        """
    )
    reset_context()
    rd = {
        "testdata": YamlRawParameter.make_raw_parameters(
            "testdata", yaml_round_trip_load(string)
        )
    }
    context._set_raw_data(rd)
    assert len(context.default_channels) == 0
    assert context.signing_metadata_url_base is None


def test_client_ssl_cert(testdata: None):
    string = dals(
        """
        client_ssl_cert_key: /some/key/path
        """
    )
    reset_context()
    rd = {
        "testdata": YamlRawParameter.make_raw_parameters(
            "testdata", yaml_round_trip_load(string)
        )
    }
    context._set_raw_data(rd)
    pytest.raises(ValidationError, context.validate_configuration)


def test_conda_envs_path(testdata: None):
    saved_envs_path = os.environ.get("CONDA_ENVS_PATH")
    beginning = "C:" + os.sep if on_win else os.sep
    path1 = beginning + os.sep.join(["my", "envs", "dir", "1"])
    path2 = beginning + os.sep.join(["my", "envs", "dir", "2"])
    try:
        os.environ["CONDA_ENVS_PATH"] = path1
        reset_context()
        assert context.envs_dirs[0] == path1

        os.environ["CONDA_ENVS_PATH"] = os.pathsep.join([path1, path2])
        reset_context()
        assert context.envs_dirs[0] == path1
        assert context.envs_dirs[1] == path2
    finally:
        if saved_envs_path:
            os.environ["CONDA_ENVS_PATH"] = saved_envs_path
        else:
            del os.environ["CONDA_ENVS_PATH"]


def test_conda_bld_path(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    conda_bld_path = str(tmp_path)
    conda_bld_url = path_to_url(conda_bld_path)

    monkeypatch.setenv("CONDA_BLD_PATH", conda_bld_path)
    reset_context()
    assert context.bld_path == conda_bld_path
    assert len(context.conda_build_local_paths) >= 1
    assert context.conda_build_local_paths[0] == conda_bld_path

    channel = Channel("local")
    assert channel.channel_name == "local"
    assert channel.channel_location is None
    assert channel.platform is None
    assert channel.package_filename is None
    assert channel.auth is None
    assert channel.token is None
    assert channel.scheme is None
    assert channel.canonical_name == "local"
    assert channel.url() is None
    assert channel.urls() == [
        join_url(url, subdir)
        for url in context.conda_build_local_urls
        for subdir in (context.subdir, "noarch")
    ]

    channel = Channel(conda_bld_url)
    assert channel.canonical_name == "local"
    assert channel.platform is None
    assert channel.package_filename is None
    assert channel.auth is None
    assert channel.token is None
    assert channel.scheme == "file"
    assert channel.urls() == [
        join_url(conda_bld_url, context.subdir),
        join_url(conda_bld_url, "noarch"),
    ]
    assert channel.url() == join_url(conda_bld_url, context.subdir)
    assert (
        channel.channel_name.lower()
        == win_path_backout(conda_bld_path).lstrip("/").lower()
    )
    # location really is an empty string; all path information is in channel_name
    assert channel.channel_location == ""
    assert channel.canonical_name == "local"


def test_custom_multichannels(testdata: None):
    assert context.custom_multichannels["michele"] == (
        Channel("passion"),
        Channel("learn_from_every_thing"),
    )


def test_restore_free_channel(monkeypatch: MonkeyPatch) -> None:
    free_channel = "https://repo.anaconda.com/pkgs/free"
    assert free_channel not in context.default_channels

    monkeypatch.setenv("CONDA_RESTORE_FREE_CHANNEL", "true")
    reset_context()
    assert context.restore_free_channel

    assert context.default_channels[1] == free_channel


def test_proxy_servers(testdata: None):
    assert context.proxy_servers["http"] == "http://user:pass@corp.com:8080"
    assert context.proxy_servers["https"] is None
    assert context.proxy_servers["ftp"] is None
    assert context.proxy_servers["sftp"] == ""
    assert context.proxy_servers["ftps"] == "False"
    assert context.proxy_servers["rsync"] == "false"


def test_conda_build_root_dir(testdata: None):
    assert context.conda_build["root-dir"] == "/some/test/path"


@pytest.mark.parametrize("path_conflict", PathConflict.__members__)
def test_clobber_enum(monkeypatch: MonkeyPatch, path_conflict: str) -> None:
    monkeypatch.setenv("CONDA_PATH_CONFLICT", path_conflict)
    reset_context()
    assert context.path_conflict == PathConflict(path_conflict)


def test_context_parameter_map(testdata: None):
    parameters = list(context.list_parameters())
    mapped = [name for names in context.category_map.values() for name in names]

    # ignore anaconda-anon-usage's context monkeypatching
    if "anaconda_anon_usage" in parameters:
        parameters.remove("anaconda_anon_usage")
    if "anaconda_anon_usage" in mapped:
        mapped.remove("anaconda_anon_usage")

    assert not set(parameters).difference(mapped)
    assert len(parameters) == len(mapped)


def test_context_parameters_have_descriptions(testdata: None):
    skip_categories = ("CLI-only", "Hidden and Undocumented")
    documented_parameter_names = chain.from_iterable(
        (
            parameter_names
            for category, parameter_names in context.category_map.items()
            if category not in skip_categories
        )
    )

    from pprint import pprint

    for name in documented_parameter_names:
        context.get_descriptions()[name]
        pprint(context.describe_parameter(name))


def test_local_build_root_custom_rc(
    testdata: None,
    monkeypatch: MonkeyPatch,
    path_factory: PathFactoryFixture,
) -> None:
    # testdata sets conda-build.root-dir
    assert context.local_build_root == abspath("/some/test/path")

    monkeypatch.setenv("CONDA_BLD_PATH", bld_path := str(path_factory()))
    reset_context()
    assert context.local_build_root == bld_path

    monkeypatch.setenv("CONDA_CROOT", croot := str(path_factory()))
    reset_context()
    assert context.local_build_root == croot


def test_default_target_is_root_prefix(testdata: None):
    assert context.target_prefix == context.root_prefix


def test_target_prefix(
    path_factory: PathFactoryFixture,
    monkeypatch: MonkeyPatch,
) -> None:
    (envs1 := path_factory()).mkdir()
    (envs2 := path_factory()).mkdir()
    envs_dirs = (str(envs1), str(envs2))

    monkeypatch.setenv("CONDA_ENVS_DIRS", os.pathsep.join(envs_dirs))
    reset_context()
    assert context._envs_dirs == envs_dirs
    assert context.envs_dirs[:2] == envs_dirs

    # with both dirs writable, choose first
    reset_context(argparse_args=SimpleNamespace(name="blarg"))
    assert context.target_prefix == str(envs1 / "blarg")

    # with first dir read-only, choose second
    make_read_only(envs1 / ".conda_envs_dir_test")
    reset_context(argparse_args=SimpleNamespace(name="blarg"))
    assert context.target_prefix == str(envs2 / "blarg")

    # if first dir is read-only but environment exists, choose first
    (envs1 / "blarg").mkdir()
    reset_context(argparse_args=SimpleNamespace(name="blarg"))
    assert context.target_prefix == str(envs1 / "blarg")


def test_aggressive_update_packages(monkeypatch: MonkeyPatch) -> None:
    assert context._aggressive_update_packages == DEFAULT_AGGRESSIVE_UPDATE_PACKAGES

    specs = ("certifi", "openssl>=1.1")
    monkeypatch.setenv("CONDA_AGGRESSIVE_UPDATE_PACKAGES", ",".join(specs))
    reset_context()
    assert context._aggressive_update_packages == specs
    assert context.aggressive_update_packages == tuple(map(MatchSpec, specs))


def test_channel_priority(testdata: None):
    assert context.channel_priority == ChannelPriority.DISABLED


def test_threads(monkeypatch: MonkeyPatch) -> None:
    default_value = None
    assert context.default_threads == default_value
    assert context.repodata_threads == default_value
    assert context.verify_threads == 1
    assert context.execute_threads == 1

    with monkeypatch.context() as m:
        m.setenv("CONDA_DEFAULT_THREADS", "3")
        reset_context()
        assert context.default_threads == 3
        assert context.verify_threads == 3
        assert context.repodata_threads == 3
        assert context.execute_threads == 3

    with monkeypatch.context() as m:
        m.setenv("CONDA_VERIFY_THREADS", "3")
        reset_context()
        assert context.default_threads == default_value
        assert context.verify_threads == 3
        assert context.repodata_threads == default_value
        assert context.execute_threads == 1

    with monkeypatch.context() as m:
        m.setenv("CONDA_REPODATA_THREADS", "3")
        reset_context()
        assert context.default_threads == default_value
        assert context.verify_threads == 1
        assert context.repodata_threads == 3
        assert context.execute_threads == 1

    with monkeypatch.context() as m:
        m.setenv("CONDA_EXECUTE_THREADS", "3")
        reset_context()
        assert context.default_threads == default_value
        assert context.verify_threads == 1
        assert context.repodata_threads == default_value
        assert context.execute_threads == 3

    with monkeypatch.context() as m:
        m.setenv("CONDA_EXECUTE_THREADS", "3")
        m.setenv("CONDA_DEFAULT_THREADS", "1")
        reset_context()
        assert context.default_threads == 1
        assert context.verify_threads == 1
        assert context.repodata_threads == 1
        assert context.execute_threads == 3


def test_channels_empty(testdata: None):
    """Test when no channels provided in cli and no condarc config is present."""
    reset_context(())
    with pytest.warns((PendingDeprecationWarning, FutureWarning)):
        assert context.channels == ("defaults",)


def test_channels_defaults_condarc(testdata: None):
    """Test when no channels provided in cli, but some in condarc."""
    reset_context(())
    string = dals(
        """
        channels: ['defaults', 'conda-forge']
        """
    )
    rd = {
        "testdata": YamlRawParameter.make_raw_parameters(
            "testdata", yaml_round_trip_load(string)
        )
    }
    context._set_raw_data(rd)
    assert context.channels == ("defaults", "conda-forge")


def test_specify_channels_cli_not_adding_defaults_no_condarc(testdata: None):
    """
    When the channel haven't been specified in condarc, 'defaults'
    should NOT be present when specifying channel in the cli.

    See https://github.com/conda/conda/issues/14217 for context.
    """
    reset_context((), argparse_args=AttrDict(channel=["conda-forge"]))
    with pytest.warns((PendingDeprecationWarning, FutureWarning)):
        assert context.channels == ("conda-forge", "defaults")


def test_specify_channels_cli_condarc(testdata: None):
    """
    When the channel have been specified in condarc, these channels
    should be used along with the one specified
    """
    reset_context((), argparse_args=AttrDict(channel=["conda-forge"]))
    string = dals(
        """
        channels: ['defaults', 'conda-forge']
        """
    )
    rd = {
        "testdata": YamlRawParameter.make_raw_parameters(
            "testdata", yaml_round_trip_load(string)
        )
    }
    context._set_raw_data(rd)
    assert context.channels == ("defaults", "conda-forge")


def test_specify_different_channels_cli_condarc(testdata: None):
    """
    When the channel have been specified in condarc, these channels
    should be used along with the one specified
    In this test, the given channel in cli is different from condarc
    'defaults' should not be added
    """
    reset_context((), argparse_args=AttrDict(channel=["other"]))
    string = dals(
        """
        channels: ['conda-forge']
        """
    )
    rd = {
        "testdata": YamlRawParameter.make_raw_parameters(
            "testdata", yaml_round_trip_load(string)
        )
    }
    context._set_raw_data(rd)
    assert context.channels == ("conda-forge", "other")


def test_specify_same_channels_cli_as_in_condarc(testdata: None):
    """
    When the channel have been specified in condarc, these channels
    should be used along with the one specified

    In this test, the given channel in cli is the same as in condarc
    'defaults' should not be added
    See https://github.com/conda/conda/issues/10732
    """
    reset_context((), argparse_args=AttrDict(channel=["conda-forge"]))
    string = dals(
        """
        channels: ['conda-forge']
        """
    )
    rd = {
        "testdata": YamlRawParameter.make_raw_parameters(
            "testdata", yaml_round_trip_load(string)
        )
    }
    context._set_raw_data(rd)
    assert context.channels == ("conda-forge",)


def test_expandvars(testdata: None):
    """Environment variables should be expanded in settings that have expandvars=True."""

    def _get_expandvars_context(attr, config_expr, env_value):
        with mock.patch.dict(os.environ, {"TEST_VAR": env_value}):
            reset_context(())
            string = f"{attr}: {config_expr}"
            rd = {
                "testdata": YamlRawParameter.make_raw_parameters(
                    "testdata", yaml_round_trip_load(string)
                )
            }
            context._set_raw_data(rd)
            return getattr(context, attr)

    ssl_verify = _get_expandvars_context("ssl_verify", "${TEST_VAR}", "yes")
    assert ssl_verify

    for attr, env_value in (
        ("client_ssl_cert", "foo"),
        ("client_ssl_cert_key", "foo"),
        ("channel_alias", "http://foo"),
    ):
        value = _get_expandvars_context(attr, "${TEST_VAR}", env_value)
        assert value == env_value

    for attr in (
        "migrated_custom_channels",
        "proxy_servers",
    ):
        value = _get_expandvars_context("proxy_servers", "{'x': '${TEST_VAR}'}", "foo")
        assert value == {"x": "foo"}

    for attr in (
        "channels",
        "default_channels",
        "allowlist_channels",
        "denylist_channels",
    ):
        value = _get_expandvars_context(attr, "['${TEST_VAR}']", "foo")
        assert value == ("foo",)

    custom_channels = _get_expandvars_context(
        "custom_channels", "{'x': '${TEST_VAR}'}", "http://foo"
    )
    assert custom_channels["x"].location == "foo"

    custom_multichannels = _get_expandvars_context(
        "custom_multichannels", "{'x': ['${TEST_VAR}']}", "http://foo"
    )
    assert len(custom_multichannels["x"]) == 1
    assert custom_multichannels["x"][0].location == "foo"

    envs_dirs = _get_expandvars_context("envs_dirs", "['${TEST_VAR}']", "/foo")
    assert any("foo" in d for d in envs_dirs)

    pkgs_dirs = _get_expandvars_context("pkgs_dirs", "['${TEST_VAR}']", "/foo")
    assert any("foo" in d for d in pkgs_dirs)


def test_channel_settings(testdata: None):
    """Ensure "channel_settings" appears as we expect it to on the context object."""
    assert context.channel_settings == (
        {"channel": "darwin", "param_one": "value_one", "param_two": "value_two"},
        {
            "channel": "http://localhost",
            "param_one": "value_one",
            "param_two": "value_two",
        },
    )


def test_subdirs(monkeypatch: MonkeyPatch) -> None:
    assert context.subdirs == (context.subdir, "noarch")

    subdirs = ("linux-highest", "linux-64", "noarch")
    monkeypatch.setenv("CONDA_SUBDIRS", ",".join(subdirs))
    reset_context()
    assert context.subdirs == subdirs


def test_local_build_root_default_rc():
    reset_context()

    if context.root_writable:
        assert context.local_build_root == join(context.root_prefix, "conda-bld")
    else:
        assert context.local_build_root == expand("~/conda-bld")


if on_win:
    VALIDATE_PREFIX_NAME_BASE_DIR = Path("C:\\Users\\name\\prefix_dir\\")
else:
    VALIDATE_PREFIX_NAME_BASE_DIR = Path("/home/user/prefix_dir/")

VALIDATE_PREFIX_ENV_NAME = "env-name"

VALIDATE_PREFIX_TEST_CASES = (
    # First scenario which triggers an Environment not found error
    (
        VALIDATE_PREFIX_ENV_NAME,
        False,
        (
            VALIDATE_PREFIX_NAME_BASE_DIR,
            EnvironmentNameNotFound(VALIDATE_PREFIX_ENV_NAME),
        ),
        VALIDATE_PREFIX_NAME_BASE_DIR.joinpath(VALIDATE_PREFIX_ENV_NAME),
    ),
    # Passing in not allowed characters as the prefix name
    (
        "not/allow#characters:in-path",
        False,
        (None, None),
        CondaValueError("Invalid environment name"),
    ),
    # Passing in not allowed characters as the prefix name
    (
        "base",
        False,
        (None, None),
        CondaValueError("Use of 'base' as environment name is not allowed here."),
    ),
)


@pytest.mark.parametrize(
    "prefix,allow_base,mock_return_values,expected", VALIDATE_PREFIX_TEST_CASES
)
def test_validate_prefix_name(prefix, allow_base, mock_return_values, expected):
    ctx = mock.MagicMock()

    with (
        mock.patch("conda.base.context._first_writable_envs_dir") as mock_one,
        mock.patch("conda.base.context.locate_prefix_by_name") as mock_two,
    ):
        mock_one.side_effect = [mock_return_values[0]]
        mock_two.side_effect = [mock_return_values[1]]

        if isinstance(expected, CondaValueError):
            with pytest.raises(CondaValueError) as exc:
                validate_prefix_name(prefix, ctx, allow_base=allow_base)

            # We fuzzy match the error message here. Doing this exactly is not important
            assert str(expected) in str(exc)

        else:
            actual = validate_prefix_name(prefix, ctx, allow_base=allow_base)
            assert actual == str(expected)


def test_get_plugin_config_data_file_source(tmp_path):
    """
    Test file source of plugin configuration values
    """
    condarc = tmp_path / "condarc"

    condarc.write_text(
        dals(
            """
            plugins:
              option_one: value_one
              option_two: value_two
            """
        )
    )

    config_data = {
        path: data for path, data in Configuration._load_search_path((condarc,))
    }

    plugin_config_data = get_plugin_config_data(config_data)

    assert plugin_config_data.get(condarc) is not None

    option_one = plugin_config_data.get(condarc).get("option_one")
    assert option_one is not None
    assert option_one.value(None) == "value_one"

    option_two = plugin_config_data.get(condarc).get("option_two")
    assert option_two is not None
    assert option_two.value(None) == "value_two"


def test_get_plugin_config_data_env_var_source():
    """
    Test environment variable source of plugin configuration values
    """
    raw_data = {
        "envvars": {
            "plugins_option_one": {"_raw_value": "value_one"},
            "plugins_option_two": {"_raw_value": "value_two"},
        }
    }

    plugin_config_data = get_plugin_config_data(raw_data)

    assert plugin_config_data.get("envvars") is not None

    option_one = plugin_config_data.get("envvars").get("option_one")
    assert option_one is not None
    assert option_one.get("_raw_value") == "value_one"

    option_two = plugin_config_data.get("envvars").get("option_two")
    assert option_two is not None
    assert option_two.get("_raw_value") == "value_two"


def test_get_plugin_config_data_skip_bad_values():
    """
    Make sure that values that are not frozendict for file sources are skipped
    """
    path = Path("/tmp/")

    class Value:
        def value(self, _):
            return "some_value"

    raw_data = {path: {"plugins": Value()}}

    plugin_config_data = get_plugin_config_data(raw_data)

    assert plugin_config_data == {}


@pytest.mark.parametrize(
    "value,expected",
    (
        ("https://example.com/", True),
        ("bad_value", "channel_alias value 'bad_value' must have scheme/protocol."),
    ),
)
def test_channel_alias_validation(value, expected):
    """
    Ensure that ``conda.base.context.channel_alias_validation`` works as expected
    """
    assert channel_alias_validation(value) == expected


@pytest.mark.parametrize(
    "value,expected",
    (
        ("3.12", True),
        (
            "4.12",
            "default_python value '4.12' not of the form '[23].[0-9][0-9]?' or ''",
        ),
        ("", True),
        (
            "not a number",
            "default_python value 'not a number' not of the form '[23].[0-9][0-9]?' or ''",
        ),
    ),
)
def test_default_python_validation(value, expected):
    """
    Ensure that ``conda.base.context.default_python_validation`` works as expected
    """
    assert default_python_validation(value) == expected


def test_check_allowlist(monkeypatch: MonkeyPatch):
    # any channel is allowed
    validate_channels(("conda-canary", "conda-forge"))

    allowlist = (
        "defaults",
        "conda-forge",
        "https://beta.conda.anaconda.org/conda-test",
    )
    monkeypatch.setenv("CONDA_ALLOWLIST_CHANNELS", ",".join(allowlist))
    monkeypatch.setenv("CONDA_SUBDIR", "linux-64")
    reset_context()

    with pytest.raises(ChannelNotAllowed):
        validate_channels(("conda-canary",))

    with pytest.raises(ChannelNotAllowed):
        validate_channels(("https://repo.anaconda.com/pkgs/denied",))

    validate_channels(("defaults",))
    validate_channels((DEFAULT_CHANNELS[0], DEFAULT_CHANNELS[1]))
    validate_channels(("https://conda.anaconda.org/conda-forge/linux-64",))


def test_check_denylist(monkeypatch: MonkeyPatch):
    # any channel is allowed
    validate_channels(("conda-canary", "conda-forge"))

    denylist = (
        "defaults",
        "conda-forge",
        "https://beta.conda.anaconda.org/conda-test",
    )
    monkeypatch.setenv("CONDA_DENYLIST_CHANNELS", ",".join(denylist))
    monkeypatch.setenv("CONDA_SUBDIR", "linux-64")
    reset_context()

    with pytest.raises(ChannelDenied):
        validate_channels(("defaults",))

    with pytest.raises(ChannelDenied):
        validate_channels((DEFAULT_CHANNELS[0], DEFAULT_CHANNELS[1]))

    with pytest.raises(ChannelDenied):
        validate_channels(("conda-forge",))

    with pytest.raises(ChannelDenied):
        validate_channels(("https://conda.anaconda.org/conda-forge/linux-64",))

    with pytest.raises(ChannelDenied):
        validate_channels(("https://beta.conda.anaconda.org/conda-test",))


def test_check_allowlist_and_denylist(monkeypatch: MonkeyPatch):
    # any channel is allowed
    validate_channels(
        ("defaults", "https://beta.conda.anaconda.org/conda-test", "conda-forge")
    )
    allowlist = (
        "defaults",
        "https://beta.conda.anaconda.org/conda-test",
        "conda-forge",
    )
    denylist = ("conda-forge",)
    monkeypatch.setenv("CONDA_ALLOWLIST_CHANNELS", ",".join(allowlist))
    monkeypatch.setenv("CONDA_DENYLIST_CHANNELS", ",".join(denylist))
    monkeypatch.setenv("CONDA_SUBDIR", "linux-64")
    reset_context()

    # neither in allowlist nor denylist
    with pytest.raises(ChannelNotAllowed):
        validate_channels(("conda-canary",))

    # conda-forge is on denylist, so it should raise ChannelDenied
    # even though it is in the allowlist
    with pytest.raises(ChannelDenied):
        validate_channels(("conda-forge",))
    with pytest.raises(ChannelDenied):
        validate_channels(("https://conda.anaconda.org/conda-forge/linux-64",))

    validate_channels(("defaults",))
    validate_channels((DEFAULT_CHANNELS[0], DEFAULT_CHANNELS[1]))


def test_pkgs_envs_default_dirs(testdata, unset_condarc_pkgs):
    """Test that the default envs/pkgs directories are not in the base environment."""
    user_data = Path(user_data_dir(APP_NAME, APP_NAME, None, False))
    envs = user_data / "envs"
    pkgs = user_data / "pkgs"

    # The pkgs and envs should exist in the user data dir
    assert str(envs) in set(context.envs_dirs)
    assert str(pkgs) in set(context.pkgs_dirs)

    # They should not be in the prefix
    prefix = Path(context.conda_prefix)
    assert not envs.is_relative_to(prefix)
    assert not pkgs.is_relative_to(prefix)


def test_set_pkgs_envs_default_dirs(testdata, unset_condarc_pkgs):
    """Test that the envs/pkgs directories revert to legacy behavior if set."""
    envs = "/usr/local/foo/envs"
    pkgs = "/usr/local/foo/pkgs"

    additional_settings = dals(
        f"""
        envs_dirs:
          - {envs}
        pkgs_dirs:
          - {pkgs}
        """
    )

    # Set up the context
    reset_context()
    condarc = yaml_round_trip_load(TEST_CONDARC + additional_settings)
    context._set_raw_data(
        {"testdata": YamlRawParameter.make_raw_parameters("testdata", condarc)}
    )

    # Track the calls to the context methods that get the old prefix
    # locations of the pkgs and envs
    with (
        mock.patch.object(
            context, "_prefix_pkgs_dirs", wraps=context._prefix_pkgs_dirs
        ) as mock_prefix_pkgs,
        mock.patch.object(
            context, "_prefix_envs_dirs", wraps=context._prefix_envs_dirs
        ) as mock_prefix_envs,
    ):
        context_envs_dirs = context.envs_dirs
        context_pkgs_dirs = context.pkgs_dirs

    # The prefix pkgs and envs methods should have been called
    mock_prefix_pkgs.assert_called_once()
    mock_prefix_envs.assert_called_once()

    # The prefix paths should match the context.pkgs_dirs and
    # context.envs_dirs
    assert set(context_envs_dirs) == set(context._prefix_envs_dirs())
    assert set(context_pkgs_dirs) == set(context._prefix_pkgs_dirs())


def test_pkgs_envs_old_default_dirs(
    testdata, propagate_conda_logger, caplog, unset_condarc_pkgs, unset_condarc_envs
):
    """Test that the old locations of envs/pkgs directories generate a log warning."""
    envs = Path(context.root_prefix) / "envs"
    pkgs = Path(context.root_prefix) / "pkgs"

    with (
        mock.patch.object(
            Context,
            "root_prefix_pkgs",
            return_value=str(pkgs),
            new_callable=mock.PropertyMock,
        ),
        mock.patch.object(
            Context,
            "root_prefix_envs",
            return_value=str(envs),
            new_callable=mock.PropertyMock,
        ),
        mock.patch("conda.base.context.isdir") as mock_isdir,
        mock.patch("conda.base.context.os.listdir") as mock_listdir,
    ):

        def mock_isdir_ret(path):
            if path == context.user_data_pkgs:
                return False
            if path == context.root_prefix_pkgs:
                return True
            if path == context.root_prefix_envs:
                return True

        def mock_listdir_ret(path):
            if path == context.user_data_pkgs:
                return []
            if path == context.root_prefix_pkgs:
                return ["a/", "b/", "c/"]
            if path == context.root_prefix_envs:
                return ["a/", "b/", "c/"]

        mock_isdir.side_effect = mock_isdir_ret
        mock_listdir.side_effect = mock_listdir_ret

        _context_envs_dirs = context.envs_dirs
        _context_pkgs_dirs = context.pkgs_dirs

    assert len(caplog.records) == 2
    assert any([str(envs) in record.message for record in caplog.records])
    assert any([str(pkgs) in record.message for record in caplog.records])


def test_pkgs_envs_configured(
    testdata, propagate_conda_logger, caplog, unset_condarc_pkgs, monkeypatch, tmp_path
):
    """Test that the context uses legacy paths when `pkgs_dirs`/`envs_dirs` are set."""
    pkgs = str(tmp_path / "pkgs")
    envs = str(tmp_path / "envs")

    monkeypatch.setenv("CONDA_PKGS_DIRS", pkgs)
    monkeypatch.setenv("CONDA_ENVS_DIRS", envs)
    reset_context()

    assert set(context.pkgs_dirs) == set((pkgs,))
    assert set(context._pkgs_dirs) == set(context.pkgs_dirs)

    # When setting `envs_dirs`, the legacy behavior is to use
    # ~/.conda/envs, <root prefix>/envs,
    # and if running on windows, <user data dir>/conda/conda/envs.
    # Here we just check that the requested envs are a subset
    # of the actual envs returned.
    assert envs in set(context.envs_dirs)
    assert set(context._envs_dirs) <= set(context.envs_dirs)
