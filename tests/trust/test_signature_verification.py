# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import json
from pathlib import Path
from shutil import copyfile
from types import SimpleNamespace
from typing import Callable

import pytest
from pytest import MonkeyPatch
from pytest_mock import MockerFixture

from conda.base.constants import REPODATA_FN
from conda.base.context import context, reset_context
from conda.core.subdir_data import SubdirData
from conda.gateways.connection import HTTPError
from conda.models.channel import Channel
from conda.models.records import PackageRecord
from conda.testing import PathFactoryFixture
from conda.trust.constants import KEY_MGR_FILE
from conda.trust.signature_verification import SignatureError, _SignatureVerification

_TESTDATA = Path(__file__).parent / "testdata"
HTTP404 = HTTPError(response=SimpleNamespace(status_code=404))


@pytest.fixture
def av_data_dir(mocker: MockerFixture, path_factory: PathFactoryFixture) -> Path:
    av_data_dir = path_factory()
    av_data_dir.mkdir()
    mocker.patch(
        "conda.base.context.Context.av_data_dir",
        new_callable=mocker.PropertyMock,
        return_value=av_data_dir,
    )
    return av_data_dir


@pytest.fixture
def initial_trust_root(av_data_dir: Path, mocker: MockerFixture) -> dict:
    mocker.patch(
        "conda.trust.signature_verification.INITIAL_TRUST_ROOT",
        new=(initial_trust_root := json.loads((_TESTDATA / "1.root.json").read_text())),
    )
    return initial_trust_root


@pytest.fixture
def key_mgr(av_data_dir: Path, mocker: MockerFixture) -> dict:
    copyfile(key_mgr := _TESTDATA / "key_mgr.json", av_data_dir / KEY_MGR_FILE)
    return json.loads(key_mgr.read_text())


@pytest.fixture
def mock_fetch_channel_signing_data(mocker: MockerFixture) -> Callable[[...], None]:
    def inner(*values) -> None:
        mocker.patch(
            "conda.trust.signature_verification._SignatureVerification._fetch_channel_signing_data",
            side_effect=values,
        )

    return inner


@pytest.fixture
def sig_ver(monkeypatch: MonkeyPatch) -> _SignatureVerification:
    monkeypatch.setenv("CONDA_EXTRA_SAFETY_CHECKS", "true")
    monkeypatch.setenv("CONDA_SIGNING_METADATA_URL_BASE", url := "https://example.com")
    reset_context()
    assert context.extra_safety_checks
    assert context.signing_metadata_url_base == url

    sig_ver = _SignatureVerification()
    assert sig_ver.enabled
    return sig_ver


def test_trusted_root_no_new_metadata(
    av_data_dir: Path,
    initial_trust_root: dict,
    mock_fetch_channel_signing_data: Callable,
):
    # return HTTPError(404)
    mock_fetch_channel_signing_data(HTTP404)
    sig_ver = _SignatureVerification()

    # fetches 1.root.json (non-existant), fallback to initial_trust_root
    assert sig_ver.trusted_root == initial_trust_root
    assert sig_ver._fetch_channel_signing_data.call_count == 1


def test_trusted_root_2nd_metadata_on_disk_no_new_metadata_on_web(
    av_data_dir: Path,
    initial_trust_root: dict,
    mock_fetch_channel_signing_data: Callable,
):
    """
    Case where we cannot reach new root metadata online but have a newer version locally
    (2.root.json). Use this new version if it is valid.
    """
    # copy 2.root.json to disk
    copyfile(_TESTDATA / "2.root.json", path := av_data_dir / "2.root.json")

    # load 2.root.json
    root2 = json.loads(path.read_text())

    # return HTTPError(404)
    mock_fetch_channel_signing_data(HTTP404)
    sig_ver = _SignatureVerification()

    # fetches 3.root.json (non-existent), fallback to disk
    assert sig_ver.trusted_root == root2
    assert sig_ver._fetch_channel_signing_data.call_count == 1


