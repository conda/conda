# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import getpass
import json
import sys
from contextlib import nullcontext
from datetime import timedelta
from unittest.mock import patch

import pytest
import requests
from pytest import CaptureFixture, MonkeyPatch
from pytest_mock import MockerFixture
from conda.common.io import dashlist

from conda.auxlib.collection import AttrDict
from conda.base.constants import PathConflict
from conda.base.context import context, reset_context
from conda.exceptions import (
    BasicClobberError,
    BinaryPrefixReplacementError,
    ChecksumMismatchError,
    CommandNotFoundError,
    CondaHTTPError,
    CondaKeyError,
    CondaValueError,
    DirectoryNotFoundError,
    ExceptionHandler,
    KnownPackageClobberError,
    PackagesNotFoundError,
    PathNotFoundError,
    PlatformMismatchError,
    ProxyError,
    RemoveError,
    SharedLinkPathClobberError,
    TooManyArgumentsError,
    UnavailableInvalidChannel,
    UnknownPackageClobberError,
    UnsatisfiableError,
    conda_exception_handler,
    print_conda_exception,
)


def _raise_helper(exception):
    raise exception


def username_not_in_post_mock(post_mock, username):
    for cal in post_mock.call_args_list:
        for call_part in cal:
            if username in str(call_part):
                return False
    return True


def test_TooManyArgumentsError(
    monkeypatch: MonkeyPatch,
    capsys: CaptureFixture,
) -> None:
    expected = 2
    received = 5
    offending_arguments = "groot"
    exc = TooManyArgumentsError(expected, received, offending_arguments)

    monkeypatch.setenv("CONDA_JSON", "yes")
    reset_context()
    assert context.json

    conda_exception_handler(_raise_helper, exc)
    stdout, stderr = capsys.readouterr()

    json_obj = json.loads(stdout)
    assert not stderr
    assert (
        json_obj["exception_type"] == "<class 'conda.exceptions.TooManyArgumentsError'>"
    )
    assert json_obj["exception_name"] == "TooManyArgumentsError"
    assert json_obj["message"] == str(exc)
    assert json_obj["error"] == repr(exc)
    assert json_obj["expected"] == 2
    assert json_obj["received"] == 5
    assert json_obj["offending_arguments"] == "groot"

    monkeypatch.setenv("CONDA_JSON", "no")
    reset_context()
    assert not context.json

    conda_exception_handler(_raise_helper, exc)
    stdout, stderr = capsys.readouterr()

    assert not stdout
    assert stderr == "\n".join(
        (
            "",
            "TooManyArgumentsError:  Got 5 arguments (g, r, o, o, t) but expected 2.",
            "",
            "",
        )
    )


def test_BasicClobberError(monkeypatch: MonkeyPatch, capsys: CaptureFixture) -> None:
    source_path = "some/path/on/goodwin.ave"
    target_path = "some/path/to/wright.st"
    exc = BasicClobberError(source_path, target_path, context)

    monkeypatch.setenv("CONDA_PATH_CONFLICT", "prevent")
    reset_context()
    assert context.path_conflict == PathConflict.prevent

    conda_exception_handler(_raise_helper, exc)
    stdout, stderr = capsys.readouterr()

    assert not stdout
    assert stderr == "\n".join(
        (
            "",
            "ClobberError: Conda was asked to clobber an existing path.",
            "  source path: some/path/on/goodwin.ave",
            "  target path: some/path/to/wright.st",
            "",
            "",
            "",
            "",
        )
    )


def test_KnownPackageClobberError(
    monkeypatch: MonkeyPatch,
    capsys: CaptureFixture,
) -> None:
    target_path = "some/where/on/goodwin.ave"
    colliding_dist_being_linked = "Groot"
    colliding_linked_dist = "Liquid"
    exc = KnownPackageClobberError(
        target_path, colliding_dist_being_linked, colliding_linked_dist, context
    )

    monkeypatch.setenv("CONDA_PATH_CONFLICT", "prevent")
    reset_context()
    assert context.path_conflict == PathConflict.prevent

    conda_exception_handler(_raise_helper, exc)
    stdout, stderr = capsys.readouterr()

    assert not stdout
    assert stderr == "\n".join(
        (
            "",
            "ClobberError: The package 'Groot' cannot be installed due to a",
            "path collision for 'some/where/on/goodwin.ave'.",
            "This path already exists in the target prefix, and it won't be removed by",
            "an uninstall action in this transaction. The path appears to be coming from",
            "the package 'Liquid', which is already installed in the prefix.",
            "",
            "",
            "",
            "",
        )
    )


