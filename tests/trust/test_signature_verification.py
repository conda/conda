# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import json
from pathlib import Path
from shutil import copyfile
from types import SimpleNamespace

import pytest
from pytest import MonkeyPatch
from pytest_mock import MockerFixture

from conda.base.context import context, reset_context
from conda.gateways.connection import HTTPError
from conda.trust.signature_verification import SignatureError, _SignatureVerification

_TESTDATA = Path(__file__).parent / "testdata"


@pytest.fixture
def initial_trust_root(mocker: MockerFixture, tmp_path: Path) -> str:
    mocker.patch(
        "conda.base.context.Context.av_data_dir",
        new_callable=mocker.PropertyMock,
        return_value=tmp_path,
    )
    mocker.patch(
        "conda.trust.signature_verification.INITIAL_TRUST_ROOT",
        new=(initial_trust_root := json.loads((_TESTDATA / "1.root.json").read_text())),
    )
    return initial_trust_root


def test_trusted_root_no_new_metadata(
    initial_trust_root: str,
    tmp_path: Path,
    mocker: MockerFixture,
):
    # Mock out HTTP request
    mocker.patch(
        "conda.trust.signature_verification._SignatureVerification._fetch_channel_signing_data",
        side_effect=HTTPError(response=SimpleNamespace(status_code=404)),
    )

    sig_ver = _SignatureVerification()

    check_trusted_root = sig_ver.trusted_root
    sig_ver._fetch_channel_signing_data.assert_called()

    # Compare sig_ver's view on INITIAL_TRUST_ROOT to the contents of testdata/1.root.json
    assert check_trusted_root == initial_trust_root


def test_trusted_root_2nd_metadata_on_disk_no_new_metadata_on_web(
    initial_trust_root: str,
    tmp_path: Path,
    mocker: MockerFixture,
):
    """
    Tests a case where we cannot reach new root metadata online but have a newer version
    locally (2.root.json).  As I understand it, we should use this new version if it is valid
    """
    # Mock out HTTP Request
    mocker.patch(
        "conda.trust.signature_verification._SignatureVerification._fetch_channel_signing_data",
        side_effect=HTTPError(response=SimpleNamespace(status_code=404)),
    )

    sig_ver = _SignatureVerification()

    # Find 2.root.json in our test data directory...
    testdata_2_root = _TESTDATA / "2.root.json"

    # ... and copy it into our tmp trust root dir
    test_2_root_dest = tmp_path / "2.root.json"
    copyfile(testdata_2_root, test_2_root_dest)

    check_trusted_root = sig_ver.trusted_root
    sig_ver._fetch_channel_signing_data.assert_called()

    assert check_trusted_root == json.loads(test_2_root_dest.read_text())


def test_invalid_2nd_metadata_on_disk_no_new_metadata_on_web(
    initial_trust_root: str,
    tmp_path: Path,
    mocker: MockerFixture,
):
    """
    Unusual case:  We have an invalid 2.root.json on disk and no new metadata available online.  In this case,
    our deliberate choice is to accept whatever on disk.
    """
    sig_ver = _SignatureVerification()

    # Find 2.root_invalid.json in our test data directory...
    testdata_2_root = _TESTDATA / "2.root_invalid.json"

    # ... and copy it into our tmp trust root dir
    test_2_root_dest = tmp_path / "2.root.json"
    copyfile(testdata_2_root, test_2_root_dest)

    test_2_root_data = json.loads(test_2_root_dest.read_text())

    data_mock = mocker.Mock()
    data_mock.side_effect = [test_2_root_data]
    sig_ver = _SignatureVerification()
    sig_ver._fetch_channel_signing_data = data_mock

    # Mock out HTTP Request
    # err = HTTPError(response=SimpleNamespace(status_code=404))
    # sig_ver._fetch_channel_signing_data = mocker.MagicMock(side_effect=err)

    # This thing is a property so this is effectively a call
    check_trusted_root = sig_ver.trusted_root

    sig_ver._fetch_channel_signing_data.call_count == 1
    assert check_trusted_root == test_2_root_data


