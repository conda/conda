# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from __future__ import annotations

import os
from argparse import Namespace
from contextlib import nullcontext
from itertools import chain
from os.path import abspath, join
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING
from unittest import mock

import pytest

from conda.auxlib.collection import AttrDict
from conda.auxlib.ish import dals
from conda.base.constants import (
    DEFAULT_AGGRESSIVE_UPDATE_PACKAGES,
    DEFAULT_CHANNELS,
    ChannelPriority,
    PathConflict,
)
from conda.base.context import (
    channel_alias_validation,
    context,
    default_python_validation,
    env_name,
    reset_context,
    validate_channels,
    validate_prefix_name,
)
from conda.common.configuration import (
    DefaultValueRawParameter,
    ValidationError,
    YamlRawParameter,
)
from conda.common.path import expand, win_path_backout
from conda.common.serialize import yaml
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
    from collections.abc import Iterator

    from pytest import MonkeyPatch

    from conda.testing import PathFactoryFixture
    from conda.testing.fixtures import CondaCLIFixture, TmpEnvFixture


def test_migrated_custom_channels(context_testdata: None):
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


def test_old_channel_alias(context_testdata: None):
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


def test_signing_metadata_url_base(context_testdata: None):
    SIGNING_URL_BASE = "https://conda.example.com/pkgs"
    string = f"signing_metadata_url_base: {SIGNING_URL_BASE}"
    reset_context()
    rd = {
        "testdata": YamlRawParameter.make_raw_parameters("testdata", yaml.loads(string))
    }
    context._set_raw_data(rd)
    assert context.signing_metadata_url_base == SIGNING_URL_BASE


def test_signing_metadata_url_base_empty_default_channels(context_testdata: None):
    string = dals(
        """
        default_channels: []
        """
    )
    reset_context()
    rd = {
        "testdata": YamlRawParameter.make_raw_parameters("testdata", yaml.loads(string))
    }
    context._set_raw_data(rd)
    assert len(context.default_channels) == 0
    assert context.signing_metadata_url_base is None


def test_client_ssl_cert(context_testdata: None):
    string = dals(
        """
        client_ssl_cert_key: /some/key/path
        """
    )
    reset_context()
    rd = {
        "testdata": YamlRawParameter.make_raw_parameters("testdata", yaml.loads(string))
    }
    context._set_raw_data(rd)
    pytest.raises(ValidationError, context.validate_configuration)


def test_conda_envs_path(context_testdata: None):
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


def test_custom_multichannels(context_testdata: None):
    assert context.custom_multichannels["michele"] == (
        Channel("passion"),
        Channel("learn_from_every_thing"),
    )


def test_proxy_servers(context_testdata: None):
    assert context.proxy_servers["http"] == "http://user:pass@corp.com:8080"
    assert context.proxy_servers["https"] is None
    assert context.proxy_servers["ftp"] is None
    assert context.proxy_servers["sftp"] == ""
    assert context.proxy_servers["ftps"] == "False"
    assert context.proxy_servers["rsync"] == "false"


def test_conda_build_root_dir(context_testdata: None):
    assert context.conda_build["root-dir"] == "/some/test/path"


@pytest.mark.parametrize("path_conflict", PathConflict.__members__)
def test_clobber_enum(monkeypatch: MonkeyPatch, path_conflict: str) -> None:
    monkeypatch.setenv("CONDA_PATH_CONFLICT", path_conflict)
    reset_context()
    assert context.path_conflict == PathConflict(path_conflict)


def test_context_parameter_map(context_testdata: None):
    parameters = list(context.list_parameters())
    mapped = [name for names in context.category_map.values() for name in names]

    # ignore anaconda-anon-usage's context monkeypatching
    if "anaconda_anon_usage" in parameters:
        parameters.remove("anaconda_anon_usage")
    if "anaconda_anon_usage" in mapped:
        mapped.remove("anaconda_anon_usage")

    assert not set(parameters).difference(mapped)
    assert len(parameters) == len(mapped)


def test_context_parameters_have_descriptions(context_testdata: None):
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


def test_context_override_with_reset(monkeypatch):
    from conda.base.context import context, reset_context

    original = context.add_pip_as_python_dependency
    with context._override("add_pip_as_python_dependency", False):
        assert context.add_pip_as_python_dependency is False
        monkeypatch.setenv("CONDA_ADD_PIP_AS_PYTHON_DEPENDENCY", "True")
        reset_context()
        assert context.add_pip_as_python_dependency is False
    assert context.add_pip_as_python_dependency is original


