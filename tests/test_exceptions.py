# -*- coding: utf-8 -*-
# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause

from __future__ import absolute_import, division, print_function, unicode_literals

import json
from unittest import TestCase

import sys
import os
import getpass

from conda import text_type
from conda.auxlib.collection import AttrDict
from conda.auxlib.ish import dals
from conda.base.context import context, conda_tests_ctxt_mgmt_def_pol
from conda.common.compat import on_win
from conda.common.io import captured, env_var
from conda.exceptions import BasicClobberError, BinaryPrefixReplacementError, CommandNotFoundError, \
    CondaHTTPError, CondaKeyError, CondaRevisionError, DirectoryNotFoundError, \
    KnownPackageClobberError, ChecksumMismatchError, PackagesNotFoundError, PathNotFoundError, \
    SharedLinkPathClobberError, TooFewArgumentsError, TooManyArgumentsError, \
    UnknownPackageClobberError, conda_exception_handler, ExceptionHandler

try:
    from unittest.mock import Mock, patch
except ImportError:
    from mock import Mock, patch


def _raise_helper(exception):
    raise exception


def username_not_in_post_mock(post_mock, username):
    for cal in post_mock.call_args_list:
        for call_part in cal:
            if username in str(call_part):
                return False
    return True


class ExceptionTests(TestCase):

    def test_TooManyArgumentsError(self):
        expected = 2
        received = 5
        offending_arguments = "groot"
        exc = TooManyArgumentsError(expected, received, offending_arguments)
        with env_var("CONDA_JSON", "yes", stack_callback=conda_tests_ctxt_mgmt_def_pol):
            with captured() as c:
                conda_exception_handler(_raise_helper, exc)

        json_obj = json.loads(c.stdout)
        assert not c.stderr
        assert json_obj['exception_type'] == "<class 'conda.exceptions.TooManyArgumentsError'>"
        assert json_obj['exception_name'] == 'TooManyArgumentsError'
        assert json_obj['message'] == text_type(exc)
        assert json_obj['error'] == repr(exc)
        assert json_obj['expected'] == 2
        assert json_obj['received'] == 5
        assert json_obj['offending_arguments'] == "groot"

        with env_var("CONDA_JSON", "no", stack_callback=conda_tests_ctxt_mgmt_def_pol):
            with captured() as c:
                conda_exception_handler(_raise_helper, exc)

        assert not c.stdout
        assert c.stderr.strip() == "TooManyArgumentsError:  Got 5 arguments (g, r, o, o, t) but expected 2."

    def test_TooFewArgumentsError(self):
        expected = 5
        received = 2
        exc = TooFewArgumentsError(expected, received)
        with env_var("CONDA_JSON", "yes", stack_callback=conda_tests_ctxt_mgmt_def_pol):
            with captured() as c:
                conda_exception_handler(_raise_helper, exc)

        json_obj = json.loads(c.stdout)
        assert not c.stderr
        assert json_obj['exception_type'] == "<class 'conda.exceptions.TooFewArgumentsError'>"
        assert json_obj['exception_name'] == 'TooFewArgumentsError'
        assert json_obj['message'] == text_type(exc)
        assert json_obj['error'] == repr(exc)
        assert json_obj['expected'] == 5
        assert json_obj['received'] == 2

        with env_var("CONDA_JSON", "no", stack_callback=conda_tests_ctxt_mgmt_def_pol):
            with captured() as c:
                conda_exception_handler(_raise_helper, exc)

        assert not c.stdout
        assert c.stderr.strip() == "TooFewArgumentsError:  Got 2 arguments but expected 5."

    def test_BasicClobberError(self):
        source_path = "some/path/on/goodwin.ave"
        target_path = "some/path/to/wright.st"
        exc = BasicClobberError(source_path, target_path, context)
        t = repr(exc)
        with env_var("CONDA_PATH_CONFLICT", "prevent", stack_callback=conda_tests_ctxt_mgmt_def_pol):
            with captured() as c:
                conda_exception_handler(_raise_helper, exc)

        assert not c.stdout
        assert c.stderr.strip() == dals("""
        ClobberError: Conda was asked to clobber an existing path.
          source path: some/path/on/goodwin.ave
          target path: some/path/to/wright.st
        """).strip()

    def test_KnownPackageClobberError(self):
        target_path = "some/where/on/goodwin.ave"
        colliding_dist_being_linked = "Groot"
        colliding_linked_dist = "Liquid"
        exc = KnownPackageClobberError(target_path, colliding_dist_being_linked, colliding_linked_dist, context)
        with env_var("CONDA_PATH_CONFLICT", "prevent", stack_callback=conda_tests_ctxt_mgmt_def_pol):
            with captured() as c:
                conda_exception_handler(_raise_helper, exc)

        assert not c.stdout
        assert c.stderr.strip() == dals("""
        ClobberError: The package 'Groot' cannot be installed due to a
        path collision for 'some/where/on/goodwin.ave'.
        This path already exists in the target prefix, and it won't be removed by
        an uninstall action in this transaction. The path appears to be coming from
        the package 'Liquid', which is already installed in the prefix.
        """).strip()

    def test_UnknownPackageClobberError(self):
        target_path = "siebel/center/for/c.s"
        colliding_dist_being_linked = "Groot"
        exc = UnknownPackageClobberError(target_path, colliding_dist_being_linked, context)
        with env_var("CONDA_PATH_CONFLICT", "prevent", stack_callback=conda_tests_ctxt_mgmt_def_pol):
            with captured() as c:
                conda_exception_handler(_raise_helper, exc)

        assert not c.stdout
        assert c.stderr.strip() == dals("""
        ClobberError: The package 'Groot' cannot be installed due to a
        path collision for 'siebel/center/for/c.s'.
        This path already exists in the target prefix, and it won't be removed
        by an uninstall action in this transaction. The path is one that conda
        doesn't recognize. It may have been created by another package manager.
        """).strip()

    def test_SharedLinkPathClobberError(self):
        target_path = "some/where/in/shampoo/banana"
        incompatible_package_dists = "Groot"
        exc = SharedLinkPathClobberError(target_path, incompatible_package_dists, context)
        with env_var("CONDA_PATH_CONFLICT", "prevent", stack_callback=conda_tests_ctxt_mgmt_def_pol):
            with captured() as c:
                conda_exception_handler(_raise_helper, exc)

        assert not c.stdout
        assert c.stderr.strip() == dals("""
        ClobberError: This transaction has incompatible packages due to a shared path.
          packages: G, r, o, o, t
          path: 'some/where/in/shampoo/banana'
        """).strip()

    def test_CondaFileNotFoundError(self):
        filename = "Groot"
        exc = PathNotFoundError(filename)
        with env_var("CONDA_JSON", "yes", stack_callback=conda_tests_ctxt_mgmt_def_pol):
            with captured() as c:
                conda_exception_handler(_raise_helper, exc)

        json_obj = json.loads(c.stdout)
        assert not c.stderr
        assert json_obj['exception_type'] == "<class 'conda.exceptions.PathNotFoundError'>"
        assert json_obj['exception_name'] == 'PathNotFoundError'
        assert json_obj['message'] == text_type(exc)
        assert json_obj['error'] == repr(exc)

        with env_var("CONDA_JSON", "no", stack_callback=conda_tests_ctxt_mgmt_def_pol):
            with captured() as c:
                conda_exception_handler(_raise_helper, exc)

        assert not c.stdout
        assert c.stderr.strip() == "PathNotFoundError: Groot"

    def test_DirectoryNotFoundError(self):
        directory = "Groot"
        exc = DirectoryNotFoundError(directory)
        with env_var("CONDA_JSON", "yes", stack_callback=conda_tests_ctxt_mgmt_def_pol):
            with captured() as c:
                conda_exception_handler(_raise_helper, exc)

        json_obj = json.loads(c.stdout)
        assert not c.stderr
        assert json_obj['exception_type'] == "<class 'conda.exceptions.DirectoryNotFoundError'>"
        assert json_obj['exception_name'] == 'DirectoryNotFoundError'
        assert json_obj['message'] == text_type(exc)
        assert json_obj['error'] == repr(exc)
        assert json_obj['path'] == "Groot"

        with env_var("CONDA_JSON", "no", stack_callback=conda_tests_ctxt_mgmt_def_pol):
            with captured() as c:
                conda_exception_handler(_raise_helper, exc)

        assert not c.stdout
        assert c.stderr.strip() == "DirectoryNotFoundError: Groot"

    def test_MD5MismatchError(self):
        url = "https://download.url/path/to/file.tar.bz2"
        target_full_path = "/some/path/on/disk/another-name.tar.bz2"
        expected_md5sum = "abc123"
        actual_md5sum = "deadbeef"
        exc = ChecksumMismatchError(url, target_full_path, "md5", expected_md5sum, actual_md5sum)
        with env_var("CONDA_JSON", "yes", stack_callback=conda_tests_ctxt_mgmt_def_pol):
            with captured() as c:
                conda_exception_handler(_raise_helper, exc)

        json_obj = json.loads(c.stdout)
        assert not c.stderr
        assert json_obj['exception_type'] == "<class 'conda.exceptions.ChecksumMismatchError'>"
        assert json_obj['exception_name'] == 'ChecksumMismatchError'
        assert json_obj['message'] == text_type(exc)
        assert json_obj['error'] == repr(exc)
        assert json_obj['url'] == url
        assert json_obj['target_full_path'] == target_full_path
        assert json_obj['expected_checksum'] == expected_md5sum
        assert json_obj['actual_checksum'] == actual_md5sum

        with env_var("CONDA_JSON", "no", stack_callback=conda_tests_ctxt_mgmt_def_pol):
            with captured() as c:
                conda_exception_handler(_raise_helper, exc)

        assert not c.stdout
        assert c.stderr.strip() == dals("""
        ChecksumMismatchError: Conda detected a mismatch between the expected content and downloaded content
        for url 'https://download.url/path/to/file.tar.bz2'.
          download saved to: /some/path/on/disk/another-name.tar.bz2
          expected md5: abc123
          actual md5: deadbeef
        """).strip()

    def test_PackageNotFoundError(self):
        package = "Potato"
        with env_var("CONDA_JSON", "yes", stack_callback=conda_tests_ctxt_mgmt_def_pol):
            with captured() as c:
                exc = PackagesNotFoundError((package,))
                conda_exception_handler(_raise_helper, exc)

        json_obj = json.loads(c.stdout)
        assert not c.stderr
        assert json_obj['exception_type'] == "<class 'conda.exceptions.PackagesNotFoundError'>"
        assert json_obj['message'] == text_type(exc)
        assert json_obj['error'] == repr(exc)

        with env_var("CONDA_JSON", "no", stack_callback=conda_tests_ctxt_mgmt_def_pol):
            with captured() as c:
                conda_exception_handler(_raise_helper, exc)

        assert not c.stdout
        assert c.stderr.strip() == dals("""
        PackagesNotFoundError: The following packages are missing from the target environment:
          - Potato
        """).strip()

    def test_CondaRevisionError(self):
        message = "Potato"
        exc = CondaRevisionError(message)
        with env_var("CONDA_JSON", "yes", stack_callback=conda_tests_ctxt_mgmt_def_pol):
            with captured() as c:
                conda_exception_handler(_raise_helper, exc)

        json_obj = json.loads(c.stdout)
        assert not c.stderr
        assert json_obj['exception_type'] == "<class 'conda.exceptions.CondaRevisionError'>"
        assert json_obj['exception_name'] == 'CondaRevisionError'
        assert json_obj['message'] == text_type(exc)
        assert json_obj['error'] == repr(exc)

        with env_var("CONDA_JSON", "no", stack_callback=conda_tests_ctxt_mgmt_def_pol):
            with captured() as c:
                conda_exception_handler(_raise_helper, exc)

        assert not c.stdout
        assert c.stderr.strip() == "CondaRevisionError: Potato."

    def test_CondaKeyError(self):
        key = "Potato"
        message = "Potato is not a key."
        exc = CondaKeyError(key, message)
        with env_var("CONDA_JSON", "yes", stack_callback=conda_tests_ctxt_mgmt_def_pol):
            with captured() as c:
                conda_exception_handler(_raise_helper, exc)

        json_obj = json.loads(c.stdout)
        assert not c.stderr
        assert json_obj['exception_type'] == "<class 'conda.exceptions.CondaKeyError'>"
        assert json_obj['exception_name'] == 'CondaKeyError'
        assert json_obj['message'] == text_type(exc)
        assert json_obj['error'] == repr(exc)
        assert json_obj['key'] == "Potato"

        with env_var("CONDA_JSON", "no", stack_callback=conda_tests_ctxt_mgmt_def_pol):
            with captured() as c:
                conda_exception_handler(_raise_helper, exc)

        assert not c.stdout
        assert c.stderr.strip() == "CondaKeyError: 'Potato': Potato is not a key."

    def test_CondaHTTPError(self):
        msg = "Potato"
        url = "https://download.url/path/to/Potato.tar.gz"
        status_code = "Potato"
        reason = "COULD NOT CONNECT"
        elapsed_time = 1.24
        exc = CondaHTTPError(msg, url, status_code, reason, elapsed_time)

        with env_var("CONDA_JSON", "yes", stack_callback=conda_tests_ctxt_mgmt_def_pol):
            with captured() as c:
                conda_exception_handler(_raise_helper, exc)

            json_obj = json.loads(c.stdout)
            assert not c.stderr
            assert json_obj['exception_type'] == "<class 'conda.exceptions.CondaHTTPError'>"
            assert json_obj['exception_name'] == 'CondaHTTPError'
            assert json_obj['message'] == text_type(exc)
            assert json_obj['error'] == repr(exc)
            assert json_obj['url'] == url
            assert json_obj['status_code'] == status_code
            assert json_obj['reason'] == reason
            assert json_obj['elapsed_time'] == elapsed_time

        with env_var("CONDA_JSON", "no", stack_callback=conda_tests_ctxt_mgmt_def_pol):
            with captured() as c:
                conda_exception_handler(_raise_helper, exc)

        assert not c.stdout
        assert dals("""
                CondaHTTPError: HTTP Potato COULD NOT CONNECT for url <https://download.url/path/to/Potato.tar.gz>
                Elapsed: 1.24

                Potato
                """).strip() in c.stderr.strip()

    def test_CommandNotFoundError_simple(self):
        cmd = "instate"
        exc = CommandNotFoundError(cmd)

        with env_var("CONDA_JSON", "yes", stack_callback=conda_tests_ctxt_mgmt_def_pol):
            with captured() as c:
                conda_exception_handler(_raise_helper, exc)

        json_obj = json.loads(c.stdout)
        assert not c.stderr
        assert json_obj['exception_type'] == "<class 'conda.exceptions.CommandNotFoundError'>"
        assert json_obj['message'] == text_type(exc)
        assert json_obj['error'] == repr(exc)

        with env_var("CONDA_JSON", "no", stack_callback=conda_tests_ctxt_mgmt_def_pol):
            with captured() as c:
                conda_exception_handler(_raise_helper, exc)

        assert not c.stdout
        assert c.stderr.strip() == ("CommandNotFoundError: No command 'conda instate'.\n"
                                    "Did you mean 'conda install'?")

    def test_CommandNotFoundError_conda_build(self):
        cmd = "build"
        exc = CommandNotFoundError(cmd)

        with env_var("CONDA_JSON", "yes", stack_callback=conda_tests_ctxt_mgmt_def_pol):
            with captured() as c:
                conda_exception_handler(_raise_helper, exc)

        json_obj = json.loads(c.stdout)
        assert not c.stderr
        assert json_obj['exception_type'] == "<class 'conda.exceptions.CommandNotFoundError'>"
        assert json_obj['message'] == text_type(exc)
        assert json_obj['error'] == repr(exc)

        with env_var("CONDA_JSON", "no", stack_callback=conda_tests_ctxt_mgmt_def_pol):
            with captured() as c:
                conda_exception_handler(_raise_helper, exc)

        assert not c.stdout
        assert c.stderr.strip() == ("CommandNotFoundError: To use 'conda build', install conda-build.")

    @patch('requests.post', side_effect=(
            AttrDict(headers=AttrDict(Location='somewhere.else'), status_code=302,
                     raise_for_status=lambda: None),
            AttrDict(raise_for_status=lambda: None),
    ))
    def test_print_unexpected_error_message_upload_1(self, post_mock):
        with env_var('CONDA_REPORT_ERRORS', 'true', stack_callback=conda_tests_ctxt_mgmt_def_pol):
            with captured() as c:
                ExceptionHandler()(_raise_helper, AssertionError())

            username = getpass.getuser()
            assert username_not_in_post_mock(post_mock, username)
            assert post_mock.call_count == 2
            assert c.stdout == ''
            assert "conda version" in c.stderr

    @patch('requests.post', side_effect=(
            AttrDict(headers=AttrDict(Location='somewhere.else'), status_code=302,
                     raise_for_status=lambda: None),
            AttrDict(headers=AttrDict(Location='somewhere.again'), status_code=301,
                     raise_for_status=lambda: None),
            AttrDict(raise_for_status=lambda: None),
    ))
    def test_print_unexpected_error_message_upload_2(self, post_mock):
        with env_var('CONDA_JSON', 'true', stack_callback=conda_tests_ctxt_mgmt_def_pol):
            with env_var('CONDA_YES', 'yes', stack_callback=conda_tests_ctxt_mgmt_def_pol):
                with captured() as c:
                    ExceptionHandler()(_raise_helper, AssertionError())

                username = getpass.getuser()
                assert username_not_in_post_mock(post_mock, username)
                assert post_mock.call_count == 3
                assert len(json.loads(c.stdout)['conda_info']['channels']) >= 2
                assert not c.stderr

    @patch('requests.post', side_effect=(
            AttrDict(headers=AttrDict(Location='somewhere.else'), status_code=302,
                     raise_for_status=lambda: None),
            AttrDict(raise_for_status=lambda: None),
    ))
    @patch('conda.exceptions.input', return_value='y')
    @patch('conda.exceptions.os.isatty', return_value=True)
    def test_print_unexpected_error_message_upload_3(self, isatty_mock, input_mock, post_mock):
        with captured() as c:
            ExceptionHandler()(_raise_helper, AssertionError())

        username = getpass.getuser()
        assert username_not_in_post_mock(post_mock, username)
        assert input_mock.call_count == 1
        assert post_mock.call_count == 2
        assert c.stdout == ''
        assert "conda version" in c.stderr

    @patch('requests.post', side_effect=(
            AttrDict(headers=AttrDict(Location='somewhere.else'), status_code=302,
                     raise_for_status=lambda: None),
            AttrDict(raise_for_status=lambda: None),
    ))
    @patch('getpass.getuser', return_value='some name')
    def test_print_unexpected_error_message_upload_username_with_spaces(self, pwuid, post_mock):
        with env_var('CONDA_REPORT_ERRORS', 'true', stack_callback=conda_tests_ctxt_mgmt_def_pol):
            with captured() as c:
                ExceptionHandler()(_raise_helper, AssertionError())

            error_data = json.loads(post_mock.call_args[1].get("data"))
            assert error_data.get("has_spaces") == True
            assert error_data.get("is_ascii") == True
            assert post_mock.call_count == 2
            assert c.stdout == ''
            assert "conda version" in c.stderr

    @patch('requests.post', side_effect=(
            AttrDict(headers=AttrDict(Location='somewhere.else'), status_code=302,
                     raise_for_status=lambda: None),
            AttrDict(raise_for_status=lambda: None),
    ))
    @patch('getpass.getuser', return_value='my√nameΩ')
    def test_print_unexpected_error_message_upload_username_with_unicode(self, pwuid, post_mock):
        with env_var('CONDA_REPORT_ERRORS', 'true', stack_callback=conda_tests_ctxt_mgmt_def_pol):
            with captured() as c:
                ExceptionHandler()(_raise_helper, AssertionError())

            error_data = json.loads(post_mock.call_args[1].get("data"))
            assert error_data.get("has_spaces") == False
            assert error_data.get("is_ascii") == False
            assert post_mock.call_count == 2
            assert c.stdout == ''
            assert "conda version" in c.stderr

    @patch('requests.post', return_value=None)
    @patch('conda.exceptions.input', return_value='n')
    def test_print_unexpected_error_message_opt_out_1(self, input_mock, post_mock):
        with env_var('CONDA_REPORT_ERRORS', 'false', stack_callback=conda_tests_ctxt_mgmt_def_pol):
            e = AssertionError()
            with captured() as c:
                ExceptionHandler()(_raise_helper, AssertionError())

            assert input_mock.call_count == 0
            assert post_mock.call_count == 0
            assert c.stdout == ''
            print(c.stderr, file=sys.stderr)
            assert "conda version" in c.stderr

    @patch('requests.post', return_value=None)
    @patch('conda.exceptions.input', return_value='n')
    @patch('conda.exceptions.os.isatty', return_value=True)
    def test_print_unexpected_error_message_opt_out_2(self, isatty_mock, input_mock, post_mock):
        with captured() as c:
            ExceptionHandler()(_raise_helper, AssertionError())

        assert input_mock.call_count == 1
        assert post_mock.call_count == 0
        assert c.stdout == ''
        assert "conda version" in c.stderr

    def test_BinaryPrefixReplacementError(self):
        new_data_length = 1104
        original_data_length = 1404
        new_prefix = "some/where/on/goodwin.ave"
        path = "some/where/by/boneyard/creek"
        placeholder = "save/my/spot/in/374"
        exc = BinaryPrefixReplacementError(path, placeholder, new_prefix,
                                           original_data_length, new_data_length)
        with env_var("CONDA_JSON", "yes", stack_callback=conda_tests_ctxt_mgmt_def_pol):
            with captured() as c:
                conda_exception_handler(_raise_helper, exc)

        json_obj = json.loads(c.stdout)
        assert not c.stderr
        assert json_obj['exception_type'] == "<class 'conda.exceptions.BinaryPrefixReplacementError'>"
        assert json_obj['exception_name'] == 'BinaryPrefixReplacementError'
        assert json_obj['message'] == text_type(exc)
        assert json_obj['error'] == repr(exc)
        assert json_obj['new_data_length'] == 1104
        assert json_obj['original_data_length'] == 1404
        assert json_obj['new_prefix'] == new_prefix
        assert json_obj['path'] == path
        assert json_obj['placeholder'] == placeholder

        with env_var("CONDA_JSON", "no", stack_callback=conda_tests_ctxt_mgmt_def_pol):
            with captured() as c:
                conda_exception_handler(_raise_helper, exc)

        assert not c.stdout
        assert c.stderr.strip() == dals("""
        BinaryPrefixReplacementError: Refusing to replace mismatched data length in binary file.
          path: some/where/by/boneyard/creek
          placeholder: save/my/spot/in/374
          new prefix: some/where/on/goodwin.ave
          original data Length: 1404
          new data length: 1104
        """).strip()