def test_2nd_root_metadata_from_web(
    initial_trust_root: str,
    tmp_path: Path,
    mocker: MockerFixture,
):
    """
    Test happy case where we get a new valid root metadata from the web
    """
    # Find 2.root.json in our test data directory...
    testdata_2_root = _TESTDATA / "2.root.json"

    # Load 2.root.json's data so we can use it in our mock
    test_2_root_data = json.loads(testdata_2_root.read_text())

    data_mock = mocker.Mock()
    data_mock.side_effect = [test_2_root_data]
    sig_ver = _SignatureVerification()
    sig_ver._fetch_channel_signing_data = data_mock

    # This thing is a property so this is effectively a call
    check_trusted_root = sig_ver.trusted_root

    # One call for 2.root.json and 3.root.json (non-existant)
    assert data_mock.call_count == 2

    assert check_trusted_root == test_2_root_data


def test_3rd_root_metadata_from_web(
    initial_trust_root: str,
    tmp_path: Path,
    mocker: MockerFixture,
):
    """
    Test happy case where we get a chaing of valid root metadata from the web
    """
    # Find 2.root.json in our test data directory...
    testdata_2_root = _TESTDATA / "2.root.json"

    # Load 2.root.json's data so we can use it in our mock
    test_2_root_data = json.loads(testdata_2_root.read_text())

    # Find 3.root.json in our test data directory...
    testdata_3_root = _TESTDATA / "3.root.json"

    # Load 3.root.json's data so we can use it in our mock
    test_3_root_data = json.loads(testdata_3_root.read_text())

    data_mock = mocker.Mock()
    data_mock.side_effect = [test_2_root_data, test_3_root_data]
    sig_ver = _SignatureVerification()
    sig_ver._fetch_channel_signing_data = data_mock

    # This thing is a property so this is effectively a call
    check_trusted_root = sig_ver.trusted_root

    # One call for 2.root.json and 3.root.json and 4.root.json (non-existant)
    assert data_mock.call_count == 3

    assert check_trusted_root == test_3_root_data


def test_single_invalid_signature_3rd_root_metadata_from_web(
    initial_trust_root: str,
    tmp_path: Path,
    mocker: MockerFixture,
):
    """
    Third root metadata retrieved from online has a bad signature. Test that we do not trust it.
    """
    # Find 2.root.json in our test data directory...
    testdata_2_root = _TESTDATA / "2.root.json"

    # Load 2.root.json's data so we can use it in our mock
    test_2_root_data = json.loads(testdata_2_root.read_text())

    # Find 3.root.json in our test data directory...
    testdata_3_root = _TESTDATA / "3.root_invalid.json"

    # Load 3.root.json's data so we can use it in our mock
    test_3_root_data = json.loads(testdata_3_root.read_text())

    data_mock = mocker.Mock()
    data_mock.side_effect = [test_2_root_data, test_3_root_data]
    sig_ver = _SignatureVerification()
    sig_ver._fetch_channel_signing_data = data_mock

    # This thing is a property so this is effectively a call
    check_trusted_root = sig_ver.trusted_root

    # One call for 2.root.json and 3.root.json and 4.root.json (non-existant)
    assert data_mock.call_count == 2

    assert check_trusted_root == test_2_root_data


######## Begin Keymgr Tests ########


def test_trusted_root_no_new_key_mgr_online_key_mgr_is_on_disk(
    initial_trust_root: str,
    tmp_path: Path,
    mocker: MockerFixture,
):
    """
    If we don't have a new key_mgr online, we use the one from disk
    """
    sig_ver = _SignatureVerification()

    # Mock out HTTP request
    err = HTTPError(response=SimpleNamespace(status_code=404))
    sig_ver._fetch_channel_signing_data = mocker.MagicMock(side_effect=err)

    # Find key_mgr.json in our test data directory...
    test_key_mgr_path = _TESTDATA / "key_mgr.json"

    # ... and copy it into our tmp trust root dir
    test_key_mgr_dest = tmp_path / "key_mgr.json"
    copyfile(test_key_mgr_path, test_key_mgr_dest)

    test_key_mgr_data = json.loads(test_key_mgr_path.read_text())

    # Compare sig_ver's view on key_mgr to
    check_key_mgr = sig_ver.key_mgr
    assert check_key_mgr == test_key_mgr_data


def test_trusted_root_no_new_key_mgr_online_key_mgr_not_on_disk(
    initial_trust_root: str,
    tmp_path: Path,
    mocker: MockerFixture,
):
    """
    If we have no key_mgr online and no key_mgr on disk we don't have a key_mgr
    """
    sig_ver = _SignatureVerification()

    # Mock out HTTP request
    err = HTTPError(response=SimpleNamespace(status_code=404))
    sig_ver._fetch_channel_signing_data = mocker.MagicMock(side_effect=err)

    # We should have no key_mgr here
    assert sig_ver.key_mgr == None