def test_local_build_root_custom_rc(
    context_testdata: None,
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


def test_default_target_is_root_prefix(context_testdata: None):
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


def test_channel_priority(context_testdata: None):
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


def test_channels_empty(context_testdata: None):
    """Test when no channels provided in cli and no condarc config is present."""
    reset_context(())
    assert context.channels == ()


def test_channels_defaults_condarc(context_testdata: None):
    """Test when no channels provided in cli, but some in condarc."""
    reset_context(())
    string = dals(
        """
        channels: ['defaults', 'conda-forge']
        """
    )
    rd = {
        "testdata": YamlRawParameter.make_raw_parameters("testdata", yaml.loads(string))
    }
    context._set_raw_data(rd)
    assert context.channels == ("defaults", "conda-forge")


def test_specify_channels_cli_not_adding_defaults_no_condarc(context_testdata: None):
    """
    When the channel haven't been specified in condarc, 'defaults'
    should NOT be present when specifying channel in the cli.

    See https://github.com/conda/conda/issues/14217 for context.
    """
    reset_context((), argparse_args=AttrDict(channel=["conda-forge"]))
    assert context.channels == ("conda-forge",)


def test_specify_channels_cli_condarc(context_testdata: None):
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
        "testdata": YamlRawParameter.make_raw_parameters("testdata", yaml.loads(string))
    }
    context._set_raw_data(rd)
    assert context.channels == ("defaults", "conda-forge")


def test_specify_different_channels_cli_condarc(context_testdata: None):
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
        "testdata": YamlRawParameter.make_raw_parameters("testdata", yaml.loads(string))
    }
    context._set_raw_data(rd)
    assert context.channels == ("conda-forge", "other")


def test_specify_same_channels_cli_as_in_condarc(context_testdata: None):
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
        "testdata": YamlRawParameter.make_raw_parameters("testdata", yaml.loads(string))
    }
    context._set_raw_data(rd)
    assert context.channels == ("conda-forge",)