def test_UnknownPackageClobberError(
    monkeypatch: MonkeyPatch,
    capsys: CaptureFixture,
) -> None:
    target_path = "siebel/center/for/c.s"
    colliding_dist_being_linked = "Groot"
    exc = UnknownPackageClobberError(target_path, colliding_dist_being_linked, context)

    monkeypatch.setenv("CONDA_PATH_CONFLICT", "prevent")
    reset_context()
    assert context.path_conflict == PathConflict.prevent

    conda_exception_handler(_raise_helper, exc)
    stdout, stderr = capsys.readouterr()

    assert not stdout
    assert stderr == "\n".join(
        (
            "",
            "ClobberError: The package 'Groot' cannot be installed due to a",
            "path collision for 'siebel/center/for/c.s'.",
            "This path already exists in the target prefix, and it won't be removed",
            "by an uninstall action in this transaction. The path is one that conda",
            "doesn't recognize. It may have been created by another package manager.",
            "",
            "",
            "",
            "",
        )
    )


def test_SharedLinkPathClobberError(
    monkeypatch: MonkeyPatch,
    capsys: CaptureFixture,
) -> None:
    target_path = "some/where/in/shampoo/banana"
    incompatible_package_dists = "Groot"
    exc = SharedLinkPathClobberError(target_path, incompatible_package_dists, context)

    monkeypatch.setenv("CONDA_PATH_CONFLICT", "prevent")
    reset_context()
    assert context.path_conflict == PathConflict.prevent

    conda_exception_handler(_raise_helper, exc)
    stdout, stderr = capsys.readouterr()

    assert not stdout
    assert stderr == "\n".join(
        (
            "",
            "ClobberError: This transaction has incompatible packages due to a shared path.",
            "  packages: G, r, o, o, t",
            "  path: 'some/where/in/shampoo/banana'",
            "",
            "",
            "",
            "",
        )
    )


def test_CondaFileNotFoundError(
    monkeypatch: MonkeyPatch,
    capsys: CaptureFixture,
) -> None:
    filename = "Groot"
    exc = PathNotFoundError(filename)

    monkeypatch.setenv("CONDA_JSON", "yes")
    reset_context()
    assert context.json

    conda_exception_handler(_raise_helper, exc)
    stdout, stderr = capsys.readouterr()

    json_obj = json.loads(stdout)
    assert not stderr
    assert json_obj["exception_type"] == "<class 'conda.exceptions.PathNotFoundError'>"
    assert json_obj["exception_name"] == "PathNotFoundError"
    assert json_obj["message"] == str(exc)
    assert json_obj["error"] == repr(exc)

    monkeypatch.setenv("CONDA_JSON", "no")
    reset_context()
    assert not context.json

    conda_exception_handler(_raise_helper, exc)
    stdout, stderr = capsys.readouterr()

    assert not stdout
    assert stderr == "\n".join(("", "PathNotFoundError: Groot", "", ""))


def test_DirectoryNotFoundError(
    monkeypatch: MonkeyPatch,
    capsys: CaptureFixture,
) -> None:
    directory = "Groot"
    exc = DirectoryNotFoundError(directory)

    monkeypatch.setenv("CONDA_JSON", "yes")
    reset_context()
    assert context.json

    conda_exception_handler(_raise_helper, exc)
    stdout, stderr = capsys.readouterr()

    json_obj = json.loads(stdout)
    assert not stderr
    assert (
        json_obj["exception_type"]
        == "<class 'conda.exceptions.DirectoryNotFoundError'>"
    )
    assert json_obj["exception_name"] == "DirectoryNotFoundError"
    assert json_obj["message"] == str(exc)
    assert json_obj["error"] == repr(exc)
    assert json_obj["path"] == "Groot"

    monkeypatch.setenv("CONDA_JSON", "no")
    reset_context()
    assert not context.json

    conda_exception_handler(_raise_helper, exc)
    stdout, stderr = capsys.readouterr()

    assert not stdout
    assert stderr == "\n".join(("", "DirectoryNotFoundError: Groot", "", ""))


