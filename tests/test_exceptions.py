# Copyright (C) 2012 Anaconda, Inc
# SPDX-License-Identifier: BSD-3-Clause
import getpass
import json
import sys
from unittest.mock import patch

from pytest import CaptureFixture, MonkeyPatch, raises
from pytest_mock import MockerFixture

from conda.auxlib.collection import AttrDict
from conda.auxlib.ish import dals
from conda.base.context import conda_tests_ctxt_mgmt_def_pol, context, reset_context
from conda.common.io import captured, env_var, env_vars
from conda.exceptions import (
    BasicClobberError,
    BinaryPrefixReplacementError,
    ChecksumMismatchError,
    CommandNotFoundError,
    CondaHTTPError,
    CondaKeyError,
    DirectoryNotFoundError,
    ExceptionHandler,
    KnownPackageClobberError,
    PackagesNotFoundError,
    PathNotFoundError,
    SharedLinkPathClobberError,
    TooManyArgumentsError,
    UnknownPackageClobberError,
    conda_exception_handler,
)


def _raise_helper(exception):
    raise exception


def username_not_in_post_mock(post_mock, username):
    for cal in post_mock.call_args_list:
        for call_part in cal:
            if username in str(call_part):
                return False
    return True


def test_TooManyArgumentsError():
    expected = 2
    received = 5
    offending_arguments = "groot"
    exc = TooManyArgumentsError(expected, received, offending_arguments)
    with env_var("CONDA_JSON", "yes", stack_callback=conda_tests_ctxt_mgmt_def_pol):
        with captured() as c:
            conda_exception_handler(_raise_helper, exc)

    json_obj = json.loads(c.stdout)
    assert not c.stderr
    assert (
        json_obj["exception_type"] == "<class 'conda.exceptions.TooManyArgumentsError'>"
    )
    assert json_obj["exception_name"] == "TooManyArgumentsError"
    assert json_obj["message"] == str(exc)
    assert json_obj["error"] == repr(exc)
    assert json_obj["expected"] == 2
    assert json_obj["received"] == 5
    assert json_obj["offending_arguments"] == "groot"

    with env_var("CONDA_JSON", "no", stack_callback=conda_tests_ctxt_mgmt_def_pol):
        with captured() as c:
            conda_exception_handler(_raise_helper, exc)

    assert not c.stdout
    assert (
        c.stderr.strip()
        == "TooManyArgumentsError:  Got 5 arguments (g, r, o, o, t) but expected 2."
    )


def test_BasicClobberError():
    source_path = "some/path/on/goodwin.ave"
    target_path = "some/path/to/wright.st"
    exc = BasicClobberError(source_path, target_path, context)
    repr(exc)
    with env_var(
        "CONDA_PATH_CONFLICT",
        "prevent",
        stack_callback=conda_tests_ctxt_mgmt_def_pol,
    ):
        with captured() as c:
            conda_exception_handler(_raise_helper, exc)

    assert not c.stdout
    assert (
        c.stderr.strip()
        == dals(
            """
    ClobberError: Conda was asked to clobber an existing path.
      source path: some/path/on/goodwin.ave
      target path: some/path/to/wright.st
    """
        ).strip()
    )


def test_KnownPackageClobberError():
    target_path = "some/where/on/goodwin.ave"
    colliding_dist_being_linked = "Groot"
    colliding_linked_dist = "Liquid"
    exc = KnownPackageClobberError(
        target_path, colliding_dist_being_linked, colliding_linked_dist, context
    )
    with env_var(
        "CONDA_PATH_CONFLICT",
        "prevent",
        stack_callback=conda_tests_ctxt_mgmt_def_pol,
    ):
        with captured() as c:
            conda_exception_handler(_raise_helper, exc)

    assert not c.stdout
    assert (
        c.stderr.strip()
        == dals(
            """
    ClobberError: The package 'Groot' cannot be installed due to a
    path collision for 'some/where/on/goodwin.ave'.
    This path already exists in the target prefix, and it won't be removed by
    an uninstall action in this transaction. The path appears to be coming from
    the package 'Liquid', which is already installed in the prefix.
    """
        ).strip()
    )


