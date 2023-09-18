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

from conda.base.context import context, reset_context
from conda.gateways.connection import HTTPError
from conda.trust.constants import KEY_MGR_FILE
from conda.trust.signature_verification import SignatureError, _SignatureVerification

_TESTDATA = Path(__file__).parent / "testdata"
HTTP404 = HTTPError(response=SimpleNamespace(status_code=404))


@pytest.fixture
def av_data_dir(mocker: MockerFixture, tmp_path: Path) -> Path:
    mocker.patch(
        "conda.base.context.Context.av_data_dir",
        new_callable=mocker.PropertyMock,
        return_value=tmp_path,
    )
    return tmp_path


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


def test_trusted_root_no_new_metadata(
    av_data_dir: Path,
    initial_trust_root: dict,
    mock_fetch_channel_signing_data: Callable,
):
    mock_fetch_channel_signing_data(HTTP404)
    sig_ver = _SignatureVerification()

    # Compare sig_ver's view on INITIAL_TRUST_ROOT to the contents of testdata/1.root.json
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
    copyfile(_TESTDATA / "2.root.json", path := av_data_dir / "2.root.json")
    root2 = json.loads(path.read_text())

    mock_fetch_channel_signing_data(HTTP404)
    sig_ver = _SignatureVerification()

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
    copyfile(_TESTDATA / "2.root_invalid.json", path := av_data_dir / "2.root.json")
    root2 = json.loads(path.read_text())

    mock_fetch_channel_signing_data(root2)
    sig_ver = _SignatureVerification()

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
    root2 = json.loads((_TESTDATA / "2.root.json").read_text())

    mock_fetch_channel_signing_data(root2)
    sig_ver = _SignatureVerification()

    # One call for 2.root.json and 3.root.json (non-existant)
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
    root2 = json.loads((_TESTDATA / "2.root.json").read_text())
    root3 = json.loads((_TESTDATA / "3.root.json").read_text())

    mock_fetch_channel_signing_data(root2, root3)
    sig_ver = _SignatureVerification()

    # One call for 2.root.json and 3.root.json and 4.root.json (non-existant)
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
    root2 = json.loads((_TESTDATA / "2.root.json").read_text())
    root3 = json.loads((_TESTDATA / "3.root_invalid.json").read_text())

    mock_fetch_channel_signing_data(root2, root3)
    sig_ver = _SignatureVerification()

    # One call for 2.root.json and 3.root.json and 4.root.json (non-existant)
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
    mock_fetch_channel_signing_data(HTTP404)
    sig_ver = _SignatureVerification()

    # Compare sig_ver's view on key_mgr to
    assert sig_ver.key_mgr == key_mgr


def test_trusted_root_no_new_key_mgr_online_key_mgr_not_on_disk(
    av_data_dir: Path,
    initial_trust_root: dict,
    mock_fetch_channel_signing_data: Callable,
):
    """
    If we have no key_mgr online and no key_mgr on disk we don't have a key_mgr
    """
    mock_fetch_channel_signing_data(HTTP404)
    sig_ver = _SignatureVerification()

    # We should have no key_mgr here
    assert sig_ver.key_mgr is None


def test_trusted_root_new_key_mgr_online(
    av_data_dir: Path,
    initial_trust_root: dict,
    mock_fetch_channel_signing_data: Callable,
):
    """
    We have a new key_mgr online that can be verified against our trusted root.
    We should accept the new key_mgr
    """
    key_mgr = json.loads((_TESTDATA / "key_mgr.json").read_text())

    # First time around we return an HTTPError(404) to signal we don't have new root metadata.
    # Next, we return our new key_mgr data signaling we should update our key_mgr delegation
    mock_fetch_channel_signing_data(key_mgr, HTTP404)
    sig_ver = _SignatureVerification()

    assert sig_ver.key_mgr == key_mgr


def test_trusted_root_invalid_key_mgr_online_valid_on_disk(
    av_data_dir: Path,
    initial_trust_root: dict,
    mock_fetch_channel_signing_data: Callable,
):
    """
    We have a new key_mgr online that can be verified against our trusted root.
    We should accept the new key_mgr

    Note:  This one does not fail with a warning and no side effects like the others.
    Instead, we raise a SignatureError
    """
    key_mgr = json.loads((_TESTDATA / "key_mgr_invalid.json").read_text())
    copyfile(_TESTDATA / "key_mgr.json", av_data_dir / "key_mgr.json")

    # First time around we return an HTTPError(404) to signal we don't have new root metadata.
    # Next, we return our new key_mgr data signaling we should update our key_mgr delegation
    mock_fetch_channel_signing_data(key_mgr, HTTP404)
    sig_ver = _SignatureVerification()

    with pytest.raises(SignatureError):
        sig_ver.key_mgr


def test_signature_verification_enabled(
    av_data_dir: Path,
    initial_trust_root: dict,
    key_mgr: dict,
    monkeypatch: MonkeyPatch,
):
    signature_verification = _SignatureVerification()

    monkeypatch.setenv("CONDA_EXTRA_SAFETY_CHECKS", "false")
    monkeypatch.setenv("CONDA_SIGNING_METADATA_URL_BASE", "")
    reset_context()
    assert not context.extra_safety_checks
    assert not context.signing_metadata_url_base

    _SignatureVerification.cache_clear()
    assert not signature_verification.enabled

    monkeypatch.setenv("CONDA_EXTRA_SAFETY_CHECKS", "true")
    monkeypatch.setenv("CONDA_SIGNING_METADATA_URL_BASE", "")
    reset_context()
    assert context.extra_safety_checks
    assert not context.signing_metadata_url_base

    _SignatureVerification.cache_clear()
    assert not signature_verification.enabled

    monkeypatch.setenv("CONDA_EXTRA_SAFETY_CHECKS", "true")
    monkeypatch.setenv("CONDA_SIGNING_METADATA_URL_BASE", url := "https://example.com")
    reset_context()
    assert context.extra_safety_checks
    assert context.signing_metadata_url_base == url

    _SignatureVerification.cache_clear()
    assert signature_verification.enabled