def test_MD5MismatchError(monkeypatch: MonkeyPatch, capsys: CaptureFixture) -> None:
    url = "https://download.url/path/to/file.tar.bz2"
    target_full_path = "/some/path/on/disk/another-name.tar.bz2"
    expected_md5sum = "abc123"
    actual_md5sum = "deadbeef"
    exc = ChecksumMismatchError(
        url, target_full_path, "md5", expected_md5sum, actual_md5sum
    )

    monkeypatch.setenv("CONDA_JSON", "yes")
    reset_context()
    assert context.json

    conda_exception_handler(_raise_helper, exc)
    stdout, stderr = capsys.readouterr()

    json_obj = json.loads(stdout)
    assert not stderr
    assert (
        json_obj["exception_type"] == "<class 'conda.exceptions.ChecksumMismatchError'>"
    )
    assert json_obj["exception_name"] == "ChecksumMismatchError"
    assert json_obj["message"] == str(exc)
    assert json_obj["error"] == repr(exc)
    assert json_obj["url"] == url
    assert json_obj["target_full_path"] == target_full_path
    assert json_obj["expected_checksum"] == expected_md5sum
    assert json_obj["actual_checksum"] == actual_md5sum

    monkeypatch.setenv("CONDA_JSON", "no")
    reset_context()
    assert not context.json

    conda_exception_handler(_raise_helper, exc)
    stdout, stderr = capsys.readouterr()

    assert not stdout
    assert stderr == "\n".join(
        (
            "",
            "ChecksumMismatchError: Conda detected a mismatch between the expected content and downloaded content",
            "for url 'https://download.url/path/to/file.tar.bz2'.",
            "  download saved to: /some/path/on/disk/another-name.tar.bz2",
            "  expected md5: abc123",
            "  actual md5: deadbeef",
            "",
            "",
            "",
        )
    )


def test_PackageNotFoundError(monkeypatch: MonkeyPatch, capsys: CaptureFixture) -> None:
    package = "Potato"
    exc = PackagesNotFoundError((package,))

    monkeypatch.setenv("CONDA_JSON", "yes")
    reset_context()
    assert context.json

    conda_exception_handler(_raise_helper, exc)
    stdout, stderr = capsys.readouterr()

    json_obj = json.loads(stdout)
    assert not stderr
    assert (
        json_obj["exception_type"] == "<class 'conda.exceptions.PackagesNotFoundError'>"
    )
    assert json_obj["message"] == str(exc)
    assert json_obj["error"] == repr(exc)

    monkeypatch.setenv("CONDA_JSON", "no")
    reset_context()
    assert not context.json

    conda_exception_handler(_raise_helper, exc)
    stdout, stderr = capsys.readouterr()

    assert not stdout
    assert stderr == "\n".join(
        (
            "",
            "PackagesNotFoundError: The following packages are missing from the target environment:",
            "",
            "  - Potato",
            "",
            "",
            "",
        )
    )


def test_CondaKeyError(monkeypatch: MonkeyPatch, capsys: CaptureFixture) -> None:
    key = "Potato"
    message = "Potato is not a key."
    exc = CondaKeyError(key, message)

    monkeypatch.setenv("CONDA_JSON", "yes")
    reset_context()
    assert context.json

    conda_exception_handler(_raise_helper, exc)
    stdout, stderr = capsys.readouterr()

    json_obj = json.loads(stdout)
    assert not stderr
    assert json_obj["exception_type"] == "<class 'conda.exceptions.CondaKeyError'>"
    assert json_obj["exception_name"] == "CondaKeyError"
    assert json_obj["message"] == str(exc)
    assert json_obj["error"] == repr(exc)
    assert json_obj["key"] == "Potato"

    monkeypatch.setenv("CONDA_JSON", "no")
    reset_context()
    assert not context.json

    conda_exception_handler(_raise_helper, exc)
    stdout, stderr = capsys.readouterr()

    assert not stdout
    assert stderr == "\n".join(
        ("", "CondaKeyError: 'Potato': Potato is not a key.", "", "")
    )


def test_CondaHTTPError(monkeypatch: MonkeyPatch, capsys: CaptureFixture) -> None:
    msg = "Potato"
    url = "https://download.url/path/to/Potato.tar.gz"
    status_code = "Potato"
    reason = "COULD NOT CONNECT"
    elapsed_time = 1.24
    exc = CondaHTTPError(msg, url, status_code, reason, elapsed_time)

    monkeypatch.setenv("CONDA_JSON", "yes")
    reset_context()
    assert context.json

    conda_exception_handler(_raise_helper, exc)
    stdout, stderr = capsys.readouterr()

    json_obj = json.loads(stdout)
    assert not stderr
    assert json_obj["exception_type"] == "<class 'conda.exceptions.CondaHTTPError'>"
    assert json_obj["exception_name"] == "CondaHTTPError"
    assert json_obj["message"] == str(exc)
    assert json_obj["error"] == repr(exc)
    assert json_obj["url"] == url
    assert json_obj["status_code"] == status_code
    assert json_obj["reason"] == reason
    assert json_obj["elapsed_time"] == elapsed_time

    monkeypatch.setenv("CONDA_JSON", "no")
    reset_context()
    assert not context.json

    conda_exception_handler(_raise_helper, exc)
    stdout, stderr = capsys.readouterr()

    assert not stdout
    assert stderr == "\n".join(
        (
            "",
            "CondaHTTPError: HTTP Potato COULD NOT CONNECT for url <https://download.url/path/to/Potato.tar.gz>",
            "Elapsed: 1.24",
            "",
            "Potato",
            "",
            "",
        )
    )