def test_invalid_2nd_metadata_on_disk_no_new_metadata_on_web(
    av_data_dir: Path,
    initial_trust_root: dict,
    mock_fetch_channel_signing_data: Callable,
):
    """
    Unusual case:  We have an invalid 2.root.json on disk and no new metadata available
    online. In this case, our deliberate choice is to accept whatever on disk.
    """
    # copy 2.root_invalid.json to disk
    copyfile(_TESTDATA / "2.root_invalid.json", path := av_data_dir / "2.root.json")

    # load 2.root.json
    root2 = json.loads(path.read_text())

    # return HTTPError(404)
    mock_fetch_channel_signing_data(HTTP404)
    sig_ver = _SignatureVerification()

    # fetches 3.root.json (non-existent), fallback to disk
    assert sig_ver.trusted_root == root2
    assert sig_ver._fetch_channel_signing_data.call_count == 1


def test_2nd_root_metadata_from_web(
    av_data_dir: Path,
    initial_trust_root: dict,
    mock_fetch_channel_signing_data: Callable,
):
    """
    Test happy case where we get a new valid root metadata from the web
    """
    # load 2.root.json
    root2 = json.loads((_TESTDATA / "2.root.json").read_text())

    # return 2.root.json then HTTPError(404)
    mock_fetch_channel_signing_data(root2, HTTP404)
    sig_ver = _SignatureVerification()

    # fetches 2.root.json (valid) and 3.root.json (non-existant)
    assert sig_ver.trusted_root == root2
    assert sig_ver._fetch_channel_signing_data.call_count == 2


def test_3rd_root_metadata_from_web(
    av_data_dir: Path,
    initial_trust_root: dict,
    mock_fetch_channel_signing_data: Callable,
):
    """
    Test happy case where we get a chain of valid root metadata from the web
    """
    # load 2.root.json and 3.root.json
    root2 = json.loads((_TESTDATA / "2.root.json").read_text())
    root3 = json.loads((_TESTDATA / "3.root.json").read_text())

    # return 2.root.json, 3.root.json, then HTTPError(404)
    mock_fetch_channel_signing_data(root2, root3, HTTP404)
    sig_ver = _SignatureVerification()

    # fetches 2.root.json (valid), 3.root.json (valid), and 4.root.json (non-existant)
    assert sig_ver.trusted_root == root3
    assert sig_ver._fetch_channel_signing_data.call_count == 3


def test_single_invalid_signature_3rd_root_metadata_from_web(
    av_data_dir: Path,
    initial_trust_root: dict,
    mock_fetch_channel_signing_data: Callable,
):
    """
    Third root metadata retrieved from online has a bad signature. Test that we do not trust it.
    """
    # load 2.root.json and 3.root_invalid.json
    root2 = json.loads((_TESTDATA / "2.root.json").read_text())
    root3 = json.loads((_TESTDATA / "3.root_invalid.json").read_text())

    # return 2.root.json then 3.root.json
    mock_fetch_channel_signing_data(root2, root3)
    sig_ver = _SignatureVerification()

    # fetches 2.root.json (valid) and 3.root.json (invalid)
    assert sig_ver.trusted_root == root2
    assert sig_ver._fetch_channel_signing_data.call_count == 2


def test_trusted_root_no_new_key_mgr_online_key_mgr_is_on_disk(
    av_data_dir: Path,
    initial_trust_root: dict,
    key_mgr: dict,
    mock_fetch_channel_signing_data: Callable,
):
    """
    If we don't have a new key_mgr online, we use the one from disk
    """
    # return HTTPError(404)
    mock_fetch_channel_signing_data(HTTP404)
    sig_ver = _SignatureVerification()

    # fetches key_mgr.json (non-existent), fallback to disk (exists)
    assert sig_ver.key_mgr == key_mgr
    assert sig_ver._fetch_channel_signing_data.call_count == 1


def test_trusted_root_no_new_key_mgr_online_key_mgr_not_on_disk(
    av_data_dir: Path,
    initial_trust_root: dict,
    mock_fetch_channel_signing_data: Callable,
):
    """
    If we have no key_mgr online and no key_mgr on disk we don't have a key_mgr
    """
    # return HTTPError(404)
    mock_fetch_channel_signing_data(HTTP404)
    sig_ver = _SignatureVerification()

    # fetches key_mgr.json (non-existent), fallback to disk (non-existent)
    assert sig_ver.key_mgr is None
    assert sig_ver._fetch_channel_signing_data.call_count == 1


