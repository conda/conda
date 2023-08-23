# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from logging import getLogger
from pathlib import Path
from unittest.mock import patch

import pytest
from requests import HTTPError

from conda.auxlib.compat import Utf8NamedTemporaryFile
from conda.base.context import reset_context
from conda.common.compat import ensure_binary
from conda.common.url import path_to_url
from conda.exceptions import CondaExitZero
from conda.gateways.anaconda_client import remove_binstar_token, set_binstar_token
from conda.gateways.connection.session import (
    CondaHttpAuth,
    CondaSession,
    get_channel_name_from_url,
    get_session_storage_key,
    session_manager,
)
from conda.gateways.disk.delete import rm_rf
from conda.plugins.types import ChannelAuthBase
from conda.testing.gateways.fixtures import MINIO_EXE
from conda.testing.integration import env_var, make_temp_env

log = getLogger(__name__)


def test_add_binstar_token():
    try:
        # # token already exists in url, don't add anything
        # url = "https://conda.anaconda.org/t/dont-add-a-token/biopython/linux-64/repodata.json"
        # assert CondaHttpAuth.add_binstar_token(url) == url
        #
        # # even if a token is there, don't use it
        set_binstar_token("https://api.anaconda.test", "tk-abacadaba-1029384756")
        # url = "https://conda.anaconda.test/t/dont-add-a-token/biopython/linux-64/repodata.json"
        # assert CondaHttpAuth.add_binstar_token(url) == url

        # now test adding the token
        url = "https://conda.anaconda.test/biopython/linux-64/repodata.json"
        new_url = "https://conda.anaconda.test/t/tk-abacadaba-1029384756/biopython/linux-64/repodata.json"
        assert CondaHttpAuth.add_binstar_token(url) == new_url
    finally:
        remove_binstar_token("https://api.anaconda.test")


def test_local_file_adapter_404():
    session = CondaSession()
    test_path = "file:///some/location/doesnt/exist"
    r = session.get(test_path)
    with pytest.raises(HTTPError):
        r.raise_for_status()
    assert r.status_code == 404
    assert r.json()["path"] == test_path[len("file://") :]


def test_local_file_adapter_200():
    test_path = None
    try:
        with Utf8NamedTemporaryFile(delete=False) as fh:
            test_path = fh.name
            fh.write(ensure_binary('{"content": "file content"}'))

        test_url = path_to_url(test_path)
        session = CondaSession()
        r = session.get(test_url)
        r.raise_for_status()
        assert r.status_code == 200
        assert r.json()["content"] == "file content"
    finally:
        if test_path is not None:
            rm_rf(test_path)


@pytest.mark.skipif(MINIO_EXE is None, reason="Minio server not available")
@pytest.mark.integration
def test_s3_server(minio_s3_server):
    import boto3
    from botocore.client import Config

    endpoint = minio_s3_server.endpoint
    bucket_name = minio_s3_server.name
    channel_dir = Path(__file__).parent.parent / "data" / "conda_format_repo"

    minio_s3_server.populate_bucket(endpoint, bucket_name, channel_dir)

    # We patch the default kwargs values in boto3.session.Session.resource(...)
    # which is used in conda.gateways.connection.s3.S3Adapter to initialize the S3
    # connection; otherwise it would default to a real AWS instance
    patched_defaults = (
        "us-east-1",  # region_name
        None,  # api_version
        True,  # use_ssl
        None,  # verify
        endpoint,  # endpoint_url
        "minioadmin",  # aws_access_key_id
        "minioadmin",  # aws_secret_access_key
        None,  # aws_session_token
        Config(signature_version="s3v4"),  # config
    )
    with pytest.raises(CondaExitZero):
        with patch.object(
            boto3.session.Session.resource, "__defaults__", patched_defaults
        ):
            # the .conda files in this repo are somehow corrupted
            with env_var("CONDA_USE_ONLY_TAR_BZ2", "True"):
                with make_temp_env(
                    "--override-channels",
                    f"--channel=s3://{bucket_name}",
                    "--download-only",
                    "--no-deps",  # this fake repo only includes the zlib tarball
                    "zlib",
                    use_exception_handler=False,
                    no_capture=True,
                ):
                    # we just want to run make_temp_env and cleanup after
                    pass


def test_session_manager_returns_default():
    """
    Tests to make sure that our session manager returns a regular
    CondaSession object when no other session classes are registered.
    """
    url = "https://localhost/test"
    session_obj = session_manager(url)
    session_manager.cache_clear()  # ensuring cleanup

    assert type(session_obj) is CondaSession


