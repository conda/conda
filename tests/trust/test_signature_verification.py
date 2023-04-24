# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import json
from os import path, unlink
from shutil import copyfile
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock, Mock, PropertyMock, patch

from conda.gateways.connection import HTTPError
from conda.trust.constants import INITIAL_TRUST_ROOT
from conda.trust.signature_verification import _SignatureVerification


def _test_data_dir():
    test_dir = path.split(path.dirname(__file__))[0]
    return path.join(test_dir, "trust/testdata/")


def _get_test_initial_trust_root():
    test_1_root_json_location = path.join(_test_data_dir(), "1.root.json")
    with open(test_1_root_json_location) as f:
        return json.load(f)


def test_trusted_root_no_new_metadata():
    tmp_rootdir = TemporaryDirectory()

    with patch(
        "conda.base.context.Context.av_data_dir", new_callable=PropertyMock
    ) as av_data_dir_mock:
        av_data_dir_mock.return_value = tmp_rootdir.name
        with patch(
            "conda.trust.signature_verification.INITIAL_TRUST_ROOT",
            new=_get_test_initial_trust_root(),
        ):
            sig_ver = _SignatureVerification()

            # Mock out HTTP request
            err = HTTPError()
            err.response = SimpleNamespace()
            err.response.status_code = 404
            sig_ver._fetch_channel_signing_data = MagicMock(side_effect=err)

            # This thing is a property so this is effectively a call
            check_trusted_root = sig_ver.trusted_root
            sig_ver._fetch_channel_signing_data.assert_called()

            # Compare sig_ver's view on INITIAL_TRUST_ROOT to the contents of testdata/1.root.json
            assert check_trusted_root == _get_test_initial_trust_root()


def test_trusted_root_2nd_metadata_on_disk_no_new_metadata_on_web():
    """
    Tests a case where we cannot reach new root metadata online but have a newer version
    locally (2.root.json).  As I understand it, we should use this new version if it is valid
    """
    # Configure temporary trust root dir
    tmp_rootdir = TemporaryDirectory()
    with patch(
        "conda.base.context.Context.av_data_dir", new_callable=PropertyMock
    ) as av_data_dir_mock:
        av_data_dir_mock.return_value = tmp_rootdir.name
        with patch(
            "conda.trust.signature_verification.INITIAL_TRUST_ROOT",
            new=_get_test_initial_trust_root(),
        ):
            sig_ver = _SignatureVerification()

            # Find 2.root.json in our test data directory...
            testdata_2_root = path.join(_test_data_dir(), "2.root.json")

            # ... and copy it into our tmp trust root dir
            test_2_root_dest = path.join(tmp_rootdir.name, "2.root.json")
            copyfile(testdata_2_root, test_2_root_dest)

            # Mock out HTTP Request
            err = HTTPError()
            err.response = SimpleNamespace()
            err.response.status_code = 404
            sig_ver._fetch_channel_signing_data = MagicMock(side_effect=err)

            # This thing is a property so this is effectively a call
            check_trusted_root = sig_ver.trusted_root
            sig_ver._fetch_channel_signing_data.assert_called()

            with open(test_2_root_dest) as f:
                test_2_root_data = json.load(f)

            # Clean up old 2.root.json
            unlink(test_2_root_dest)

            assert check_trusted_root == test_2_root_data


def test_invalid_2nd_metadata_on_disk_no_new_metadata_on_web():
    """
    Unusual case:  We have an invalid 2.root.json on disk and no new metadata available online.  In this case,
    our deliberate choice is to accept whatever on disk.
    """
    # Configure temporary trust root dir
    tmp_rootdir = TemporaryDirectory()
    with patch(
        "conda.base.context.Context.av_data_dir", new_callable=PropertyMock
    ) as av_data_dir_mock:
        av_data_dir_mock.return_value = tmp_rootdir.name
        with patch(
            "conda.trust.signature_verification.INITIAL_TRUST_ROOT",
            new=_get_test_initial_trust_root(),
        ):
            sig_ver = _SignatureVerification()

            # Find 2.root_invalid.json in our test data directory...
            testdata_2_root = path.join(_test_data_dir(), "2.root_invalid.json")

            # ... and copy it into our tmp trust root dir
            test_2_root_dest = path.join(tmp_rootdir.name, "2.root.json")
            copyfile(testdata_2_root, test_2_root_dest)

            with open(test_2_root_dest) as f:
                test_2_root_data = json.load(f)

            data_mock = Mock()
            data_mock.side_effect = [test_2_root_data]
            sig_ver = _SignatureVerification()
            sig_ver._fetch_channel_signing_data = data_mock

            # Mock out HTTP Request
            # err = HTTPError()
            # err.response=SimpleNamespace()
            # err.response.status_code = 404
            # sig_ver._fetch_channel_signing_data = MagicMock(side_effect=err)

            # This thing is a property so this is effectively a call
            check_trusted_root = sig_ver.trusted_root
            # Clean up old 2.root.json
            unlink(test_2_root_dest)

            sig_ver._fetch_channel_signing_data.call_count == 1
            assert check_trusted_root == test_2_root_data