def test_trusted_root_new_key_mgr_online(
    av_data_dir: Path,
    initial_trust_root: dict,
    mock_fetch_channel_signing_data: Callable,
):
    """
    We have a new key_mgr online that can be verified against our trusted root.
    We should accept the new key_mgr
    """
    # load key_mgr.json
    key_mgr = json.loads((_TESTDATA / "key_mgr.json").read_text())

    # return key_mgr.json then HTTPError(404)
    mock_fetch_channel_signing_data(key_mgr, HTTP404)
    sig_ver = _SignatureVerification()

    # fetches key_mgr.json (valid) then 2.root.json (non-existant)
    assert sig_ver.key_mgr == key_mgr
    assert sig_ver._fetch_channel_signing_data.call_count == 2


def test_trusted_root_invalid_key_mgr_online_valid_on_disk(
    av_data_dir: Path,
    initial_trust_root: dict,
    key_mgr: dict,
    mock_fetch_channel_signing_data: Callable,
):
    """
    We have a new key_mgr online that can be verified against our trusted root.
    We should accept the new key_mgr

    Note:  This one does not fail with a warning and no side effects like the others.
    Instead, we raise a SignatureError
    """
    # load key_mgr_invalid.json
    key_mgr = json.loads((_TESTDATA / "key_mgr_invalid.json").read_text())

    # return key_mgr_invalid.json then HTTPError(404)
    mock_fetch_channel_signing_data(key_mgr, HTTP404)
    sig_ver = _SignatureVerification()

    # fetches key_mgr.json (invalid) then 2.root.json (non-existant)
    with pytest.raises(SignatureError):
        sig_ver.key_mgr
    assert sig_ver._fetch_channel_signing_data.call_count == 2


def test_signature_verification_not_enabled(
    av_data_dir: Path,
    initial_trust_root: dict,
    key_mgr: dict,
    monkeypatch: MonkeyPatch,
):
    sig_ver = _SignatureVerification()

    monkeypatch.setenv("CONDA_EXTRA_SAFETY_CHECKS", "false")
    monkeypatch.setenv("CONDA_SIGNING_METADATA_URL_BASE", "")
    reset_context()
    assert not context.extra_safety_checks
    assert not context.signing_metadata_url_base

    _SignatureVerification.cache_clear()
    assert not sig_ver.enabled

    monkeypatch.setenv("CONDA_EXTRA_SAFETY_CHECKS", "true")
    monkeypatch.setenv("CONDA_SIGNING_METADATA_URL_BASE", "")
    reset_context()
    assert context.extra_safety_checks
    assert not context.signing_metadata_url_base

    _SignatureVerification.cache_clear()
    assert not sig_ver.enabled


@pytest.mark.parametrize(
    "package,trusted",
    [
        ("_anaconda_depends-2018.12-py27_0.tar.bz2", True),
        ("zstd-1.3.7-h0b5b093_0.conda", True),
        ("zstd-1.4.4-h0b5b093_3.conda", True),
        # bad key_mgr.json pubkey
        ("broken-0.0.1-broken.tar.bz2", False),
        # bad signature
        ("broken-0.0.1-broken.conda", False),
    ],
)
def test_signature_verification(
    sig_ver: _SignatureVerification,
    mocker: MockerFixture,
    path_factory: PathFactoryFixture,
    package: str,
    trusted: bool,
):
    # mock out the cache path base
    cache_path_base = path_factory()
    cache_path_base.mkdir()
    mocker.patch(
        "conda.core.subdir_data.SubdirData.cache_path_base",
        new_callable=mocker.PropertyMock,
        return_value=cache_path_base,
    )

    # load repodata.json with signatures
    src = _TESTDATA / "repodata_short_signed_sample.json"
    repodata = json.loads(src.read_text())

    # copy repodata.json to cache path
    dst = cache_path_base / (subdir := repodata["info"]["subdir"]) / REPODATA_FN
    dst.parent.mkdir(parents=True, exist_ok=True)
    copyfile(src, dst)

    # create record to verify
    record = PackageRecord.from_objects(
        repodata["packages.conda" if package.endswith(".conda") else "packages"][
            package
        ],
        channel=Channel.from_value(f"file://{cache_path_base}/{subdir}"),
        fn=package,
    )

    # ensure signature is valid
    sig_ver.verify(REPODATA_FN, record)

    if trusted:
        assert "(package metadata is TRUSTED)" in record.metadata
    else:
        assert "(package metadata is UNTRUSTED)" in record.metadata