def test_UnknownPackageClobberError():
    target_path = "siebel/center/for/c.s"
    colliding_dist_being_linked = "Groot"
    exc = UnknownPackageClobberError(target_path, colliding_dist_being_linked, context)
    with env_var(
        "CONDA_PATH_CONFLICT",
        "prevent",
        stack_callback=conda_tests_ctxt_mgmt_def_pol,
    ):
        with captured() as c:
            conda_exception_handler(_raise_helper, exc)

    assert not c.stdout
    assert (
        c.stderr.strip()
        == dals(
            """
    ClobberError: The package 'Groot' cannot be installed due to a
    path collision for 'siebel/center/for/c.s'.
    This path already exists in the target prefix, and it won't be removed
    by an uninstall action in this transaction. The path is one that conda
    doesn't recognize. It may have been created by another package manager.
    """
        ).strip()
    )


def test_SharedLinkPathClobberError():
    target_path = "some/where/in/shampoo/banana"
    incompatible_package_dists = "Groot"
    exc = SharedLinkPathClobberError(target_path, incompatible_package_dists, context)
    with env_var(
        "CONDA_PATH_CONFLICT",
        "prevent",
        stack_callback=conda_tests_ctxt_mgmt_def_pol,
    ):
        with captured() as c:
            conda_exception_handler(_raise_helper, exc)

    assert not c.stdout
    assert (
        c.stderr.strip()
        == dals(
            """
    ClobberError: This transaction has incompatible packages due to a shared path.
      packages: G, r, o, o, t
      path: 'some/where/in/shampoo/banana'
    """
        ).strip()
    )


def test_CondaFileNotFoundError():
    filename = "Groot"
    exc = PathNotFoundError(filename)
    with env_var("CONDA_JSON", "yes", stack_callback=conda_tests_ctxt_mgmt_def_pol):
        with captured() as c:
            conda_exception_handler(_raise_helper, exc)

    json_obj = json.loads(c.stdout)
    assert not c.stderr
    assert json_obj["exception_type"] == "<class 'conda.exceptions.PathNotFoundError'>"
    assert json_obj["exception_name"] == "PathNotFoundError"
    assert json_obj["message"] == str(exc)
    assert json_obj["error"] == repr(exc)

    with env_var("CONDA_JSON", "no", stack_callback=conda_tests_ctxt_mgmt_def_pol):
        with captured() as c:
            conda_exception_handler(_raise_helper, exc)

    assert not c.stdout
    assert c.stderr.strip() == "PathNotFoundError: Groot"


def test_DirectoryNotFoundError():
    directory = "Groot"
    exc = DirectoryNotFoundError(directory)
    with env_var("CONDA_JSON", "yes", stack_callback=conda_tests_ctxt_mgmt_def_pol):
        with captured() as c:
            conda_exception_handler(_raise_helper, exc)

    json_obj = json.loads(c.stdout)
    assert not c.stderr
    assert (
        json_obj["exception_type"]
        == "<class 'conda.exceptions.DirectoryNotFoundError'>"
    )
    assert json_obj["exception_name"] == "DirectoryNotFoundError"
    assert json_obj["message"] == str(exc)
    assert json_obj["error"] == repr(exc)
    assert json_obj["path"] == "Groot"

    with env_var("CONDA_JSON", "no", stack_callback=conda_tests_ctxt_mgmt_def_pol):
        with captured() as c:
            conda_exception_handler(_raise_helper, exc)

    assert not c.stdout
    assert c.stderr.strip() == "DirectoryNotFoundError: Groot"