def test_http_error_custom_reason_code(
    monkeypatch: MonkeyPatch, capsys: CaptureFixture
) -> None:
    msg = ""
    url = "https://download.url/path/to/something.tar.gz"
    status_code = "403"
    reason = "-->>> Requested item is quarantined -->>> FOR DETAILS SEE -->>> https://someurl/foo <<<------"
    elapsed_time = 1.25
    exc = CondaHTTPError(msg, url, status_code, reason, elapsed_time)

    monkeypatch.setenv("CONDA_JSON", "yes")
    reset_context()
    assert context.json

    conda_exception_handler(_raise_helper, exc)
    stdout, stderr = capsys.readouterr()

    json_obj = json.loads(stdout)
    assert not stderr
    assert json_obj["exception_type"] == "<class 'conda.exceptions.CondaHTTPError'>"
    assert json_obj["exception_name"] == "CondaHTTPError"
    assert json_obj["message"] == str(exc)
    assert json_obj["error"] == repr(exc)
    assert json_obj["url"] == url
    assert json_obj["status_code"] == status_code
    assert json_obj["reason"] == reason
    assert json_obj["elapsed_time"] == elapsed_time

    monkeypatch.setenv("CONDA_JSON", "no")
    reset_context()
    assert not context.json

    conda_exception_handler(_raise_helper, exc)
    stdout, stderr = capsys.readouterr()

    assert not stdout
    assert stderr == "\n".join(
        (
            "",
            "CondaHTTPError: HTTP 403 -->>> Requested item is quarantined -->>> FOR DETAILS SEE -->>> https://someurl/foo <<<------ for url <https://download.url/path/to/something.tar.gz>",
            "Elapsed: 1.25",
            "",
            "",
            "",
            "",
        )
    )


def test_http_error_rfc_9457(monkeypatch: MonkeyPatch, capsys: CaptureFixture) -> None:
    msg = ""
    url = "https://download.url/path/to/something.tar.gz"
    status_code = "403"
    # in HTTP/2, reason will be empty
    reason = ""
    # in a RFC 9457 compliant response, the "detail" field is what we want to capture
    detail = "-->>> Requested item is quarantined -->>> FOR DETAILS SEE -->>> https://someurl/foo <<<------"

    # Create a mock Response object
    class MockResponse:
        def __init__(self, json_data):
            self.json_data = json_data
            self.headers = {"content-type": "application/problem+json"}

        def json(self):
            return self.json_data

    # Create the response with a detail field
    response = MockResponse({"detail": detail})

    elapsed_time = 1.26
    exc = CondaHTTPError(
        msg, url, status_code, reason, timedelta(seconds=elapsed_time), response
    )

    monkeypatch.setenv("CONDA_JSON", "yes")
    reset_context()

    conda_exception_handler(_raise_helper, exc)
    stdout, stderr = capsys.readouterr()

    json_obj = json.loads(stdout)
    assert not stderr
    assert json_obj["json"]["detail"] == detail

    monkeypatch.setenv("CONDA_JSON", "no")
    reset_context()
    assert not context.json

    conda_exception_handler(_raise_helper, exc)
    stdout, stderr = capsys.readouterr()

    assert not stdout
    assert stderr == "\n".join(
        (
            "",
            "CondaHTTPError: HTTP 403 CONNECTION FAILED for url <https://download.url/path/to/something.tar.gz>",
            "Elapsed: 00:01.260000",
            "",
            detail,
            "",
            "",
        )
    )