def test_expandvars(context_testdata: None):
    """Environment variables should be expanded in settings that have expandvars=True."""

    def _get_expandvars_context(attr, config_expr, env_value):
        with mock.patch.dict(os.environ, {"TEST_VAR": env_value}):
            reset_context(())
            string = f"{attr}: {config_expr}"
            rd = {
                "testdata": YamlRawParameter.make_raw_parameters(
                    "testdata", yaml.loads(string)
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


def test_channel_settings(context_testdata: None):
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
        mock.patch("conda.gateways.disk.create.first_writable_envs_dir") as mock_one,
        mock.patch("conda.base.context.locate_prefix_by_name") as mock_two,
    ):
        mock_one.side_effect = [mock_return_values[0]]
        mock_two.side_effect = [mock_return_values[1]]

        if isinstance(expected, CondaValueError):
            with pytest.raises(CondaValueError) as exc, pytest.deprecated_call():
                validate_prefix_name(prefix, ctx, allow_base=allow_base)

            # We fuzzy match the error message here. Doing this exactly is not important
            assert str(expected) in str(exc)

        else:
            with pytest.deprecated_call():
                actual = validate_prefix_name(prefix, ctx, allow_base=allow_base)
            assert actual == str(expected)


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


@pytest.mark.parametrize(
    "channels,expected_channels",
    [
        (
            ("defaults", "https://beta.conda.anaconda.org/conda-test", "conda-forge"),
            ("defaults", "https://beta.conda.anaconda.org/conda-test", "conda-forge"),
        ),
        (
            (
                "defaults",
                "https://beta.conda.anaconda.org/conda-test",
                "conda-forge",
                None,
            ),
            ("defaults", "https://beta.conda.anaconda.org/conda-test", "conda-forge"),
        ),
        (
            (None,),
            (),
        ),
        (
            (""),
            (),
        ),
        (
            (),
            (),
        ),
    ],
)
def test_validate_channels(channels: Iterator[str], expected_channels: tuple[str, ...]):
    validated_channels = validate_channels(channels)
    assert expected_channels == validated_channels


def test_default_activation_prefix(
    conda_cli: CondaCLIFixture,
    tmp_env: TmpEnvFixture,
    monkeypatch: MonkeyPatch,
):
    """Test that the default_activation_prefix returns the correct prefix.

    context.default_activation_env can either be a name or a prefix path, so we check
    that in either case, the context.default_activation_prefix is a path.
    """
    key = "CONDA_DEFAULT_ACTIVATION_ENV"

    with tmp_env() as prefix:
        name = env_name(prefix)
        monkeypatch.setenv(key, str(context.root_prefix))
        reset_context()
        assert prefix != context.default_activation_prefix

        monkeypatch.setenv(key, str(prefix))
        reset_context()
        assert prefix == context.default_activation_prefix

        monkeypatch.setenv(key, str(name))
        reset_context()
        assert prefix == context.default_activation_prefix


PYTHON_SPEC = "python"
ZLIB_URL = "https://repo.anaconda.com/pkgs/main/linux-64/zlib-1.2.13-h5eee18b_1.conda"


@pytest.mark.parametrize(
    "context_packages,expected_packages",
    (
        (tuple(), tuple()),
        ((PYTHON_SPEC,), (PYTHON_SPEC,)),
        ((PYTHON_SPEC, ZLIB_URL), (PYTHON_SPEC,)),
    ),
)
def test_create_default_packages(
    monkeypatch: MonkeyPatch,
    context_packages: tuple[str, ...],
    expected_packages: tuple[str, ...],
):
    """Ensure that the `create_default_packages` config only returns valid package
    specs, and no explicit packages."""
    monkeypatch.setenv("CONDA_CREATE_DEFAULT_PACKAGES", f"{','.join(context_packages)}")
    reset_context()

    create_default_packages = context.create_default_packages
    assert create_default_packages == expected_packages


def test_create_default_packages_will_warn_for_explicit_packages(
    monkeypatch: MonkeyPatch,
):
    """This test will ensure that the context object emits a warning whenever an explicit
    package is in the `create_default_packages` setting. Further, this property will ensure
    that no invalid packages are returned to the caller.
    """
    # Add an explicit package and a valid package spec to `create_default_packages`. We
    # expect this to:
    #   * emit a warning about the explicit package and,
    #   * only return the valid (python) package
    monkeypatch.setenv("CONDA_CREATE_DEFAULT_PACKAGES", f"{ZLIB_URL},{PYTHON_SPEC}")
    reset_context()

    with pytest.warns(
        UserWarning,
        match=(
            rf"Ignoring invalid packages in `create_default_packages`: \n"
            rf"  - {ZLIB_URL}\n"
            rf"\n"
            rf"Explicit package are not allowed.+"
        ),
    ):
        # Ensure only valid packages are returned
        assert context.create_default_packages == (PYTHON_SPEC,)


def test_export_platforms(monkeypatch: MonkeyPatch):
    reset_context([])
    assert context.export_platforms == (context.subdir,)

    monkeypatch.setenv("CONDA_EXPORT_PLATFORMS", "linux-64,osx-64")
    reset_context()
    assert context.export_platforms == ("linux-64", "osx-64")

    monkeypatch.setenv("CONDA_EXPORT_PLATFORMS", "linux-64,osx-64,win-64")
    reset_context()
    assert context.export_platforms == ("linux-64", "osx-64", "win-64")

    reset_context(argparse_args=Namespace(export_platforms=["linux-32"]))
    assert context.export_platforms == (
        "linux-32",
        "linux-64",
        "osx-64",
        "win-64",
    )

    reset_context(
        argparse_args=Namespace(
            export_platforms=["linux-32"],
            override_platforms=True,
        )
    )
    assert context.export_platforms == ("linux-32",)


@pytest.mark.parametrize(
    "function,raises",
    [("error_upload_url", TypeError)],
)
def test_deprecations(function: str, raises: type[Exception] | None) -> None:
    raises_context = pytest.raises(raises) if raises else nullcontext()
    with pytest.deprecated_call(), raises_context:
        getattr(context, function)()


def test_custom_multichannels_overrides_default_channels(reset_conda_context: None):
    # default_channels
    reset_context()
    default_channels = ["default_channels_1", "default_channels_2"]
    raw_data = {"default_channels": default_channels}
    rd = {
        "testdata": DefaultValueRawParameter.make_raw_parameters("testdata", raw_data)
    }
    context._set_raw_data(rd)

    assert [channel.name for channel in context.default_channels] == default_channels
    assert [
        channel.name for channel in context.custom_multichannels["defaults"]
    ] == default_channels

    # custom_channels.defaults
    reset_context()
    custom_channels = ["custom_channel_1", "custom_channel_2"]
    raw_data = {"custom_multichannels": {"defaults": custom_channels}}
    rd = {
        "testdata": DefaultValueRawParameter.make_raw_parameters("testdata", raw_data)
    }
    context._set_raw_data(rd)

    assert [channel.name for channel in context.default_channels] == custom_channels
    assert [
        channel.name for channel in context.custom_multichannels["defaults"]
    ] == custom_channels

    # custom_channels.defaults overrides default_channels
    reset_context()
    raw_data = {
        "default_channels": default_channels,
        "custom_multichannels": {"defaults": custom_channels},
    }
    rd = {
        "testdata": DefaultValueRawParameter.make_raw_parameters("testdata", raw_data)
    }
    context._set_raw_data(rd)

    assert [channel.name for channel in context.default_channels] == custom_channels
    assert [
        channel.name for channel in context.custom_multichannels["defaults"]
    ] == custom_channels
