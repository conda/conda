# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import hashlib
from logging import getLogger
from pathlib import Path
from unittest.mock import patch

import pytest
from requests import HTTPError

from conda.auxlib.compat import Utf8NamedTemporaryFile
from conda.base.context import reset_context
from conda.common.compat import ensure_binary
from conda.common.io import env_vars
from conda.common.url import path_to_url
from conda.exceptions import CondaExitZero
from conda.gateways.anaconda_client import remove_binstar_token, set_binstar_token
from conda.gateways.connection.download import download_inner
from conda.gateways.connection.session import (
    CondaHttpAuth,
    CondaSession,
    get_channel_name_from_url,
    get_session,
    get_session_storage_key,
)
from conda.gateways.disk.delete import rm_rf
from conda.plugins.types import ChannelAuthBase
from conda.testing.gateways.fixtures import MINIO_EXE
from conda.testing.integration import make_temp_env

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
    endpoint = minio_s3_server.endpoint
    bucket_name = minio_s3_server.name
    channel_dir = Path(__file__).parent.parent / "data" / "conda_format_repo"

    minio_s3_server.populate_bucket(endpoint, bucket_name, channel_dir)

    inner_s3_test(endpoint, bucket_name)


@pytest.mark.integration
def test_s3_server_with_mock(package_server):
    """
    Use boto3 to fetch from a mock s3 server pointing at the test package
    repository. This works since conda only GET's against s3 and s3 is http.
    """
    host, port = package_server.getsockname()
    endpoint_url = f"http://{host}:{port}"
    bucket_name = "test"

    inner_s3_test(endpoint_url, bucket_name)