def test_session_manager_with_channel_settings(mocker):
    """
    Tests to make sure the session_manager function works when ``channel_settings``
    have been set on the context object.
    """
    mocker.patch(
        "conda.gateways.connection.session.get_channel_name_from_url",
        return_value="defaults",
    )
    mock_context = mocker.patch("conda.gateways.connection.session.context")
    mock_context.channel_settings = ({"channel": "defaults", "auth": "dummy_one"},)

    url = "https://localhost/test1"

    session_obj = session_manager(url)
    session_manager.cache_clear()  # ensuring cleanup

    assert type(session_obj) is CondaSession

    # For session objects with a custom auth handler it will not be set to CondaHttpAuth
    assert type(session_obj.auth) is not CondaHttpAuth

    # Make sure we tried to retrieve our auth handler in this function
    assert (
        mocker.call("dummy_one")
        in mock_context.plugin_manager.get_auth_handler.mock_calls
    )


def test_session_manager_with_channel_settings_multiple(mocker):
    """
    Tests to make sure the session_manager function works when ``channel_settings``
    have been set on the context object and there exists more than one channel
    configured using the same type of auth handler.

    It's important that our cache keys are set up so that we do not return the
    same CondaSession object for these two different channels.
    """
    mocker.patch(
        "conda.gateways.connection.session.get_channel_name_from_url",
        side_effect=["channel_one", "channel_two"],
    )
    mock_context = mocker.patch("conda.gateways.connection.session.context")
    mock_context.channel_settings = (
        {"channel": "channel_one", "auth": "dummy_one"},
        {"channel": "channel_two", "auth": "dummy_one"},
    )
    mock_context.plugin_manager.get_auth_handler.return_value = ChannelAuthBase

    url_one = "https://localhost/test1"
    url_two = "https://localhost/test2"

    session_obj_one = session_manager(url_one)
    session_obj_two = session_manager(url_two)

    session_manager.cache_clear()  # ensuring cleanup

    assert session_obj_one is not session_obj_two

    storage_key_one = get_session_storage_key(session_obj_one.auth)
    storage_key_two = get_session_storage_key(session_obj_two.auth)

    assert storage_key_one in session_obj_one._thread_local.sessions
    assert storage_key_two in session_obj_one._thread_local.sessions

    assert type(session_obj_one) is CondaSession
    assert type(session_obj_two) is CondaSession

    # For session objects with a custom auth handler it will not be set to CondaHttpAuth
    assert type(session_obj_one.auth) is not CondaHttpAuth
    assert type(session_obj_two.auth) is not CondaHttpAuth

    # Make sure we tried to retrieve our auth handler in this function
    assert (
        mocker.call("dummy_one")
        in mock_context.plugin_manager.get_auth_handler.mock_calls
    )


def test_session_manager_with_channel_settings_no_handler(mocker):
    """
    Tests to make sure the session_manager function works when ``channel_settings``
    have been set on the context objet. This test does not find a matching auth
    handler.
    """
    mocker.patch(
        "conda.gateways.connection.session.get_channel_name_from_url",
        return_value="defaults",
    )
    mock_context = mocker.patch("conda.gateways.connection.session.context")
    mock_context.plugin_manager.get_auth_handler.return_value = None
    mock_context.channel_settings = ({"channel": "defaults", "auth": "dummy_two"},)

    url = "https://localhost/test2"

    session_obj = session_manager(url)
    session_manager.cache_clear()  # ensuring cleanup

    assert type(session_obj) is CondaSession

    # For sessions without a custom auth handler, this will be the default auth handler
    assert type(session_obj.auth) is CondaHttpAuth

    # Make sure we tried to retrieve our auth handler in this function
    assert (
        mocker.call("dummy_two")
        in mock_context.plugin_manager.get_auth_handler.mock_calls
    )


@pytest.mark.parametrize(
    "url, channels, expected",
    (
        (
            "https://repo.anaconda.com/pkgs/main/linux-64/test-package-0.1.0.conda",
            ("defaults",),
            "defaults",
        ),
        (
            "https://conda.anaconda.org/conda-forge/linux-64/test-package-0.1.0.tar.bz2",
            ("conda-forge", "defaults"),
            "conda-forge",
        ),
        (
            "http://localhost/noarch/test-package-0.1.0.conda",
            ("defaults", "http://localhost"),
            "http://localhost",
        ),
        ("http://localhost", ("defaults",), "http://localhost"),
    ),
)
def test_get_channel_name_from_url(url, channels, expected, monkeypatch):
    """
    Makes sure we return the correct value from the ``get_channel_name_from_url`` function.
    """
    monkeypatch.setenv("CONDA_CHANNELS", ",".join(channels))
    reset_context()
    channel_name = get_channel_name_from_url(url)

    assert expected == channel_name