def test_MD5MismatchError():
    url = "https://download.url/path/to/file.tar.bz2"
    target_full_path = "/some/path/on/disk/another-name.tar.bz2"
    expected_md5sum = "abc123"
    actual_md5sum = "deadbeef"
    exc = ChecksumMismatchError(
        url, target_full_path, "md5", expected_md5sum, actual_md5sum
    )
    with env_var("CONDA_JSON", "yes", stack_callback=conda_tests_ctxt_mgmt_def_pol):
        with captured() as c:
            conda_exception_handler(_raise_helper, exc)

    json_obj = json.loads(c.stdout)
    assert not c.stderr
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

    with env_var("CONDA_JSON", "no", stack_callback=conda_tests_ctxt_mgmt_def_pol):
        with captured() as c:
            conda_exception_handler(_raise_helper, exc)

    assert not c.stdout
    assert (
        c.stderr.strip()
        == dals(
            """
    ChecksumMismatchError: Conda detected a mismatch between the expected content and downloaded content
    for url 'https://download.url/path/to/file.tar.bz2'.
      download saved to: /some/path/on/disk/another-name.tar.bz2
      expected md5: abc123
      actual md5: deadbeef
    """
        ).strip()
    )


def test_PackageNotFoundError():
    package = "Potato"
    with env_var("CONDA_JSON", "yes", stack_callback=conda_tests_ctxt_mgmt_def_pol):
        with captured() as c:
            exc = PackagesNotFoundError((package,))
            conda_exception_handler(_raise_helper, exc)

    json_obj = json.loads(c.stdout)
    assert not c.stderr
    assert (
        json_obj["exception_type"] == "<class 'conda.exceptions.PackagesNotFoundError'>"
    )
    assert json_obj["message"] == str(exc)
    assert json_obj["error"] == repr(exc)

    with env_var("CONDA_JSON", "no", stack_callback=conda_tests_ctxt_mgmt_def_pol):
        with captured() as c:
            conda_exception_handler(_raise_helper, exc)

    assert not c.stdout
    assert (
        c.stderr.strip()
        == dals(
            """
    PackagesNotFoundError: The following packages are missing from the target environment:
      - Potato
    """
        ).strip()
    )


def test_CondaKeyError():
    key = "Potato"
    message = "Potato is not a key."
    exc = CondaKeyError(key, message)
    with env_var("CONDA_JSON", "yes", stack_callback=conda_tests_ctxt_mgmt_def_pol):
        with captured() as c:
            conda_exception_handler(_raise_helper, exc)

    json_obj = json.loads(c.stdout)
    assert not c.stderr
    assert json_obj["exception_type"] == "<class 'conda.exceptions.CondaKeyError'>"
    assert json_obj["exception_name"] == "CondaKeyError"
    assert json_obj["message"] == str(exc)
    assert json_obj["error"] == repr(exc)
    assert json_obj["key"] == "Potato"

    with env_var("CONDA_JSON", "no", stack_callback=conda_tests_ctxt_mgmt_def_pol):
        with captured() as c:
            conda_exception_handler(_raise_helper, exc)

    assert not c.stdout
    assert c.stderr.strip() == "CondaKeyError: 'Potato': Potato is not a key."


def test_CondaHTTPError():
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
        assert json_obj["exception_type"] == "<class 'conda.exceptions.CondaHTTPError'>"
        assert json_obj["exception_name"] == "CondaHTTPError"
        assert json_obj["message"] == str(exc)
        assert json_obj["error"] == repr(exc)
        assert json_obj["url"] == url
        assert json_obj["status_code"] == status_code
        assert json_obj["reason"] == reason
        assert json_obj["elapsed_time"] == elapsed_time

    with env_var("CONDA_JSON", "no", stack_callback=conda_tests_ctxt_mgmt_def_pol):
        with captured() as c:
            conda_exception_handler(_raise_helper, exc)

    assert not c.stdout
    assert (
        dals(
            """
            CondaHTTPError: HTTP Potato COULD NOT CONNECT for url <https://download.url/path/to/Potato.tar.gz>
            Elapsed: 1.24

            Potato
            """
        ).strip()
        in c.stderr.strip()
    )