def test_trusted_root_new_key_mgr_online(
    initial_trust_root: str,
    tmp_path: Path,
    mocker: MockerFixture,
):
    """
    We have a new key_mgr online that can be verified against our trusted root.
    We should accept the new key_mgr
    """
    # Find key_mgr.json in our test data directory...
    test_key_mgr_path = _TESTDATA / "key_mgr.json"

    # Load key_mgr's data so we can use it in our mock
    test_key_mgr_data = json.loads(test_key_mgr_path.read_text())

    # This HTTPError is for the first request.  Will make us use our local 1.root.json
    err = HTTPError(response=SimpleNamespace(status_code=404))
    data_mock = mocker.Mock()

    # First time around we return an HTTPError(404) to signal we don't have new root metadata.
    # Next, we return our new key_mgr data signaling we should update our key_mgr delegation
    data_mock.side_effect = [test_key_mgr_data, err]
    sig_ver = _SignatureVerification()
    if not sig_ver.enabled:
        pytest.skip("Signature verification not enabled")
    sig_ver._fetch_channel_signing_data = data_mock
    check_key_mgr = sig_ver.key_mgr

    assert check_key_mgr == test_key_mgr_data


def test_trusted_root_invalid_key_mgr_online_valid_on_disk(
    initial_trust_root: str,
    tmp_path: Path,
    mocker: MockerFixture,
):
    """
    We have a new key_mgr online that can be verified against our trusted root.
    We should accept the new key_mgr

    Note:  This one does not fail with a warning and no side effects like the others.
    Instead, we raise a SignatureError
    """
    sig_ver = _SignatureVerification()
    if not sig_ver.enabled:
        pytest.skip("Signature verification not enabled")

    ## Find and load invalid key_mgr data
    # Find key_mgr_invalid.json in our test data directory...
    test_key_mgr_invalid_path = _TESTDATA / "key_mgr_invalid.json"

    # Load key_mgr_invalid's data so we can use it in our mock
    test_key_mgr_invalid_data = json.loads(test_key_mgr_invalid_path.read_text())

    ## Find and load valid key_mgr data
    # Find key_mgr_invalid.json in our test data directory...
    test_key_mgr_path = _TESTDATA / "key_mgr.json"

    # Load key_mgr's data so we can use it in our checks later
    test_key_mgr_data = json.loads(test_key_mgr_path.read_text())

    # Copy valid key_mgr data into our trust data directory
    test_key_mgr_dest = tmp_path / "key_mgr.json"
    copyfile(test_key_mgr_path, test_key_mgr_dest)

    # This HTTPError is for the first request.  Will make us use our local 1.root.json
    err = HTTPError(response=SimpleNamespace(status_code=404))
    data_mock = mocker.Mock()

    # First time around we return an HTTPError(404) to signal we don't have new root metadata.
    # Next, we return our new key_mgr data signaling we should update our key_mgr delegation
    data_mock.side_effect = [test_key_mgr_invalid_data, err]
    sig_ver._fetch_channel_signing_data = data_mock

    with pytest.raises(SignatureError):
        check_key_mgr = sig_ver.key_mgr


def test_signature_verification_enabled(monkeypatch: MonkeyPatch):
    signature_verification = _SignatureVerification()

    monkeypatch.setenv("CONDA_EXTRA_SAFETY_CHECKS", "false")
    monkeypatch.setenv("CONDA_SIGNING_METADATA_URL_BASE", "")
    reset_context()
    assert not context.extra_safety_checks
    assert not context.signing_metadata_url_base

    _SignatureVerification.enabled.fget.cache_clear()
    assert not signature_verification.enabled

    monkeypatch.setenv("CONDA_EXTRA_SAFETY_CHECKS", "true")
    monkeypatch.setenv("CONDA_SIGNING_METADATA_URL_BASE", "")
    reset_context()
    assert context.extra_safety_checks
    assert not context.signing_metadata_url_base

    _SignatureVerification.enabled.fget.cache_clear()
    assert not signature_verification.enabled

    monkeypatch.setenv("CONDA_EXTRA_SAFETY_CHECKS", "true")
    monkeypatch.setenv("CONDA_SIGNING_METADATA_URL_BASE", url := "https://example.com")
    reset_context()
    assert context.extra_safety_checks
    assert context.signing_metadata_url_base == url

    _SignatureVerification.enabled.fget.cache_clear()
    assert signature_verification.enabled