def test_2nd_root_metadata_from_web():
    """
    Test happy case where we get a new valid root metadata from the web
    """
    tmp_rootdir = TemporaryDirectory()
    with patch(
        "conda.base.context.Context.av_data_dir", new_callable=PropertyMock
    ) as av_data_dir_mock:
        av_data_dir_mock.return_value = tmp_rootdir.name
        with patch(
            "conda.trust.signature_verification.INITIAL_TRUST_ROOT",
            new=_get_test_initial_trust_root(),
        ):
            # Find 2.root.json in our test data directory...
            testdata_2_root = path.join(_test_data_dir(), "2.root.json")

            # Load 2.root.json's data so we can use it in our mock
            with open(testdata_2_root) as f:
                test_2_root_data = json.load(f)

            data_mock = Mock()
            data_mock.side_effect = [test_2_root_data]
            sig_ver = _SignatureVerification()
            sig_ver._fetch_channel_signing_data = data_mock

            # This thing is a property so this is effectively a call
            check_trusted_root = sig_ver.trusted_root

            # One call for 2.root.json and 3.root.json (non-existant)
            assert data_mock.call_count == 2

            assert check_trusted_root == test_2_root_data


def test_3rd_root_metadata_from_web():
    """
    Test happy case where we get a chaing of valid root metadata from the web
    """
    tmp_rootdir = TemporaryDirectory()
    with patch(
        "conda.base.context.Context.av_data_dir", new_callable=PropertyMock
    ) as av_data_dir_mock:
        av_data_dir_mock.return_value = tmp_rootdir.name
        with patch(
            "conda.trust.signature_verification.INITIAL_TRUST_ROOT",
            new=_get_test_initial_trust_root(),
        ):
            # Find 2.root.json in our test data directory...
            testdata_2_root = path.join(_test_data_dir(), "2.root.json")

            # Load 2.root.json's data so we can use it in our mock
            with open(testdata_2_root) as f:
                test_2_root_data = json.load(f)

            # Find 3.root.json in our test data directory...
            testdata_3_root = path.join(_test_data_dir(), "3.root.json")

            # Load 3.root.json's data so we can use it in our mock
            with open(testdata_3_root) as f:
                test_3_root_data = json.load(f)

            data_mock = Mock()
            data_mock.side_effect = [test_2_root_data, test_3_root_data]
            sig_ver = _SignatureVerification()
            sig_ver._fetch_channel_signing_data = data_mock

            # This thing is a property so this is effectively a call
            check_trusted_root = sig_ver.trusted_root

            # One call for 2.root.json and 3.root.json and 4.root.json (non-existant)
            assert data_mock.call_count == 3

            assert check_trusted_root == test_3_root_data


def test_single_invalid_signature_3rd_root_metadata_from_web():
    """
    Third root metadata retrieved from online has a bad signature. Test that we do not trust it.
    """
    tmp_rootdir = TemporaryDirectory()
    with patch(
        "conda.base.context.Context.av_data_dir", new_callable=PropertyMock
    ) as av_data_dir_mock:
        av_data_dir_mock.return_value = tmp_rootdir.name
        with patch(
            "conda.trust.signature_verification.INITIAL_TRUST_ROOT",
            new=_get_test_initial_trust_root(),
        ):
            # Find 2.root.json in our test data directory...
            testdata_2_root = path.join(_test_data_dir(), "2.root.json")

            # Load 2.root.json's data so we can use it in our mock
            with open(testdata_2_root) as f:
                test_2_root_data = json.load(f)

            # Find 3.root.json in our test data directory...
            testdata_3_root = path.join(_test_data_dir(), "3.root_invalid.json")

            # Load 3.root.json's data so we can use it in our mock
            with open(testdata_3_root) as f:
                test_3_root_data = json.load(f)

            data_mock = Mock()
            data_mock.side_effect = [test_2_root_data, test_3_root_data]
            sig_ver = _SignatureVerification()
            sig_ver._fetch_channel_signing_data = data_mock

            # This thing is a property so this is effectively a call
            check_trusted_root = sig_ver.trusted_root

            # One call for 2.root.json and 3.root.json and 4.root.json (non-existant)
            assert data_mock.call_count == 2

            assert check_trusted_root == test_2_root_data