def test_http_error_rfc_9457_non_string_detail(
    monkeypatch: MonkeyPatch, capsys: CaptureFixture
) -> None:
    """
    CondaHTTPError should ignore 'detail' when the response is not an RFC 9457
    application/problem+json response. Frameworks such as FastAPI use 'detail'
    for non-string values (say, a list of validation error objects), so we must
    not read it unless the content type is indicative of an RFC 9457 response.
    """
    msg = ""
    url = "https://example.com/channel/linux-64/repodata.json"
    status_code = "422"
    reason = "Unprocessable Content"
    # FastAPI returns 'detail' as a list of validation error objects, not a string
    detail = [{"loc": ["path", "filename"], "msg": "value is not a valid enum member"}]

    class MockResponse:
        def __init__(self, json_data):
            self.json_data = json_data
            self.headers = {"content-type": "application/json"}

        def json(self):
            return self.json_data

    response = MockResponse({"detail": detail})
    exc = CondaHTTPError(
        msg, url, status_code, reason, timedelta(seconds=0.1), response
    )

    monkeypatch.setenv("CONDA_JSON", "no")
    reset_context()

    conda_exception_handler(_raise_helper, exc)
    stdout, stderr = capsys.readouterr()

    assert not stdout
    assert str(detail) not in stderr


@pytest.mark.parametrize(
    "error_class",
    [
        json.JSONDecodeError,
        ValueError,
        requests.exceptions.JSONDecodeError,
    ],
)
def test_non_json_response_body(error_class: type) -> None:
    """UnavailableInvalidChannel and CondaHTTPError handle non-JSON responses.

    Regression test for #16136: when simplejson is installed,
    response.json() raises requests.exceptions.JSONDecodeError which
    inherits from simplejson.JSONDecodeError (a ValueError), not from
    json.JSONDecodeError (stdlib).
    """

    class MockResponse:
        reason = "Not Found"
        headers = {}

        def json(self):
            raise error_class("bad", "", 0)

    response = MockResponse()

    exc = UnavailableInvalidChannel("test-channel", 404, response=response)
    assert exc.status_code == 404

    CondaHTTPError("msg", "https://x", 404, "Not Found", "0:01", response)


def test_CommandNotFoundError_simple(
    monkeypatch: MonkeyPatch,
    capsys: CaptureFixture,
) -> None:
    cmd = "instate"
    with pytest.deprecated_call():
        exc = CommandNotFoundError(cmd)

    monkeypatch.setenv("CONDA_JSON", "yes")
    reset_context()
    assert context.json

    conda_exception_handler(_raise_helper, exc)
    stdout, stderr = capsys.readouterr()

    json_obj = json.loads(stdout)
    assert not stderr
    assert (
        json_obj["exception_type"] == "<class 'conda.exceptions.CommandNotFoundError'>"
    )
    assert json_obj["message"] == str(exc)
    assert json_obj["error"] == repr(exc)

    monkeypatch.setenv("CONDA_JSON", "no")
    reset_context()
    assert not context.json

    conda_exception_handler(_raise_helper, exc)
    stdout, stderr = capsys.readouterr()

    assert not stdout
    assert stderr == "\n".join(
        (
            "",
            "CommandNotFoundError: No command 'conda instate'.",
            "Did you mean 'conda install'?",
            "",
            "",
        )
    )


def test_CommandNotFoundError_conda_build(
    monkeypatch: MonkeyPatch,
    capsys: CaptureFixture,
) -> None:
    cmd = "build"
    with pytest.deprecated_call():
        exc = CommandNotFoundError(cmd)

    monkeypatch.setenv("CONDA_JSON", "yes")
    reset_context()
    assert context.json

    conda_exception_handler(_raise_helper, exc)
    stdout, stderr = capsys.readouterr()

    json_obj = json.loads(stdout)
    assert not stderr
    assert (
        json_obj["exception_type"] == "<class 'conda.exceptions.CommandNotFoundError'>"
    )
    assert json_obj["message"] == str(exc)
    assert json_obj["error"] == repr(exc)

    monkeypatch.setenv("CONDA_JSON", "no")
    reset_context()
    assert not context.json

    conda_exception_handler(_raise_helper, exc)
    stdout, stderr = capsys.readouterr()

    assert not stdout
    assert stderr == "\n".join(
        (
            "",
            "CommandNotFoundError: To use 'conda build', install conda-build.",
            "",
            "",
        )
    )


def test_print_unexpected_error_message_upload_1(
    mocker: MockerFixture,
    monkeypatch: MonkeyPatch,
    capsys: CaptureFixture,
):
    """
    Test that error reports are not submitted when CONDA_REPORT_ERRORS=true.
    """
    post_mock = mocker.patch(
        "requests.post",
        side_effect=(
            AttrDict(
                headers=AttrDict(Location="somewhere.else"),
                status_code=302,
                raise_for_status=lambda: None,
            ),
            AttrDict(raise_for_status=lambda: None),
        ),
    )

    monkeypatch.setenv("CONDA_REPORT_ERRORS", "true")
    monkeypatch.setenv("CONDA_ALWAYS_YES", "false")
    monkeypatch.setenv("CONDA_JSON", "false")
    reset_context()
    with pytest.deprecated_call():
        assert context.report_errors is True
    assert not context.json
    assert not context.always_yes

    ExceptionHandler()(_raise_helper, AssertionError())
    stdout, stderr = capsys.readouterr()

    assert username_not_in_post_mock(post_mock, getpass.getuser())
    assert post_mock.call_count == 0
    assert not stdout
    assert "conda version" in stderr