def test_CommandNotFoundError_simple():
    cmd = "instate"
    exc = CommandNotFoundError(cmd)

    with env_var("CONDA_JSON", "yes", stack_callback=conda_tests_ctxt_mgmt_def_pol):
        with captured() as c:
            conda_exception_handler(_raise_helper, exc)

    json_obj = json.loads(c.stdout)
    assert not c.stderr
    assert (
        json_obj["exception_type"] == "<class 'conda.exceptions.CommandNotFoundError'>"
    )
    assert json_obj["message"] == str(exc)
    assert json_obj["error"] == repr(exc)

    with env_var("CONDA_JSON", "no", stack_callback=conda_tests_ctxt_mgmt_def_pol):
        with captured() as c:
            conda_exception_handler(_raise_helper, exc)

    assert not c.stdout
    assert c.stderr.strip() == (
        "CommandNotFoundError: No command 'conda instate'.\n"
        "Did you mean 'conda install'?"
    )


def test_CommandNotFoundError_conda_build():
    cmd = "build"
    exc = CommandNotFoundError(cmd)

    with env_var("CONDA_JSON", "yes", stack_callback=conda_tests_ctxt_mgmt_def_pol):
        with captured() as c:
            conda_exception_handler(_raise_helper, exc)

    json_obj = json.loads(c.stdout)
    assert not c.stderr
    assert (
        json_obj["exception_type"] == "<class 'conda.exceptions.CommandNotFoundError'>"
    )
    assert json_obj["message"] == str(exc)
    assert json_obj["error"] == repr(exc)

    with env_var("CONDA_JSON", "no", stack_callback=conda_tests_ctxt_mgmt_def_pol):
        with captured() as c:
            conda_exception_handler(_raise_helper, exc)

    assert not c.stdout
    assert c.stderr.strip() == (
        "CommandNotFoundError: To use 'conda build', install conda-build."
    )


def test_print_unexpected_error_message_upload_1(
    mocker: MockerFixture,
    monkeypatch: MonkeyPatch,
    capsys: CaptureFixture,
):
    """
    Test that error reports are auto submitted when CONDA_REPORT_ERRORS=true.
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
    assert context.report_errors is True
    assert not context.json
    assert not context.always_yes

    ExceptionHandler()(_raise_helper, AssertionError())
    stdout, stderr = capsys.readouterr()

    assert username_not_in_post_mock(post_mock, getpass.getuser())
    assert post_mock.call_count == 2
    assert not stdout
    assert "conda version" in stderr


def test_print_unexpected_error_message_upload_2(
    mocker: MockerFixture,
    monkeypatch: MonkeyPatch,
    capsys: CaptureFixture,
):
    """
    Test that error reports are auto submitted when CONDA_ALWAYS_YES=true. Also
    test that we receive the error report in as a JSON when CONDA_JSON=true.
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
    assert context.report_errors is None
    assert context.json
    assert context.always_yes

    ExceptionHandler()(_raise_helper, AssertionError())
    stdout, stderr = capsys.readouterr()

    assert username_not_in_post_mock(post_mock, getpass.getuser())
    assert post_mock.call_count == 3
    assert len(json.loads(stdout)["conda_info"]["channels"]) >= 2
    assert not stderr


