# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
from logging import getLogger
from pathlib import Path
from unittest.mock import patch

import pytest
from requests import HTTPError

from conda.auxlib.compat import Utf8NamedTemporaryFile
from conda.common.compat import ensure_binary
from conda.common.url import path_to_url
from conda.exceptions import CondaExitZero
from conda.gateways.anaconda_client import remove_binstar_token, set_binstar_token
from conda.gateways.connection.session import CondaHttpAuth, CondaSession
from conda.gateways.disk.delete import rm_rf
from conda.testing import TmpEnvFixture
from conda.testing.gateways.fixtures import MINIO_EXE
from conda.testing.integration import env_var

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
def test_s3_server(minio_s3_server, tmp_env: TmpEnvFixture):
    import boto3
    from botocore.client import Config

    endpoint, bucket_name = minio_s3_server.server_url.rsplit("/", 1)
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
                with tmp_env(
                    "--override-channels",
                    f"--channel=s3://{bucket_name}",
                    "--download-only",
                    "--no-deps",  # this fake repo only includes the zlib tarball
                    "zlib",
                ):
                    # we just want to run tmp_env and cleanup after
                    pass