def test_print_unexpected_error_message_upload_2(
    mocker: MockerFixture,
    monkeypatch: MonkeyPatch,
    capsys: CaptureFixture,
):
    """
    Test that error reports are not submitted when CONDA_ALWAYS_YES=true. Also
    test that we do not receive the error report in as a JSON when CONDA_JSON=true.
    """
    post_mock = mocker.patch(
        "requests.post",
        side_effect=(
            AttrDict(
                headers=AttrDict(Location="somewhere.else"),
                status_code=302,
                raise_for_status=lambda: None,
            ),
            AttrDict(
                headers=AttrDict(Location="somewhere.again"),
                status_code=301,
                raise_for_status=lambda: None,
            ),
            AttrDict(raise_for_status=lambda: None),
        ),
    )

    monkeypatch.setenv("CONDA_REPORT_ERRORS", "none")
    monkeypatch.setenv("CONDA_ALWAYS_YES", "true")
    monkeypatch.setenv("CONDA_JSON", "true")
    reset_context()
    with pytest.deprecated_call():
        assert context.report_errors is None
    assert context.json
    assert context.always_yes

    ExceptionHandler()(_raise_helper, AssertionError())
    stdout, stderr = capsys.readouterr()

    assert username_not_in_post_mock(post_mock, getpass.getuser())
    assert post_mock.call_count == 0
    assert len(json.loads(stdout)["conda_info"]["channels"]) >= 2
    assert not stderr


def test_print_unexpected_error_message_upload_3(
    mocker: MockerFixture,
    monkeypatch: MonkeyPatch,
    capsys: CaptureFixture,
):
    """
    Test that we no longer prompt for user confirmation since error reporting
    functionality has been removed.
    """
    post_mock = mocker.patch("requests.post")
    input_mock = mocker.patch("builtins.input")
    isatty_mock = mocker.patch("os.isatty")

    monkeypatch.setenv("CONDA_REPORT_ERRORS", "none")
    monkeypatch.setenv("CONDA_ALWAYS_YES", "false")
    monkeypatch.setenv("CONDA_JSON", "false")
    reset_context()
    with pytest.deprecated_call():
        assert context.report_errors is None
    assert not context.json
    assert not context.always_yes

    ExceptionHandler()(_raise_helper, AssertionError())
    stdout, stderr = capsys.readouterr()

    assert username_not_in_post_mock(post_mock, username=getpass.getuser())
    assert isatty_mock.call_count == 0
    assert input_mock.call_count == 0
    assert post_mock.call_count == 0
    assert not stdout
    assert "conda version" in stderr


@patch("requests.post", return_value=None)
@patch("builtins.input", return_value="n")
def test_print_unexpected_error_message_opt_out_1(
    mocker: MockerFixture,
    monkeypatch: MonkeyPatch,
    capsys: CaptureFixture,
) -> None:
    """Test that error reports are not submitted when report_errors is false."""
    input_mock = mocker.patch("builtins.input")
    post_mock = mocker.patch("requests.post")

    monkeypatch.setenv("CONDA_REPORT_ERRORS", "false")
    reset_context()
    with pytest.deprecated_call():
        assert not context.report_errors

    ExceptionHandler()(_raise_helper, AssertionError())
    stdout, stderr = capsys.readouterr()

    assert input_mock.call_count == 0
    assert post_mock.call_count == 0
    assert stdout == ""
    print(stderr, file=sys.stderr)
    assert "conda version" in stderr


@patch("requests.post", return_value=None)
@patch("builtins.input", return_value="n")
@patch("os.isatty", return_value=True)
def test_print_unexpected_error_message_opt_out_2(
    isatty_mock,
    input_mock,
    post_mock,
    capsys: CaptureFixture,
):
    ExceptionHandler()(_raise_helper, AssertionError())
    stdout, stderr = capsys.readouterr()

    # Since error submission was removed, no prompts should occur
    assert input_mock.call_count == 0
    assert post_mock.call_count == 0
    assert stdout == ""
    assert "conda version" in stderr