def inner_s3_test(endpoint_url, bucket_name):
    """
    Called by functions that build a populated s3 server.

    (Not sure how to accomplish the same thing with pytest parametrize)
    """
    import boto3
    from botocore.client import Config

    # We patch the default kwargs values in boto3.session.Session.resource(...)
    # which is used in conda.gateways.connection.s3.S3Adapter to initialize the S3
    # connection; otherwise it would default to a real AWS instance
    patched_defaults = (
        "us-east-1",  # region_name
        None,  # api_version
        True,  # use_ssl
        None,  # verify
        endpoint_url,  # endpoint_url
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
            with env_vars(
                {"CONDA_USE_ONLY_TAR_BZ2": "True", "CONDA_SUBDIR": "linux-64"}
            ):
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


def test_get_session_returns_default():
    """
    Tests to make sure that our session manager returns a regular
    CondaSession object when no other session classes are registered.
    """
    url = "https://localhost/test"
    session_obj = get_session(url)
    get_session.cache_clear()  # ensuring cleanup

    assert type(session_obj) is CondaSession


def test_get_session_with_channel_settings(mocker):
    """
    Tests to make sure the get_session function works when ``channel_settings``
    have been set on the context object.
    """
    mocker.patch(
        "conda.gateways.connection.session.get_channel_name_from_url",
        return_value="defaults",
    )
    mock_context = mocker.patch("conda.gateways.connection.session.context")
    mock_context.channel_settings = ({"channel": "defaults", "auth": "dummy_one"},)

    url = "https://localhost/test1"

    session_obj = get_session(url)
    get_session.cache_clear()  # ensuring cleanup

    assert type(session_obj) is CondaSession

    # For session objects with a custom auth handler it will not be set to CondaHttpAuth
    assert type(session_obj.auth) is not CondaHttpAuth

    # Make sure we tried to retrieve our auth handler in this function
    assert (
        mocker.call("dummy_one")
        in mock_context.plugin_manager.get_auth_handler.mock_calls
    )


@pytest.mark.parametrize(
    "channel_settings_url, expect_match",
    [
        pytest.param(
            "https://repo.some-hostname.com/channel-name",
            True,
            id="exact-url",
        ),
        pytest.param(
            "https://repo.some-hostname.com/*",
            True,
            id="url-prefix",
        ),
        pytest.param(
            "https://repo.some-hostname.com/another-channel",
            False,
            id="no-match",
        ),
        pytest.param(
            "https://*.com/*",
            True,
            id="wildcard-match-same-schema",
        ),
        pytest.param(
            "http://*.com/*",
            False,
            id="wildcard-no-match-different-scheme",
        ),
        pytest.param(
            "*",
            False,
            id="wildcard-no-match-missing-scheme",
        ),
    ],
)
def test_get_session_with_url_pattern(mocker, channel_settings_url, expect_match):
    """
    For channels specified by URL, we can configure channel_settings with a URL containing
    either an exact URL match or with a glob-like pattern. In the latter case we require the
    HTTP schemes to be identical.
    """
    channel_url = "https://repo.some-hostname.com/channel-name"
    mocker.patch(
        "conda.gateways.connection.session.get_channel_name_from_url",
        return_value=channel_url,
    )
    mock_context = mocker.patch("conda.gateways.connection.session.context")
    mock_context.channel_settings = (
        {"channel": channel_settings_url, "auth": "dummy_one"},
    )

    session_obj = get_session(channel_url)
    get_session.cache_clear()  # ensuring cleanup

    # In all cases, the returned type is CondaSession
    assert type(session_obj) is CondaSession

    if expect_match:
        # For session objects with a custom auth handler it will not be set to CondaHttpAuth
        assert type(session_obj.auth) is not CondaHttpAuth

        # Make sure we tried to retrieve our auth handler in this function
        assert (
            mocker.call("dummy_one")
            in mock_context.plugin_manager.get_auth_handler.mock_calls
        )
    else:
        # If we do not match, then we default to CondaHttpAuth
        assert type(session_obj.auth) is CondaHttpAuth

        # We have not tried to retrieve our auth handler
        assert not mock_context.plugin_manager.get_auth_handler.mock_calls


def test_get_session_with_channel_settings_multiple(mocker):
    """
    Tests to make sure the get_session function works when ``channel_settings``
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

    session_obj_one = get_session(url_one)
    session_obj_two = get_session(url_two)

    get_session.cache_clear()  # ensuring cleanup

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


def test_get_session_with_channel_settings_no_handler(mocker):
    """
    Tests to make sure the get_session function works when ``channel_settings``
    have been set on the context objet. This test does not find a matching auth
    handler.
    """
    mocker.patch(
        "conda.gateways.connection.session.get_channel_name_from_url",
        return_value="defaults",
    )
    mock = mocker.patch(
        "conda.plugins.manager.CondaPluginManager.get_auth_handler",
        return_value=None,
    )
    mocker.patch(
        "conda.base.context.Context.channel_settings",
        new_callable=mocker.PropertyMock,
        return_value=({"channel": "defaults", "auth": "dummy_two"},),
    )

    url = "https://localhost/test2"

    session_obj = get_session(url)
    get_session.cache_clear()  # ensuring cleanup

    assert type(session_obj) is CondaSession

    # For sessions without a custom auth handler, this will be the default auth handler
    assert type(session_obj.auth) is CondaHttpAuth

    # Make sure we tried to retrieve our auth handler in this function
    assert mocker.call("dummy_two") in mock.mock_calls


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


def test_accept_range_none(package_server, tmp_path):
    """
    Ensure when "accept-ranges" is "none" we are able to truncate a partially downloaded file.
    """
    test_content = "test content test content test content"

    host, port = package_server.getsockname()
    url = f"http://{host}:{port}/none-accept-ranges"
    expected_sha256 = hashlib.sha256(test_content.encode("utf-8")).hexdigest()

    # assert range request not supported
    response = CondaSession().get(url, headers={"Range": "bytes=10-"})
    assert response.status_code == 200

    tmp_dir = tmp_path / "sub"
    tmp_dir.mkdir()
    filename = "test-file"

    partial_file = Path(tmp_dir / f"{filename}.partial")
    complete_file = Path(tmp_dir / filename)

    partial_file.write_text(test_content[:12])

    download_inner(url, complete_file, "md5", expected_sha256, 38, lambda x: x)

    assert complete_file.read_text() == test_content
    assert not partial_file.exists()

    # What if the partial file was wrong? (Since this endpoint always returns
    # 200 not 206, this doesn't test complete-download, then hash mismatch.
    # Another test in test_fetch.py asserts that we check the hash.)
    complete_file.unlink()
    partial_file.write_text("wrong content")

    download_inner(url, complete_file, None, expected_sha256, len(test_content), None)

    assert complete_file.read_text() == test_content
    assert not partial_file.exists()