def test_print_unexpected_error_message_upload_3(
    mocker: MockerFixture,
    monkeypatch: MonkeyPatch,
    capsys: CaptureFixture,
):
    """
    Test that we prompt for user confirmation before submitting error reports
    when CONDA_REPORT_ERRORS=none, CONDA_ALWAYS_YES=false, and CONDA_JSON=false.
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
    input_mock = mocker.patch("builtins.input", return_value="y")
    isatty_mock = mocker.patch("os.isatty", return_value=True)

    monkeypatch.setenv("CONDA_REPORT_ERRORS", "none")
    monkeypatch.setenv("CONDA_ALWAYS_YES", "false")
    monkeypatch.setenv("CONDA_JSON", "false")
    reset_context()
    assert context.report_errors is None
    assert not context.json
    assert not context.always_yes

    ExceptionHandler()(_raise_helper, AssertionError())
    stdout, stderr = capsys.readouterr()

    assert username_not_in_post_mock(post_mock, username=getpass.getuser())
    assert isatty_mock.call_count == 1
    assert input_mock.call_count == 1
    assert post_mock.call_count == 2
    assert not stdout
    assert "conda version" in stderr


@patch(
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
@patch("getpass.getuser", return_value="some name")
def test_print_unexpected_error_message_upload_username_with_spaces(pwuid, post_mock):
    with env_var(
        "CONDA_REPORT_ERRORS", "true", stack_callback=conda_tests_ctxt_mgmt_def_pol
    ):
        with captured() as c:
            ExceptionHandler()(_raise_helper, AssertionError())

        error_data = json.loads(post_mock.call_args[1].get("data"))
        assert error_data.get("has_spaces") is True
        assert error_data.get("is_ascii") is True
        assert post_mock.call_count == 2
        assert c.stdout == ""
        assert "conda version" in c.stderr


@patch(
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
@patch("getpass.getuser", return_value="my√nameΩ")
def test_print_unexpected_error_message_upload_username_with_unicode(pwuid, post_mock):
    with env_var(
        "CONDA_REPORT_ERRORS", "true", stack_callback=conda_tests_ctxt_mgmt_def_pol
    ):
        with captured() as c:
            ExceptionHandler()(_raise_helper, AssertionError())

        error_data = json.loads(post_mock.call_args[1].get("data"))
        assert error_data.get("has_spaces") is False
        assert error_data.get("is_ascii") is False
        assert post_mock.call_count == 2
        assert c.stdout == ""
        assert "conda version" in c.stderr


@patch("requests.post", return_value=None)
@patch("builtins.input", return_value="n")
def test_print_unexpected_error_message_opt_out_1(input_mock, post_mock):
    with env_var(
        "CONDA_REPORT_ERRORS", "false", stack_callback=conda_tests_ctxt_mgmt_def_pol
    ):
        AssertionError()
        with captured() as c:
            ExceptionHandler()(_raise_helper, AssertionError())

        assert input_mock.call_count == 0
        assert post_mock.call_count == 0
        assert c.stdout == ""
        print(c.stderr, file=sys.stderr)
        assert "conda version" in c.stderr


@patch("requests.post", return_value=None)
@patch("builtins.input", return_value="n")
@patch("os.isatty", return_value=True)
def test_print_unexpected_error_message_opt_out_2(isatty_mock, input_mock, post_mock):
    with captured() as c:
        ExceptionHandler()(_raise_helper, AssertionError())

    assert input_mock.call_count == 1
    assert post_mock.call_count == 0
    assert c.stdout == ""
    assert "conda version" in c.stderr


def test_BinaryPrefixReplacementError():
    new_data_length = 1104
    original_data_length = 1404
    new_prefix = "some/where/on/goodwin.ave"
    path = "some/where/by/boneyard/creek"
    placeholder = "save/my/spot/in/374"
    exc = BinaryPrefixReplacementError(
        path, placeholder, new_prefix, original_data_length, new_data_length
    )
    with env_var("CONDA_JSON", "yes", stack_callback=conda_tests_ctxt_mgmt_def_pol):
        with captured() as c:
            conda_exception_handler(_raise_helper, exc)

    json_obj = json.loads(c.stdout)
    assert not c.stderr
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

    with env_var("CONDA_JSON", "no", stack_callback=conda_tests_ctxt_mgmt_def_pol):
        with captured() as c:
            conda_exception_handler(_raise_helper, exc)

    assert not c.stdout
    assert (
        c.stderr.strip()
        == dals(
            """
    BinaryPrefixReplacementError: Refusing to replace mismatched data length in binary file.
      path: some/where/by/boneyard/creek
      placeholder: save/my/spot/in/374
      new prefix: some/where/on/goodwin.ave
      original data Length: 1404
      new data length: 1104
    """
        ).strip()
    )


def test_PackagesNotFoundError_use_only_tar_bz2():
    note = "use_only_tar_bz2"
    for use_only_tar_bz2 in (True, False):
        expected = note if use_only_tar_bz2 else ""
        with env_vars(
            {"CONDA_USE_ONLY_TAR_BZ2": str(use_only_tar_bz2)},
            stack_callback=conda_tests_ctxt_mgmt_def_pol,
        ), raises(PackagesNotFoundError, match=expected):
            raise PackagesNotFoundError(
                packages=["does-not-exist"],
                channel_urls=["https://repo.anaconda.org/pkgs/main"],
            )