def test_BinaryPrefixReplacementError(
    monkeypatch: MonkeyPatch,
    capsys: CaptureFixture,
) -> None:
    new_data_length = 1104
    original_data_length = 1404
    new_prefix = "some/where/on/goodwin.ave"
    path = "some/where/by/boneyard/creek"
    placeholder = "save/my/spot/in/374"
    exc = BinaryPrefixReplacementError(
        path, placeholder, new_prefix, original_data_length, new_data_length
    )

    monkeypatch.setenv("CONDA_JSON", "yes")
    reset_context()
    assert context.json

    conda_exception_handler(_raise_helper, exc)
    stdout, stderr = capsys.readouterr()

    json_obj = json.loads(stdout)
    assert not stderr
    assert (
        json_obj["exception_type"]
        == "<class 'conda.exceptions.BinaryPrefixReplacementError'>"
    )
    assert json_obj["exception_name"] == "BinaryPrefixReplacementError"
    assert json_obj["message"] == str(exc)
    assert json_obj["error"] == repr(exc)
    assert json_obj["new_data_length"] == 1104
    assert json_obj["original_data_length"] == 1404
    assert json_obj["new_prefix"] == new_prefix
    assert json_obj["path"] == path
    assert json_obj["placeholder"] == placeholder

    monkeypatch.setenv("CONDA_JSON", "no")
    reset_context()
    assert not context.json

    conda_exception_handler(_raise_helper, exc)
    stdout, stderr = capsys.readouterr()

    assert not stdout
    assert stderr == "\n".join(
        (
            "",
            "BinaryPrefixReplacementError: Refusing to replace mismatched data length in binary file.",
            "  path: some/where/by/boneyard/creek",
            "  placeholder: save/my/spot/in/374",
            "  new prefix: some/where/on/goodwin.ave",
            "  original data Length: 1404",
            "  new data length: 1104",
            "",
            "",
            "",
        )
    )


def test_RemoveError_with_guidance() -> None:
    exc = RemoveError(
        "legacy message",
        guidance={
            "summary": (summary := "Guidance summary."),
            "cause": (cause := "Root cause."),
            "hints": [
                {
                    "text": (text := "Do the thing."),
                    "hint_code": (hint_code := "do_the_thing"),
                },
            ],
        },
    )
    assert exc.guidance is not None
    assert exc.guidance.summary == summary
    assert exc.guidance.cause == cause
    assert len(exc.guidance.hints) == 1
    assert exc.guidance.hints[0].text == text
    assert exc.guidance.hints[0].hint_code == hint_code


def test_RemoveError_without_guidance() -> None:
    exc = RemoveError("legacy message")
    assert exc.guidance is None


def test_RemoveError_guidance_in_dump_map() -> None:
    exc = RemoveError(
        "legacy message",
        guidance={
            "summary": (summary := "Guidance summary."),
            "cause": (cause := "Root cause."),
            "hints": [
                {
                    "text": (text := "Do the thing."),
                    "hint_code": (hint_code := "do_the_thing"),
                },
            ],
        },
    )
    assert exc.dump_map()["guidance"] == {
        "summary": summary,
        "cause": cause,
        "hints": ({"text": text, "hint_code": hint_code},),
        "hint_codes": (hint_code,),
    }


def test_RemoveError_without_guidance_dump_map_no_key() -> None:
    exc = RemoveError("legacy message")
    assert "guidance" not in exc.dump_map()


def test_RemoveError_str_unchanged_with_guidance() -> None:
    """__str__ should remain the legacy message, not the guidance."""
    exc = RemoveError(
        (message := "legacy message"),
        guidance={"summary": "Guidance summary."},
    )
    assert str(exc) == message


def test_print_conda_exception_with_guidance(
    monkeypatch: MonkeyPatch,
    capsys: CaptureFixture,
) -> None:
    monkeypatch.setenv("CONDA_JSON", "no")
    reset_context()
    assert not context.json

    exc = RemoveError(
        "legacy message",
        guidance={
            "summary": (summary := "Guidance summary."),
            "cause": (cause := "Root cause."),
            "hints": [{"text": (text := "Do the thing."), "hint_code": (hint_code := "do_the_thing"),}],
        },
    )
    print_conda_exception(exc)
    err = capsys.readouterr().err
    assert err == f"\nRemoveError: {summary}\n\nCause: {cause}\nNext steps:\n  - ({hint_code}) {text}\n\n"


def test_print_conda_exception_without_guidance(
    monkeypatch: MonkeyPatch,
    capsys: CaptureFixture,
) -> None:
    monkeypatch.setenv("CONDA_JSON", "no")
    reset_context()
    assert not context.json

    exc = RemoveError(message := "legacy message")
    # Use a context manager to avoid issues with the exception_handler
    print_conda_exception(exc)
    err = capsys.readouterr().err
    assert err == f"\nRemoveError: {message}\n\n"


def test_PackagesNotFoundError_guidance_for_bulk_missing(
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("CONDA_USE_ONLY_TAR_BZ2", "false")
    reset_context()
    assert not context.use_only_tar_bz2

    pkgs = [f"pkg{i}" for i in range(5)]
    exc = PackagesNotFoundError(
        pkgs,
        channel_urls=["https://repo.anaconda.org/pkgs/main"],
    )
    assert exc.guidance is not None
    assert "Many packages are unavailable" in exc.guidance.summary
    assert exc.guidance.hints[0].hint_code == "check_channel_config"


def test_PackagesNotFoundError_no_guidance_for_few_packages(
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setenv("CONDA_USE_ONLY_TAR_BZ2", "false")
    reset_context()
    assert not context.use_only_tar_bz2

    exc = PackagesNotFoundError(
        ["single-pkg"],
        channel_urls=["https://repo.anaconda.org/pkgs/main"],
    )
    assert exc.guidance is None


def test_UnsatisfiableError_guidance() -> None:
    exc = UnsatisfiableError({})
    assert exc.guidance is not None
    assert "could not find a compatible set" in exc.guidance.summary


@pytest.mark.parametrize("use_only_tar_bz2", [True, False])
def test_PackagesNotFoundError_use_only_tar_bz2(
    monkeypatch: MonkeyPatch,
    use_only_tar_bz2: bool,
) -> None:
    monkeypatch.setenv("CONDA_USE_ONLY_TAR_BZ2", str(use_only_tar_bz2))
    reset_context()
    assert context.use_only_tar_bz2 is use_only_tar_bz2

    with pytest.raises(
        PackagesNotFoundError,
        match="use_only_tar_bz2" if use_only_tar_bz2 else "",
    ):
        raise PackagesNotFoundError(
            packages=["does-not-exist"],
            channel_urls=["https://repo.anaconda.org/pkgs/main"],
        )


def test_proxy_error_default_message() -> None:
    """Test ProxyError with default and custom messages."""
    # Test default message
    exc_default = ProxyError()
    default_message = str(exc_default)
    assert "proxy configuration" in default_message
    assert ".netrc" in default_message
    assert "_PROXY" in default_message


def test_proxy_error_custom_message() -> None:
    """Test ProxyError with custom message."""
    custom_message = "Could not find a proxy for 'https'. Custom error message."
    exc_custom = ProxyError(custom_message)
    assert str(exc_custom) == custom_message

    assert str(ProxyError()) != str(exc_custom)


@pytest.mark.parametrize(
    "function,raises",
    [("error_upload_url", TypeError)],
)
def test_ExceptionHandler_deprecations(
    function: str, raises: type[Exception] | None
) -> None:
    raises_context = pytest.raises(raises) if raises else nullcontext()
    with pytest.deprecated_call(), raises_context:
        getattr(ExceptionHandler(), function)()


def test_platform_mismatch_error_is_conda_value_error() -> None:
    """`PlatformMismatchError` is a `CondaValueError` so existing handlers keep working."""
    exc = PlatformMismatchError([("env.yml", ("osx-64",))], "linux-64")
    assert isinstance(exc, CondaValueError)


@pytest.mark.parametrize(
    "sources,subdir,expected_fragments",
    [
        pytest.param(
            [("env.yml", ("osx-64", "osx-arm64"))],
            "linux-64",
            (
                "Environment file 'env.yml' does not include packages for linux-64",
                "Available platforms: osx-64, osx-arm64",
                "regenerate the environment file with linux-64",
                "    conda export --file env.yml "
                "--platform osx-64 --platform osx-arm64 --platform linux-64",
            ),
            id="single-source",
        ),
        pytest.param(
            [("a.yml", ("osx-64",)), ("b.yml", ("win-64", "linux-aarch64"))],
            "linux-64",
            (
                "The following environment files do not include packages for linux-64",
                "'a.yml': osx-64",
                "'b.yml': win-64, linux-aarch64",
                "Regenerate each file with linux-64",
                "--platform linux-64",
            ),
            id="multiple-sources",
        ),
    ],
)
def test_platform_mismatch_error_message(
    sources: list[tuple[str, tuple[str, ...]]],
    subdir: str,
    expected_fragments: tuple[str, ...],
) -> None:
    """Error message names every incompatible source and advises regenerating it."""
    message = str(PlatformMismatchError(sources, subdir))
    for fragment in expected_fragments:
        assert fragment in message
